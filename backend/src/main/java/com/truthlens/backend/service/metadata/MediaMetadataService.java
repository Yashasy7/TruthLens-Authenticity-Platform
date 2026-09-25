package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.ForensicAnomalyDto;
import com.truthlens.backend.dto.MediaMetadataResponse;
import com.truthlens.backend.dto.MetadataAnomalyReportResponse;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaMetadata;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaMetadataRepository;
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
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Service orchestrating forensic metadata extraction, normalization, persistence,
 * anomaly rule evaluation, and secure access control for multimedia assets.
 */
@Service
public class MediaMetadataService {

    private static final Logger log = LoggerFactory.getLogger(MediaMetadataService.class);

    private final MediaRepository mediaRepository;
    private final MediaMetadataRepository mediaMetadataRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final CompositeMetadataExtractorService extractorService;
    private final MetadataAnomalyEvaluator anomalyEvaluator;
    private final ObjectMapper objectMapper;

    public MediaMetadataService(
            MediaRepository mediaRepository,
            MediaMetadataRepository mediaMetadataRepository,
            UserRepository userRepository,
            StorageService storageService,
            CompositeMetadataExtractorService extractorService,
            MetadataAnomalyEvaluator anomalyEvaluator,
            ObjectMapper objectMapper) {
        this.mediaRepository = mediaRepository;
        this.mediaMetadataRepository = mediaMetadataRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.extractorService = extractorService;
        this.anomalyEvaluator = anomalyEvaluator;
        this.objectMapper = objectMapper;
    }

    /**
     * Extracts and persists metadata for an ingested media item.
     * Idempotent and concurrency-safe against race conditions.
     *
     * @param media the ingested media entity
     * @return persisted {@link MediaMetadataResponse}
     */
    @Transactional
    public MediaMetadataResponse extractAndSaveMetadata(Media media) {
        if (media == null) {
            throw new IllegalArgumentException("Media entity must not be null");
        }

        Optional<MediaMetadata> existing = mediaMetadataRepository.findByMediaId(media.getId());
        if (existing.isPresent()) {
            return toResponse(existing.get());
        }

        MediaMetadata metadata = extractMetadataEntity(media);
        MediaMetadata saved;
        try {
            saved = mediaMetadataRepository.saveAndFlush(metadata);
        } catch (DataIntegrityViolationException dive) {
            log.warn("Concurrent metadata extraction race for media '{}'; returning existing record", media.getId());
            saved = mediaMetadataRepository.findByMediaId(media.getId()).orElseThrow(() -> dive);
        }

        log.info("Persisted metadata for media '{}': make={}, model={}, anomalies={}, forensicScore={}",
                media.getId(), saved.getCameraMake(), saved.getCameraModel(), saved.getAnomalyCount(), saved.getForensicScore());

        return toResponse(saved);
    }

    /**
     * Retrieves the forensic metadata record for a media asset with object-level authorization.
     * Generates metadata on-demand if not already extracted.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return safe {@link MediaMetadataResponse}
     */
    @Transactional
    public MediaMetadataResponse getMetadata(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaMetadata metadata = mediaMetadataRepository.findByMediaId(mediaId)
                .orElseGet(() -> extractAndSaveMetadataInternal(media));

        return toResponse(metadata);
    }

    /**
     * Explicitly re-extracts metadata and re-evaluates forensic anomaly rules for a media asset.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return updated {@link MediaMetadataResponse}
     */
    @Transactional
    public MediaMetadataResponse generateOrReevaluateMetadata(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaMetadata freshMetadata = extractMetadataEntity(media);
        Optional<MediaMetadata> existingOpt = mediaMetadataRepository.findByMediaId(mediaId);

        MediaMetadata toSave;
        if (existingOpt.isPresent()) {
            toSave = existingOpt.get();
            copyExtractedFields(freshMetadata, toSave);
        } else {
            toSave = freshMetadata;
        }

        MediaMetadata updated = mediaMetadataRepository.saveAndFlush(toSave);
        log.info("Re-evaluated metadata for media '{}': anomalies={}, forensicScore={}",
                mediaId, updated.getAnomalyCount(), updated.getForensicScore());

        return toResponse(updated);
    }

