package com.truthlens.backend.service.image;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiImageAnalysisResponse;
import com.truthlens.backend.dto.ImageAnalysisResponse;
import com.truthlens.backend.dto.ImageEvidenceDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ImageAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.ImageAnalysisRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageKeyGenerator;
import com.truthlens.backend.service.storage.StorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.Base64;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Core service orchestrating Module 05 — Image Authenticity Analysis.
 *
 * <p>Enforces IDOR authorization and image-type validation, loads quarantined media from storage,
 * calls the internal AI/ML vision service, safely stores visual heatmap artifacts,
 * and persists bounded evidence for explainable consumption.</p>
 */
@Service
public class ImageAuthenticityService {

    private static final Logger log = LoggerFactory.getLogger(ImageAuthenticityService.class);

    private final ImageAnalysisRepository imageAnalysisRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final StorageKeyGenerator storageKeyGenerator;
    private final AiServiceClient aiServiceClient;
    private final ObjectMapper objectMapper;

    public ImageAuthenticityService(
            ImageAnalysisRepository imageAnalysisRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            StorageKeyGenerator storageKeyGenerator,
            AiServiceClient aiServiceClient,
            ObjectMapper objectMapper) {
        this.imageAnalysisRepository = imageAnalysisRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.storageKeyGenerator = storageKeyGenerator;
        this.aiServiceClient = aiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves the image authenticity analysis for a media asset, performing analysis
     * on demand if not already completed.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link ImageAnalysisResponse}
     */
    @Transactional
    public ImageAnalysisResponse getImageAnalysis(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return imageAnalysisRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeAnalysis(media));
    }

    /**
     * Explicitly triggers or re-triggers image authenticity analysis for a media asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link ImageAnalysisResponse}
     */
    @Transactional
    public ImageAnalysisResponse reanalyzeImage(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeAnalysis(media);
    }

    /**
     * Retrieves the structured forensic evidence breakdown for an image.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return {@link ImageEvidenceDto}
     */
    @Transactional(readOnly = true)
    public ImageEvidenceDto getEvidence(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        ImageAnalysis analysis = imageAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No image analysis record found for media id: " + mediaId));

        return parseEvidence(analysis.getEvidenceJson(), analysis);
    }

    /**
     * Streams a visual forensic heatmap artifact (ELA or Grad-CAM) for authorized callers.
     *
     * @param mediaId          UUID of the media asset
     * @param artifactType     "ela" or "gradcam"
     * @param currentUserEmail email of the authenticated caller
     * @return InputStream to stream the PNG artifact
     */
    @Transactional(readOnly = true)
    public InputStream getArtifactStream(UUID mediaId, String artifactType, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        ImageAnalysis analysis = imageAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No image analysis record found for media id: " + mediaId));

        String storageKey;
        if ("ela".equalsIgnoreCase(artifactType)) {
            storageKey = analysis.getElaHeatmapUrl();
        } else if ("gradcam".equalsIgnoreCase(artifactType)) {
            storageKey = analysis.getGradcamHeatmapUrl();
        } else {
            throw new IllegalArgumentException("Unsupported artifact type: '" + artifactType + "'. Supported types: 'ela', 'gradcam'");
        }

        if (storageKey == null || storageKey.isBlank() || !storageService.exists(storageKey)) {
            throw new MediaNotFoundException("Visual artifact '" + artifactType + "' not found for media id: " + mediaId);
        }

        return storageService.load(storageKey);
    }

    // -------------------------------------------------------------------------
    // Internal Analysis Execution
    // -------------------------------------------------------------------------

    private ImageAnalysisResponse executeAnalysis(Media media) {
        UUID mediaId = media.getId();
        log.info("Starting image authenticity analysis for media ID: {}", mediaId);

        byte[] imageBytes;
        try (InputStream is = storageService.load(media.getStoragePath())) {
            imageBytes = is.readAllBytes();
        } catch (Exception e) {
            log.error("Failed to read media storage file for media ID: {}", mediaId, e);
            throw new StorageException("Unable to read media file from storage for analysis", e);
        }

        FastApiImageAnalysisResponse aiResult;
        try {
            aiResult = aiServiceClient.analyzeImage(imageBytes, media.getOriginalFilename(), media.getMimeType());
        } catch (AiServiceException e) {
            log.error("AI service failure while analyzing media ID {}: {}", mediaId, e.getMessage());
            saveFailedAnalysis(media, e.getMessage());
            throw e;
        }

        // Store heatmap artifacts safely in isolated storage
        String elaStorageKey = null;
        if (aiResult.getElaHeatmapBase64() != null && !aiResult.getElaHeatmapBase64().isBlank()) {
            elaStorageKey = storeHeatmapArtifact(aiResult.getElaHeatmapBase64(), "ela");
        }

        String gradcamStorageKey = null;
        if (aiResult.getGradcamHeatmapBase64() != null && !aiResult.getGradcamHeatmapBase64().isBlank()) {
            gradcamStorageKey = storeHeatmapArtifact(aiResult.getGradcamHeatmapBase64(), "gradcam");
        }

        // Build or update ImageAnalysis entity
        Optional<ImageAnalysis> existingOpt = imageAnalysisRepository.findByMediaId(mediaId);
        ImageAnalysis analysis = existingOpt.orElseGet(() -> new ImageAnalysis(media));

        analysis.setAiProb(aiResult.getAiProb());
        analysis.setManipulationProb(aiResult.getManipulationProb());
        analysis.setElaHeatmapUrl(elaStorageKey);
        analysis.setGradcamHeatmapUrl(gradcamStorageKey);
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelVersion(aiResult.getModelVersion());

        analysis.setNoiseVariance(aiResult.getNoiseVariance());
        analysis.setFftAnomalyScore(aiResult.getFftAnomalyScore());
        analysis.setCopyMoveDetected(aiResult.isCopyMoveDetected());
        analysis.setSplicingDetected(aiResult.isSplicingDetected());

        if (aiResult.getEvidence() != null) {
            try {
                analysis.setEvidenceJson(objectMapper.writeValueAsString(aiResult.getEvidence()));
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialize evidence object for media ID {}", mediaId, e);
                analysis.setEvidenceJson("{}");
            }
        }

        try {
            ImageAnalysis saved = imageAnalysisRepository.saveAndFlush(analysis);
            log.info("Completed image authenticity analysis for media ID: {} (aiProb={}, manipulationProb={})",
                    mediaId, saved.getAiProb(), saved.getManipulationProb());
            return toResponse(saved);
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent analysis persist conflict on media ID {}, reloading existing record", mediaId);
            return imageAnalysisRepository.findByMediaId(mediaId)
                    .map(this::toResponse)
                    .orElseThrow(() -> new IllegalStateException("Failed to retrieve concurrent analysis result", e));
        }
    }

    private void saveFailedAnalysis(Media media, String errorMessage) {
        try {
            Optional<ImageAnalysis> existingOpt = imageAnalysisRepository.findByMediaId(media.getId());
            ImageAnalysis analysis = existingOpt.orElseGet(() -> new ImageAnalysis(media));
            analysis.setAnalysisStatus(AnalysisStatus.FAILED);
            analysis.setAiProb(0.0);
            analysis.setManipulationProb(0.0);
            analysis.setEvidenceJson(objectMapper.writeValueAsString(Map.of("error", errorMessage != null ? errorMessage : "Unknown error")));
            imageAnalysisRepository.saveAndFlush(analysis);
        } catch (Exception ex) {
            log.warn("Failed to record FAILED status for media ID {}: {}", media.getId(), ex.getMessage());
        }
    }

    private String storeHeatmapArtifact(String base64Content, String artifactType) {
        try {
            byte[] bytes = Base64.getDecoder().decode(base64Content);
            String storageKey = storageKeyGenerator.generateKey(MediaType.IMAGE, "image/png");
            return storageService.store(new ByteArrayInputStream(bytes), storageKey, "image/png", bytes.length);
        } catch (Exception e) {
            log.warn("Failed to decode or store {} heatmap artifact: {}", artifactType, e.getMessage());
            return null;
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access image analysis");
        }

        Media media = mediaRepository.findById(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("Media not found with id: " + mediaId));

        User currentUser = userRepository.findByEmail(currentUserEmail)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + currentUserEmail));

        boolean isOwner = media.getUploader().getId().equals(currentUser.getId());
        boolean isElevated = currentUser.getRoles().stream()
                .anyMatch(r -> r.getName() == RoleName.ANALYST ||
                               r.getName() == RoleName.MODERATOR ||
                               r.getName() == RoleName.ADMIN);

        if (!isOwner && !isElevated) {
            log.warn("IDOR attempt blocked on image analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's analysis.");
        }

        if (media.getMediaType() != MediaType.IMAGE) {
            throw new InvalidMediaException("Image authenticity analysis is only supported for image assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private ImageAnalysisResponse toResponse(ImageAnalysis entity) {
        ImageEvidenceDto evidence = parseEvidence(entity.getEvidenceJson(), entity);
        String assessment = computeAuthenticityAssessment(entity.getAiProb(), entity.getManipulationProb(), entity.getAnalysisStatus());

        String elaUrl = entity.getElaHeatmapUrl() != null ? "/api/media/" + entity.getMedia().getId() + "/image-analysis/artifacts/ela" : null;
        String gradcamUrl = entity.getGradcamHeatmapUrl() != null ? "/api/media/" + entity.getMedia().getId() + "/image-analysis/artifacts/gradcam" : null;

        return new ImageAnalysisResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getAiProb(),
                entity.getManipulationProb(),
                assessment,
                elaUrl,
                gradcamUrl,
                entity.getNoiseVariance(),
                entity.getFftAnomalyScore(),
                entity.isCopyMoveDetected(),
                entity.isSplicingDetected(),
                entity.getAnalysisStatus(),
                entity.getModelVersion(),
                evidence,
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private ImageEvidenceDto parseEvidence(String json, ImageAnalysis entity) {
        if (json != null && !json.isBlank()) {
            try {
                return objectMapper.readValue(json, ImageEvidenceDto.class);
            } catch (Exception e) {
                log.debug("Could not deserialize evidence JSON directly, building fallback DTO: {}", e.getMessage());
            }
        }
        return new ImageEvidenceDto(
                entity.getNoiseVariance(),
                null,
                entity.getFftAnomalyScore(),
                entity.isCopyMoveDetected(),
                entity.isSplicingDetected(),
                null,
                null,
                Map.of()
        );
    }

    private String computeAuthenticityAssessment(double aiProb, double manipulationProb, AnalysisStatus status) {
        if (status == AnalysisStatus.FAILED) {
            return "ANALYSIS_FAILED";
        }
        if (status == AnalysisStatus.PENDING || status == AnalysisStatus.PROCESSING) {
            return "IN_PROGRESS";
        }
        if (aiProb >= 0.75 && manipulationProb >= 0.75) {
            return "HIGH_SYNTHETIC_AND_MANIPULATION_RISK";
        }
        if (aiProb >= 0.75) {
            return "HIGH_SYNTHETIC_RISK";
        }
        if (manipulationProb >= 0.75) {
            return "HIGH_MANIPULATION_RISK";
        }
        if (aiProb >= 0.50 || manipulationProb >= 0.50) {
            return "SUSPICIOUS_ANOMALIES_DETECTED";
        }
        if (aiProb <= 0.25 && manipulationProb <= 0.25) {
            return "LOW_ANOMALY_LEVEL";
        }
        return "MODERATE_ANOMALY_LEVEL";
    }
}
