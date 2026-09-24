package com.truthlens.backend.service.ocr;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiOcrResponse;
import com.truthlens.backend.dto.OcrEvidenceDto;
import com.truthlens.backend.dto.OcrResultResponse;
import com.truthlens.backend.dto.OcrTextRegionDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.OcrResult;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.OcrResultRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

/**
 * Core business service for Optical Character Recognition & Visual Text Extraction (Module 09).
 *
 * <p>Enforces strict service-layer authorization and media validation:
 * <ul>
 *   <li>Only media owners or users with elevated roles (ANALYST, MODERATOR, ADMIN) can access or trigger analysis.</li>
 *   <li>Supports both {@link MediaType#IMAGE} and {@link MediaType#VIDEO} visual assets.</li>
 * </ul>
 * </p>
 */
@Service
public class OcrAnalysisService {

    private static final Logger log = LoggerFactory.getLogger(OcrAnalysisService.class);

    private final OcrResultRepository ocrResultRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final OcrAiServiceClient ocrAiServiceClient;
    private final ObjectMapper objectMapper;

    public OcrAnalysisService(
            OcrResultRepository ocrResultRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            OcrAiServiceClient ocrAiServiceClient,
            ObjectMapper objectMapper) {
        this.ocrResultRepository = ocrResultRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.ocrAiServiceClient = ocrAiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves OCR analysis findings for a media asset.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link OcrResultResponse}
     */
    @Transactional
    public OcrResultResponse getOcrResult(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return ocrResultRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeAnalysis(media));
    }

    /**
     * Explicitly re-triggers OCR analysis for a media asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link OcrResultResponse}
     */
    @Transactional
    public OcrResultResponse reanalyzeOcr(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeAnalysis(media);
    }

    /**
     * Retrieves the list of extracted text regions with spatial bounding boxes and timestamps.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return list of {@link OcrTextRegionDto}
     */
    @Transactional(readOnly = true)
    public List<OcrTextRegionDto> getBoundingBoxes(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        OcrResult result = ocrResultRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No OCR analysis record found for media id: " + mediaId));

        return parseRegions(result.getBoundingBoxesJson());
    }

    /**
     * Retrieves the raw concatenated text extracted from the visual asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return raw extracted text string
     */
    @Transactional(readOnly = true)
    public String getExtractedText(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        OcrResult result = ocrResultRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No OCR analysis record found for media id: " + mediaId));

        return result.getExtractedText() != null ? result.getExtractedText() : "";
    }

    // -------------------------------------------------------------------------
    // Execution & Persistence
    // -------------------------------------------------------------------------

    private OcrResultResponse executeAnalysis(Media media) {
        byte[] mediaBytes = loadMediaBytes(media);

        try {
            FastApiOcrResponse aiResponse = ocrAiServiceClient.analyzeOcr(
                    mediaBytes,
                    media.getOriginalFilename(),
                    media.getMimeType()
            );

            return persistAnalysis(media, aiResponse);

        } catch (AiServiceException e) {
            log.error("AI service error during OCR analysis for media {}: {}", media.getId(), e.getMessage());
            persistFailure(media, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Unexpected error during OCR analysis for media {}: {}", media.getId(), e.getMessage(), e);
            persistFailure(media, e.getMessage());
            throw new AiServiceException("OCR analysis pipeline failed: " + e.getMessage(), e);
        }
    }

    private byte[] loadMediaBytes(Media media) {
        try (InputStream is = storageService.load(media.getStoragePath())) {
            return is.readAllBytes();
        } catch (Exception e) {
            log.error("Failed to read media bytes from storage for path {}: {}", media.getStoragePath(), e.getMessage());
            throw new StorageException("Unable to read media file from storage: " + e.getMessage(), e);
        }
    }

    private OcrResultResponse persistAnalysis(Media media, FastApiOcrResponse aiResponse) {
        String boundingBoxesJson = null;
        try {
            if (aiResponse.getRegions() != null) {
                boundingBoxesJson = objectMapper.writeValueAsString(aiResponse.getRegions());
            }
        } catch (Exception e) {
            log.warn("Failed to serialize OCR text regions to JSON: {}", e.getMessage());
        }

        String evidenceJson = null;
        try {
            if (aiResponse.getEvidence() != null) {
                evidenceJson = objectMapper.writeValueAsString(aiResponse.getEvidence());
            }
        } catch (Exception e) {
            log.warn("Failed to serialize OCR evidence to JSON: {}", e.getMessage());
        }

        final String finalBoundingBoxesJson = boundingBoxesJson;
        final String finalEvidenceJson = evidenceJson;

        OcrResult entity = ocrResultRepository.findByMediaId(media.getId())
                .map(existing -> {
                    existing.setExtractedText(aiResponse.getExtractedText());
                    existing.setLanguage(aiResponse.getLanguage() != null ? aiResponse.getLanguage() : "en");
                    existing.setConfidenceScore(aiResponse.getConfidenceScore());
                    existing.setRegionsCount(aiResponse.getRegionsCount());
                    existing.setBoundingBoxesJson(finalBoundingBoxesJson);
                    existing.setEvidenceJson(finalEvidenceJson);
                    existing.setAnalysisStatus(AnalysisStatus.COMPLETED);
                    return existing;
                })
                .orElseGet(() -> new OcrResult(
                        media,
                        aiResponse.getExtractedText(),
                        aiResponse.getLanguage(),
                        aiResponse.getConfidenceScore(),
                        aiResponse.getRegionsCount(),
                        finalBoundingBoxesJson,
                        finalEvidenceJson,
                        AnalysisStatus.COMPLETED
                ));

        try {
            entity = ocrResultRepository.save(entity);
            log.info("Persisted OCR analysis findings for media {}: regions={}, lang={}",
                    media.getId(), entity.getRegionsCount(), entity.getLanguage());
            return toResponse(entity);
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent OCR analysis detected for media {}; reloading existing record", media.getId());
            return ocrResultRepository.findByMediaId(media.getId())
                    .map(this::toResponse)
                    .orElseThrow(() -> e);
        }
    }

    private void persistFailure(Media media, String errorMessage) {
        try {
            OcrResult entity = ocrResultRepository.findByMediaId(media.getId())
                    .orElseGet(() -> new OcrResult(
                            media,
                            "",
                            "en",
                            0.0,
                            0,
                            "[]",
                            "{}",
                            AnalysisStatus.FAILED
                    ));
            entity.setAnalysisStatus(AnalysisStatus.FAILED);
            ocrResultRepository.save(entity);
        } catch (Exception e) {
            log.warn("Failed to record OCR analysis failure state for media {}: {}", media.getId(), e.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access OCR analysis");
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
            log.warn("IDOR attempt blocked on OCR analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's analysis.");
        }

        if (media.getMediaType() != MediaType.IMAGE && media.getMediaType() != MediaType.VIDEO) {
            throw new InvalidMediaException("OCR text extraction is only supported for image and video assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private OcrResultResponse toResponse(OcrResult entity) {
        List<OcrTextRegionDto> regions = parseRegions(entity.getBoundingBoxesJson());
        OcrEvidenceDto evidence = parseEvidence(entity.getEvidenceJson());

        return new OcrResultResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getExtractedText(),
                entity.getLanguage(),
                entity.getConfidenceScore(),
                entity.getRegionsCount(),
                regions,
                evidence,
                entity.getAnalysisStatus(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private List<OcrTextRegionDto> parseRegions(String json) {
        if (json == null || json.isBlank() || "[]".equals(json.trim())) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<OcrTextRegionDto>>() {});
        } catch (Exception e) {
            log.warn("Failed to deserialize OCR text regions JSON: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private OcrEvidenceDto parseEvidence(String json) {
        if (json == null || json.isBlank() || "{}".equals(json.trim())) {
            return new OcrEvidenceDto();
        }
        try {
            return objectMapper.readValue(json, OcrEvidenceDto.class);
        } catch (Exception e) {
            log.warn("Failed to deserialize OCR evidence JSON: {}", e.getMessage());
            return new OcrEvidenceDto();
        }
    }
}