    /**
     * Retrieves the forensic anomaly report for a media asset with object-level authorization.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return {@link MetadataAnomalyReportResponse}
     */
    @Transactional
    public MetadataAnomalyReportResponse getAnomalyReport(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaMetadata metadata = mediaMetadataRepository.findByMediaId(mediaId)
                .orElseGet(() -> extractAndSaveMetadataInternal(media));

        List<ForensicAnomalyDto> anomalies = parseAnomalyFlags(metadata.getAnomalyFlags());
        String riskLevel = calculateRiskLevel(metadata.getForensicScore());

        String summary = String.format("Forensic evaluation completed with %d anomaly indicator(s). Overall metadata suspicion score: %.4f (%s).",
                metadata.getAnomalyCount(), metadata.getForensicScore(), riskLevel);

        return new MetadataAnomalyReportResponse(
                mediaId,
                metadata.isHasAnomalies(),
                metadata.getAnomalyCount(),
                metadata.getForensicScore(),
                riskLevel,
                anomalies,
                summary,
                metadata.getUpdatedAt() != null ? metadata.getUpdatedAt() : metadata.getCreatedAt()
        );
    }

    /**
     * Retrieves raw JSON metadata tree for a media asset with object-level authorization.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return raw JSON string
     */
    @Transactional
    public String getRawMetadataJson(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaMetadata metadata = mediaMetadataRepository.findByMediaId(mediaId)
                .orElseGet(() -> extractAndSaveMetadataInternal(media));

        return metadata.getRawJson() != null ? metadata.getRawJson() : "{}";
    }

    // Helper methods

    private MediaMetadata extractAndSaveMetadataInternal(Media media) {
        MediaMetadata metadata = extractMetadataEntity(media);
        try {
            return mediaMetadataRepository.saveAndFlush(metadata);
        } catch (DataIntegrityViolationException dive) {
            return mediaMetadataRepository.findByMediaId(media.getId()).orElseThrow(() -> dive);
        }
    }

    private MediaMetadata extractMetadataEntity(Media media) {
        ExtractedMetadata extracted;
        try (InputStream is = storageService.load(media.getStoragePath())) {
            extracted = extractorService.extractMetadata(is, media.getOriginalFilename(), media.getMimeType());
        } catch (Exception e) {
            log.warn("Failed to load/extract metadata from storage for media '{}': {}", media.getId(), e.getMessage());
            extracted = new ExtractedMetadata();
            extracted.setRawJson("{}");
        }

        MetadataAnomalyEvaluator.EvaluationResult eval = anomalyEvaluator.evaluate(media, extracted);
        String anomalyFlagsJson;
        try {
            anomalyFlagsJson = objectMapper.writeValueAsString(eval.anomalies());
        } catch (Exception e) {
            log.error("Failed to serialize anomaly flags to JSON", e);
            anomalyFlagsJson = "[]";
        }

        MediaMetadata entity = new MediaMetadata(media);
        entity.setCameraMake(extracted.getCameraMake());
        entity.setCameraModel(extracted.getCameraModel());
        entity.setLensModel(extracted.getLensModel());
        entity.setSoftwareTag(extracted.getSoftwareTag());
        entity.setCapturedAt(extracted.getCapturedAt());
        entity.setModifiedAt(extracted.getModifiedAt());
        entity.setGpsLatitude(extracted.getGpsLatitude());
        entity.setGpsLongitude(extracted.getGpsLongitude());
        entity.setGpsAltitude(extracted.getGpsAltitude());
        entity.setWidth(extracted.getWidth());
        entity.setHeight(extracted.getHeight());
        entity.setDurationSeconds(extracted.getDurationSeconds());
        entity.setBitrate(extracted.getBitrate());
        entity.setFrameRate(extracted.getFrameRate());
        entity.setVideoCodec(extracted.getVideoCodec());
        entity.setAudioCodec(extracted.getAudioCodec());
        entity.setAudioSampleRate(extracted.getAudioSampleRate());
        entity.setAudioChannels(extracted.getAudioChannels());
        entity.setContainerFormat(extracted.getContainerFormat());
        entity.setRawJson(extracted.getRawJson());
        entity.setAnomalyFlags(anomalyFlagsJson);
        entity.setHasAnomalies(!eval.anomalies().isEmpty());
        entity.setAnomalyCount(eval.anomalies().size());
        entity.setForensicScore(eval.forensicScore());
        entity.setExtractionEngine(extracted.getExtractionEngine());

        return entity;
    }

