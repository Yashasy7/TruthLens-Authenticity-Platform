package com.truthlens.backend.service.avsync;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.AvSyncAnalysisResponse;
import com.truthlens.backend.dto.AvSyncEvidenceDto;
import com.truthlens.backend.dto.FastApiAvSyncResponse;
import com.truthlens.backend.dto.MismatchSegmentDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AvSyncAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.AvSyncAnalysisRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Core business service for Audio-Video Synchronization Analysis (Module 08).
 *
 * <p>Enforces strict service-layer authorization and media validation:
 * <ul>
 *   <li>Only media owners or users with elevated roles (ANALYST, MODERATOR, ADMIN) can access or trigger analysis.</li>
 *   <li>Only {@link MediaType#VIDEO} assets containing audio can be analyzed.</li>
 * </ul>
 * </p>
 */
@Service
public class AvSyncAnalysisService {

    private static final Logger log = LoggerFactory.getLogger(AvSyncAnalysisService.class);

    private final AvSyncAnalysisRepository avSyncAnalysisRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final AvSyncAiServiceClient avSyncAiServiceClient;
    private final ObjectMapper objectMapper;

    public AvSyncAnalysisService(
            AvSyncAnalysisRepository avSyncAnalysisRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            AvSyncAiServiceClient avSyncAiServiceClient,
            ObjectMapper objectMapper) {
        this.avSyncAnalysisRepository = avSyncAnalysisRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.avSyncAiServiceClient = avSyncAiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves AV synchronization analysis findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link AvSyncAnalysisResponse}
     */
    @Transactional
    public AvSyncAnalysisResponse getAvSyncAnalysis(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return avSyncAnalysisRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeAnalysis(media));
    }

    /**
     * Explicitly re-triggers AV synchronization analysis for a media asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link AvSyncAnalysisResponse}
     */
    @Transactional
    public AvSyncAnalysisResponse reanalyzeAvSync(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeAnalysis(media);
    }

    /**
     * Retrieves the granular cross-modal forensic evidence and metrics for an asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return {@link AvSyncEvidenceDto}
     */
    @Transactional(readOnly = true)
    public AvSyncEvidenceDto getEvidence(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        AvSyncAnalysis analysis = avSyncAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No AV sync analysis record found for media id: " + mediaId));

        return parseEvidence(analysis.getEvidenceJson());
    }

    /**
     * Retrieves the list of detected mismatch segments for an asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return list of {@link MismatchSegmentDto}
     */
    @Transactional(readOnly = true)
    public List<MismatchSegmentDto> getMismatchSegments(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        AvSyncAnalysis analysis = avSyncAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No AV sync analysis record found for media id: " + mediaId));

        return parseMismatchSegments(analysis.getMismatchSegmentsJson());
    }

    // -------------------------------------------------------------------------
    // Internal Analysis Execution
    // -------------------------------------------------------------------------

    private AvSyncAnalysisResponse executeAnalysis(Media media) {
        UUID mediaId = media.getId();
        log.info("Starting AV synchronization analysis for media ID: {}", mediaId);

        byte[] videoBytes;
        try (InputStream is = storageService.load(media.getStoragePath())) {
            videoBytes = is.readAllBytes();
        } catch (Exception e) {
            log.error("Failed to read video file from storage for media ID: {}", mediaId, e);
            throw new StorageException("Unable to read video file from storage for analysis", e);
        }

        FastApiAvSyncResponse aiResult;
        try {
            aiResult = avSyncAiServiceClient.analyzeAvSync(videoBytes, media.getOriginalFilename(), media.getMimeType());
        } catch (AiServiceException e) {
            log.error("AI service failure while analyzing AV sync for media ID {}: {}", mediaId, e.getMessage());
            saveFailedAnalysis(media, e.getMessage());
            throw e;
        }

        Optional<AvSyncAnalysis> existingOpt = avSyncAnalysisRepository.findByMediaId(mediaId);
        AvSyncAnalysis analysis = existingOpt.orElseGet(() -> new AvSyncAnalysis(media));

        analysis.setSyncScore(aiResult.getSyncScore());
        analysis.setLipOffsetMs(aiResult.getLipOffsetMs());
        analysis.setConfidence(aiResult.getConfidence());
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelName(aiResult.getModelName());
        analysis.setModelVersion(aiResult.getModelVersion());

        try {
            analysis.setMismatchSegmentsJson(objectMapper.writeValueAsString(aiResult.getMismatchSegments()));
            analysis.setEvidenceJson(objectMapper.writeValueAsString(aiResult.getEvidence()));
        } catch (Exception e) {
            log.warn("Failed to serialize AV sync evidence JSON for media ID {}: {}", mediaId, e.getMessage());
            analysis.setMismatchSegmentsJson("[]");
            analysis.setEvidenceJson("{}");
        }

        try {
            AvSyncAnalysis saved = avSyncAnalysisRepository.saveAndFlush(analysis);
            log.info("Completed AV sync analysis for media ID: {} (syncScore={}, lipOffsetMs={}ms)",
                    mediaId, saved.getSyncScore(), saved.getLipOffsetMs());
            return toResponse(saved);
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent AV sync analysis persist conflict on media ID {}, reloading existing record", mediaId);
            return avSyncAnalysisRepository.findByMediaId(mediaId)
                    .map(this::toResponse)
                    .orElseThrow(() -> new IllegalStateException("Failed to retrieve concurrent AV sync analysis result", e));
        }
    }

    private void saveFailedAnalysis(Media media, String errorMessage) {
        try {
            Optional<AvSyncAnalysis> existingOpt = avSyncAnalysisRepository.findByMediaId(media.getId());
            AvSyncAnalysis analysis = existingOpt.orElseGet(() -> new AvSyncAnalysis(media));
            analysis.setAnalysisStatus(AnalysisStatus.FAILED);
            analysis.setSyncScore(0.0);
            analysis.setLipOffsetMs(0.0);
            analysis.setConfidence(0.0);
            analysis.setMismatchSegmentsJson("[]");
            analysis.setEvidenceJson(objectMapper.writeValueAsString(Map.of("error", errorMessage != null ? errorMessage : "Unknown error")));
            avSyncAnalysisRepository.saveAndFlush(analysis);
        } catch (Exception ex) {
            log.warn("Failed to record FAILED status for AV sync media ID {}: {}", media.getId(), ex.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access AV sync analysis");
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
            log.warn("IDOR attempt blocked on AV sync analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's analysis.");
        }

        if (media.getMediaType() != MediaType.VIDEO) {
            throw new InvalidMediaException("Audio-video synchronization analysis is only supported for video assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private AvSyncAnalysisResponse toResponse(AvSyncAnalysis entity) {
        List<MismatchSegmentDto> segments = parseMismatchSegments(entity.getMismatchSegmentsJson());
        AvSyncEvidenceDto evidence = parseEvidence(entity.getEvidenceJson());
        String assessment = computeAssessment(entity.getSyncScore(), entity.getLipOffsetMs(), entity.getAnalysisStatus());

        return new AvSyncAnalysisResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getSyncScore(),
                entity.getLipOffsetMs(),
                entity.getConfidence(),
                assessment,
                entity.getAnalysisStatus(),
                entity.getModelName(),
                entity.getModelVersion(),
                segments,
                evidence,
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private String computeAssessment(double syncScore, double lipOffsetMs, AnalysisStatus status) {
        if (status == AnalysisStatus.FAILED) {
            return "ANALYSIS_FAILED";
        }
        if (syncScore >= 0.75 && Math.abs(lipOffsetMs) <= 60.0) {
            return "SYNCHRONIZED";
        }
        if (syncScore < 0.40 || Math.abs(lipOffsetMs) > 180.0) {
            return "SUSPECTED_DUBBING_OR_DESYNC";
        }
        return "ANOMALOUS_SYNCHRONIZATION";
    }

    private List<MismatchSegmentDto> parseMismatchSegments(String json) {
        if (json == null || json.isBlank() || "[]".equals(json.trim())) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<MismatchSegmentDto>>() {});
        } catch (Exception e) {
            log.warn("Failed to deserialize mismatch segments JSON: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private AvSyncEvidenceDto parseEvidence(String json) {
        if (json == null || json.isBlank() || "{}".equals(json.trim())) {
            return new AvSyncEvidenceDto();
        }
        try {
            return objectMapper.readValue(json, AvSyncEvidenceDto.class);
        } catch (Exception e) {
            log.warn("Failed to deserialize AV sync evidence JSON: {}", e.getMessage());
            return new AvSyncEvidenceDto();
        }
    }
}
