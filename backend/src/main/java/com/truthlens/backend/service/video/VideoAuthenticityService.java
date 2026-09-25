package com.truthlens.backend.service.video;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiVideoAnalysisResponse;
import com.truthlens.backend.dto.FrameScoreDto;
import com.truthlens.backend.dto.SuspiciousTimestampDto;
import com.truthlens.backend.dto.VideoAnalysisResponse;
import com.truthlens.backend.dto.VideoEvidenceDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.entity.VideoAnalysis;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.repository.VideoAnalysisRepository;
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
 * Core business service for video deepfake detection and forensic analysis (Module 06).
 */
@Service
public class VideoAuthenticityService {

    private static final Logger log = LoggerFactory.getLogger(VideoAuthenticityService.class);

    private final VideoAnalysisRepository videoAnalysisRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final VideoAiServiceClient videoAiServiceClient;
    private final ObjectMapper objectMapper;

    public VideoAuthenticityService(
            VideoAnalysisRepository videoAnalysisRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            VideoAiServiceClient videoAiServiceClient,
            ObjectMapper objectMapper) {
        this.videoAnalysisRepository = videoAnalysisRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.videoAiServiceClient = videoAiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves video deepfake analysis findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link VideoAnalysisResponse}
     */
    @Transactional
    public VideoAnalysisResponse getVideoAnalysis(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return videoAnalysisRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeAnalysis(media));
    }

    /**
     * Explicitly re-triggers video authenticity analysis for a video asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link VideoAnalysisResponse}
     */
    @Transactional
    public VideoAnalysisResponse reanalyzeVideo(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeAnalysis(media);
    }

    /**
     * Retrieves the forensic evidence and per-frame scores for a video asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return {@link VideoEvidenceDto}
     */
    @Transactional(readOnly = true)
    public VideoEvidenceDto getEvidence(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        VideoAnalysis analysis = videoAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No video analysis record found for media id: " + mediaId));

        return parseEvidence(analysis);
    }

    /**
     * Retrieves the chronological timeline of suspicious timestamps marked during analysis.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return list of {@link SuspiciousTimestampDto}
     */
    @Transactional(readOnly = true)
    public List<SuspiciousTimestampDto> getTimeline(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        VideoAnalysis analysis = videoAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No video analysis record found for media id: " + mediaId));

        return parseSuspiciousTimestamps(analysis.getSuspiciousTimestampsJson());
    }

    // -------------------------------------------------------------------------
    // Internal Analysis Execution
    // -------------------------------------------------------------------------

    private VideoAnalysisResponse executeAnalysis(Media media) {
        UUID mediaId = media.getId();
        log.info("Starting video deepfake analysis for media ID: {}", mediaId);

        byte[] videoBytes;
        try (InputStream is = storageService.load(media.getStoragePath())) {
            videoBytes = is.readAllBytes();
        } catch (Exception e) {
            log.error("Failed to read video file from storage for media ID: {}", mediaId, e);
            throw new StorageException("Unable to read video file from storage for analysis", e);
        }

        FastApiVideoAnalysisResponse aiResult;
        try {
            aiResult = videoAiServiceClient.analyzeVideo(videoBytes, media.getOriginalFilename(), media.getMimeType());
        } catch (AiServiceException e) {
            log.error("AI service failure while analyzing video media ID {}: {}", mediaId, e.getMessage());
            saveFailedAnalysis(media, e.getMessage());
            throw e;
        }

        Optional<VideoAnalysis> existingOpt = videoAnalysisRepository.findByMediaId(mediaId);
        VideoAnalysis analysis = existingOpt.orElseGet(() -> new VideoAnalysis(media));

        analysis.setDeepfakeProb(aiResult.getDeepfakeProb());
        analysis.setFaceCount(aiResult.getFaceCount());
        analysis.setTotalFramesSampled(aiResult.getTotalFramesSampled());
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelVersion(aiResult.getModelVersion());

        try {
            analysis.setSuspiciousTimestampsJson(objectMapper.writeValueAsString(aiResult.getSuspiciousTimestamps()));
            analysis.setFrameScoresJson(objectMapper.writeValueAsString(aiResult.getFrameScores()));
        } catch (Exception e) {
            log.warn("Failed to serialize video evidence JSON for media ID {}: {}", mediaId, e.getMessage());
            analysis.setSuspiciousTimestampsJson("[]");
            analysis.setFrameScoresJson("[]");
        }

        try {
            VideoAnalysis saved = videoAnalysisRepository.saveAndFlush(analysis);
            log.info("Completed video deepfake analysis for media ID: {} (deepfakeProb={}, faces={})",
                    mediaId, saved.getDeepfakeProb(), saved.getFaceCount());
            return toResponse(saved);
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent video analysis persist conflict on media ID {}, reloading existing record", mediaId);
            return videoAnalysisRepository.findByMediaId(mediaId)
                    .map(this::toResponse)
                    .orElseThrow(() -> new IllegalStateException("Failed to retrieve concurrent video analysis result", e));
        }
    }

    private void saveFailedAnalysis(Media media, String errorMessage) {
        try {
            Optional<VideoAnalysis> existingOpt = videoAnalysisRepository.findByMediaId(media.getId());
            VideoAnalysis analysis = existingOpt.orElseGet(() -> new VideoAnalysis(media));
            analysis.setAnalysisStatus(AnalysisStatus.FAILED);
            analysis.setDeepfakeProb(0.0);
            analysis.setFaceCount(0);
            analysis.setTotalFramesSampled(0);
            analysis.setSuspiciousTimestampsJson("[]");
            analysis.setFrameScoresJson(objectMapper.writeValueAsString(Map.of("error", errorMessage != null ? errorMessage : "Unknown error")));
            videoAnalysisRepository.saveAndFlush(analysis);
        } catch (Exception ex) {
            log.warn("Failed to record FAILED status for video media ID {}: {}", media.getId(), ex.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access video analysis");
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
            log.warn("IDOR attempt blocked on video analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's analysis.");
        }

        if (media.getMediaType() != MediaType.VIDEO) {
            throw new InvalidMediaException("Video deepfake analysis is only supported for video assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private VideoAnalysisResponse toResponse(VideoAnalysis entity) {
        List<SuspiciousTimestampDto> timestamps = parseSuspiciousTimestamps(entity.getSuspiciousTimestampsJson());
        VideoEvidenceDto evidence = parseEvidence(entity);
        String assessment = computeAssessment(entity.getDeepfakeProb(), entity.getAnalysisStatus());

        return new VideoAnalysisResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getDeepfakeProb(),
                entity.getFaceCount(),
                entity.getTotalFramesSampled(),
                assessment,
                entity.getAnalysisStatus(),
                entity.getModelVersion(),
                timestamps,
                evidence,
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private List<SuspiciousTimestampDto> parseSuspiciousTimestamps(String json) {
        if (json != null && !json.isBlank()) {
            try {
                return objectMapper.readValue(json, new TypeReference<List<SuspiciousTimestampDto>>() {});
            } catch (Exception e) {
                log.debug("Could not deserialize suspicious timestamps JSON: {}", e.getMessage());
            }
        }
        return Collections.emptyList();
    }

    private VideoEvidenceDto parseEvidence(VideoAnalysis entity) {
        List<FrameScoreDto> frameScores = Collections.emptyList();
        if (entity.getFrameScoresJson() != null && !entity.getFrameScoresJson().isBlank()) {
            try {
                frameScores = objectMapper.readValue(entity.getFrameScoresJson(), new TypeReference<List<FrameScoreDto>>() {});
            } catch (Exception e) {
                log.debug("Could not deserialize frame scores JSON: {}", e.getMessage());
            }
        }

        List<SuspiciousTimestampDto> timestamps = parseSuspiciousTimestamps(entity.getSuspiciousTimestampsJson());
        double duration = frameScores.isEmpty() ? 0.0 : frameScores.get(frameScores.size() - 1).timestampSeconds();

        return new VideoEvidenceDto(
                entity.getFaceCount(),
                entity.getTotalFramesSampled(),
                duration,
                frameScores,
                timestamps,
                Map.of("deepfake_prob", entity.getDeepfakeProb(), "analysis_status", entity.getAnalysisStatus().name())
        );
    }

    private String computeAssessment(double deepfakeProb, AnalysisStatus status) {
        if (status == AnalysisStatus.FAILED) {
            return "ANALYSIS_FAILED";
        }
        if (status == AnalysisStatus.PENDING || status == AnalysisStatus.PROCESSING) {
            return "IN_PROGRESS";
        }
        if (deepfakeProb >= 0.75) {
            return "HIGH_DEEPFAKE_RISK";
        }
        if (deepfakeProb >= 0.50) {
            return "SUSPICIOUS_DEEPFAKE_INDICATORS";
        }
        if (deepfakeProb <= 0.25) {
            return "LOW_DEEPFAKE_RISK";
        }
        return "MODERATE_DEEPFAKE_RISK";
    }
}