    private void copyExtractedFields(MediaMetadata source, MediaMetadata target) {
        target.setCameraMake(source.getCameraMake());
        target.setCameraModel(source.getCameraModel());
        target.setLensModel(source.getLensModel());
        target.setSoftwareTag(source.getSoftwareTag());
        target.setCapturedAt(source.getCapturedAt());
        target.setModifiedAt(source.getModifiedAt());
        target.setGpsLatitude(source.getGpsLatitude());
        target.setGpsLongitude(source.getGpsLongitude());
        target.setGpsAltitude(source.getGpsAltitude());
        target.setWidth(source.getWidth());
        target.setHeight(source.getHeight());
        target.setDurationSeconds(source.getDurationSeconds());
        target.setBitrate(source.getBitrate());
        target.setFrameRate(source.getFrameRate());
        target.setVideoCodec(source.getVideoCodec());
        target.setAudioCodec(source.getAudioCodec());
        target.setAudioSampleRate(source.getAudioSampleRate());
        target.setAudioChannels(source.getAudioChannels());
        target.setContainerFormat(source.getContainerFormat());
        target.setRawJson(source.getRawJson());
        target.setAnomalyFlags(source.getAnomalyFlags());
        target.setHasAnomalies(source.isHasAnomalies());
        target.setAnomalyCount(source.getAnomalyCount());
        target.setForensicScore(source.getForensicScore());
        target.setExtractionEngine(source.getExtractionEngine());
    }

    /**
     * Authorizes caller access to the target media asset (IDOR protection).
     * Standard users and researchers may access their own uploads; elevated roles may access any media.
     */
    private Media authorizeAndGetMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access media metadata");
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
            log.warn("IDOR attempt blocked on metadata query: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's metadata.");
        }

        return media;
    }

    private MediaMetadataResponse toResponse(MediaMetadata metadata) {
        List<ForensicAnomalyDto> anomalies = parseAnomalyFlags(metadata.getAnomalyFlags());
        String riskLevel = calculateRiskLevel(metadata.getForensicScore());

        return new MediaMetadataResponse(
                metadata.getId(),
                metadata.getMedia().getId(),
                metadata.getCameraMake(),
                metadata.getCameraModel(),
                metadata.getLensModel(),
                metadata.getSoftwareTag(),
                metadata.getCapturedAt(),
                metadata.getModifiedAt(),
                metadata.getGpsLatitude(),
                metadata.getGpsLongitude(),
                metadata.getGpsAltitude(),
                metadata.getWidth(),
                metadata.getHeight(),
                metadata.getDurationSeconds(),
                metadata.getBitrate(),
                metadata.getFrameRate(),
                metadata.getVideoCodec(),
                metadata.getAudioCodec(),
                metadata.getAudioSampleRate(),
                metadata.getAudioChannels(),
                metadata.getContainerFormat(),
                anomalies,
                metadata.isHasAnomalies(),
                metadata.getAnomalyCount(),
                metadata.getForensicScore(),
                riskLevel,
                metadata.getExtractionEngine(),
                metadata.getCreatedAt(),
                metadata.getUpdatedAt()
        );
    }

    private List<ForensicAnomalyDto> parseAnomalyFlags(String anomalyFlagsJson) {
        if (anomalyFlagsJson == null || anomalyFlagsJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(anomalyFlagsJson, new TypeReference<List<ForensicAnomalyDto>>() {});
        } catch (Exception e) {
            log.warn("Failed to parse anomaly flags JSON: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private String calculateRiskLevel(double score) {
        if (score <= 0.0) {
            return "CLEAN";
        } else if (score < 0.50) {
            return "SUSPICIOUS";
        } else {
            return "HIGH_RISK";
        }
    }
}
