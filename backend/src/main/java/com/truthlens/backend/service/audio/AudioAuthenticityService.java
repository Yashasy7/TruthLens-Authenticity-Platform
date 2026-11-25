package com.truthlens.backend.service.audio;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.AudioAnalysisResponse;
import com.truthlens.backend.dto.AudioEvidenceDto;
import com.truthlens.backend.dto.AudioSpliceMarkerDto;
import com.truthlens.backend.dto.FastApiAudioAnalysisResponse;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AudioAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.AudioAnalysisRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageKeyGenerator;
import com.truthlens.backend.service.storage.StorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Core business service for audio authenticity, voice cloning detection, and acoustic forensics (Module 07).
 */
@Service
public class AudioAuthenticityService {

    private static final Logger log = LoggerFactory.getLogger(AudioAuthenticityService.class);

    private final AudioAnalysisRepository audioAnalysisRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final StorageKeyGenerator storageKeyGenerator;
    private final AudioAiServiceClient audioAiServiceClient;
    private final ObjectMapper objectMapper;

    @Autowired
    public AudioAuthenticityService(
            AudioAnalysisRepository audioAnalysisRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            StorageKeyGenerator storageKeyGenerator,
            AudioAiServiceClient audioAiServiceClient,
            ObjectMapper objectMapper) {
        this.audioAnalysisRepository = audioAnalysisRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.storageKeyGenerator = storageKeyGenerator;
        this.audioAiServiceClient = audioAiServiceClient;
        this.objectMapper = objectMapper;
    }

    public AudioAuthenticityService(
            AudioAnalysisRepository audioAnalysisRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            AudioAiServiceClient audioAiServiceClient,
            ObjectMapper objectMapper) {
        this(
                audioAnalysisRepository,
                mediaRepository,
                userRepository,
                storageService,
                new StorageKeyGenerator(),
                audioAiServiceClient,
                objectMapper
        );
    }

    /**
     * Retrieves audio authenticity findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link AudioAnalysisResponse}
     */
    @Transactional
    public AudioAnalysisResponse getAudioAnalysis(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return audioAnalysisRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeAnalysis(media));
    }

    /**
     * Explicitly re-triggers audio authenticity analysis for an audio asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link AudioAnalysisResponse}
     */
    @Transactional
    public AudioAnalysisResponse reanalyzeAudio(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeAnalysis(media);
    }

    /**
     * Retrieves the forensic acoustic evidence and metrics for an audio asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return {@link AudioEvidenceDto}
     */
    @Transactional(readOnly = true)
    public AudioEvidenceDto getEvidence(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        AudioAnalysis analysis = audioAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No audio analysis record found for media id: " + mediaId));

        return parseEvidence(analysis);
    }

    /**
     * Retrieves the detected audio splice markers for an audio asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return list of {@link AudioSpliceMarkerDto}
     */
    @Transactional(readOnly = true)
    public List<AudioSpliceMarkerDto> getSpliceMarkers(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        AudioAnalysis analysis = audioAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No audio analysis record found for media id: " + mediaId));

        return parseSpliceMarkers(analysis.getSpliceMarkersJson());
    }

    /**
     * Streams the persisted Mel-spectrogram PNG artifact for authorized callers.
     *
     * @param mediaId          UUID of the media asset
     * @param artifactType     currently "spectrogram"
     * @param currentUserEmail email of the authenticated caller
     * @return InputStream to stream the PNG artifact
     */
    @Transactional(readOnly = true)
    public InputStream getArtifactStream(UUID mediaId, String artifactType, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        AudioAnalysis analysis = audioAnalysisRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No audio analysis record found for media id: " + mediaId));

        if (!"spectrogram".equalsIgnoreCase(artifactType)) {
            throw new IllegalArgumentException("Unsupported artifact type: '" + artifactType + "'. Supported types: 'spectrogram'");
        }

        String storageKey = analysis.getSpectrogramUrl();
        if (storageKey == null || storageKey.isBlank() || !storageService.exists(storageKey)) {
            throw new MediaNotFoundException("Visual artifact '" + artifactType + "' not found for media id: " + mediaId);
        }

        return storageService.load(storageKey);
    }

    // -------------------------------------------------------------------------
    // Internal Analysis Execution
    // -------------------------------------------------------------------------

    private AudioAnalysisResponse executeAnalysis(Media media) {
        UUID mediaId = media.getId();
        log.info("Starting audio authenticity analysis for media ID: {}", mediaId);

        byte[] audioBytes;
        try (InputStream is = storageService.load(media.getStoragePath())) {
            audioBytes = is.readAllBytes();
        } catch (Exception e) {
            log.error("Failed to read audio file from storage for media ID: {}", mediaId, e);
            throw new StorageException("Unable to read audio file from storage for analysis", e);
        }

        FastApiAudioAnalysisResponse aiResult;
        try {
            aiResult = audioAiServiceClient.analyzeAudio(audioBytes, media.getOriginalFilename(), media.getMimeType());
        } catch (AiServiceException e) {
            log.error("AI service failure while analyzing audio media ID {}: {}", mediaId, e.getMessage());
            saveFailedAnalysis(media, e.getMessage());
            throw e;
        }

        // Persist spectrogram PNG artifact safely into isolated storage when available
        String spectrogramStorageKey = null;
        if (aiResult.getSpectrogramBase64() != null && !aiResult.getSpectrogramBase64().isBlank()) {
            spectrogramStorageKey = storeSpectrogramArtifact(aiResult.getSpectrogramBase64());
        }
        if (spectrogramStorageKey == null && aiResult.getSpectrogramUrl() != null && !aiResult.getSpectrogramUrl().isBlank()) {
            spectrogramStorageKey = aiResult.getSpectrogramUrl();
        }

        boolean modelUnavailable = "MODEL_UNAVAILABLE".equalsIgnoreCase(aiResult.getStatus())
                || aiResult.getSyntheticVoiceProb() == null
                || (aiResult.getEvidence() != null
                    && aiResult.getEvidence().details() != null
                    && Boolean.FALSE.equals(aiResult.getEvidence().details().get("checkpoint_loaded")));

        Optional<AudioAnalysis> existingOpt = audioAnalysisRepository.findByMediaId(mediaId);
        AudioAnalysis analysis = existingOpt.orElseGet(() -> new AudioAnalysis(media));

        double probToPersist = (aiResult.getSyntheticVoiceProb() != null) ? aiResult.getSyntheticVoiceProb() : 0.0;
        analysis.setSyntheticVoiceProb(probToPersist);
        analysis.setSpectrogramUrl(spectrogramStorageKey);
        analysis.setPitchVariance(aiResult.getPitchVariance());
        double phaseDisc = (aiResult.getEvidence() != null) ? aiResult.getEvidence().phaseDiscontinuityScore() : 0.0;
        analysis.setPhaseDiscontinuity(phaseDisc);
        analysis.setAnalysisStatus(modelUnavailable ? AnalysisStatus.FAILED : AnalysisStatus.COMPLETED);
        analysis.setModelName(aiResult.getModelName());
        analysis.setModelVersion(aiResult.getModelVersion());

        try {
            analysis.setSpliceMarkersJson(objectMapper.writeValueAsString(aiResult.getSpliceMarkers()));
            analysis.setEvidenceJson(objectMapper.writeValueAsString(aiResult.getEvidence()));
        } catch (Exception e) {
            log.warn("Failed to serialize audio evidence JSON for media ID {}: {}", mediaId, e.getMessage());
            analysis.setSpliceMarkersJson("[]");
            analysis.setEvidenceJson("{}");
        }

        try {
            AudioAnalysis saved = audioAnalysisRepository.saveAndFlush(analysis);
            log.info("Completed audio authenticity analysis for media ID: {} (syntheticVoiceProb={}, pitchVariance={})",
                    mediaId, saved.getSyntheticVoiceProb(), saved.getPitchVariance());
            return toResponse(saved, aiResult.getSpectrogramBase64());
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent audio analysis persist conflict on media ID {}, reloading existing record", mediaId);
            return audioAnalysisRepository.findByMediaId(mediaId)
                    .map(this::toResponse)
                    .orElseThrow(() -> new IllegalStateException("Failed to retrieve concurrent audio analysis result", e));
        }
    }

    private String storeSpectrogramArtifact(String base64Content) {
        try {
            byte[] bytes = Base64.getDecoder().decode(base64Content);
            String storageKey = storageKeyGenerator.generateKey(MediaType.AUDIO, "image/png");
            return storageService.store(new ByteArrayInputStream(bytes), storageKey, "image/png", bytes.length);
        } catch (Exception e) {
            log.warn("Failed to decode or store spectrogram PNG artifact: {}", e.getMessage());
            return null;
        }
    }

    private void saveFailedAnalysis(Media media, String errorMessage) {
        try {
            Optional<AudioAnalysis> existingOpt = audioAnalysisRepository.findByMediaId(media.getId());
            AudioAnalysis analysis = existingOpt.orElseGet(() -> new AudioAnalysis(media));
            analysis.setAnalysisStatus(AnalysisStatus.FAILED);
            analysis.setSyntheticVoiceProb(0.0);
            analysis.setPitchVariance(0.0);
            analysis.setPhaseDiscontinuity(0.0);
            analysis.setSpliceMarkersJson("[]");
            analysis.setEvidenceJson(objectMapper.writeValueAsString(Map.of("error", errorMessage != null ? errorMessage : "Unknown error")));
            audioAnalysisRepository.saveAndFlush(analysis);
        } catch (Exception ex) {
            log.warn("Failed to record FAILED status for audio media ID {}: {}", media.getId(), ex.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access audio analysis");
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
            log.warn("IDOR attempt blocked on audio analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's analysis.");
        }

        if (media.getMediaType() != MediaType.AUDIO) {
            throw new InvalidMediaException("Audio authenticity analysis is only supported for audio assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private AudioAnalysisResponse toResponse(AudioAnalysis entity) {
        return toResponse(entity, null);
    }

    private AudioAnalysisResponse toResponse(AudioAnalysis entity, String spectrogramBase64) {
        List<AudioSpliceMarkerDto> markers = parseSpliceMarkers(entity.getSpliceMarkersJson());
        AudioEvidenceDto evidence = parseEvidence(entity);
        String assessment = computeAssessment(entity, evidence);

        String resolvedSpectrogramUrl = null;
        if (entity.getSpectrogramUrl() != null && !entity.getSpectrogramUrl().isBlank()) {
            resolvedSpectrogramUrl = "/api/media/" + entity.getMedia().getId() + "/audio-analysis/artifacts/spectrogram";
        }

        return new AudioAnalysisResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getSyntheticVoiceProb(),
                resolvedSpectrogramUrl,
                spectrogramBase64,
                entity.getPitchVariance(),
                entity.getPhaseDiscontinuity(),
                assessment,
                entity.getAnalysisStatus(),
                entity.getModelName(),
                entity.getModelVersion(),
                markers,
                evidence,
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private List<AudioSpliceMarkerDto> parseSpliceMarkers(String json) {
        if (json != null && !json.isBlank()) {
            try {
                return objectMapper.readValue(json, new TypeReference<List<AudioSpliceMarkerDto>>() {});
            } catch (Exception e) {
                log.debug("Could not deserialize splice markers JSON: {}", e.getMessage());
            }
        }
        return Collections.emptyList();
    }

    private AudioEvidenceDto parseEvidence(AudioAnalysis entity) {
        if (entity.getEvidenceJson() != null && !entity.getEvidenceJson().isBlank()) {
            try {
                return objectMapper.readValue(entity.getEvidenceJson(), AudioEvidenceDto.class);
            } catch (Exception e) {
                log.debug("Could not deserialize audio evidence JSON: {}", e.getMessage());
            }
        }

        List<AudioSpliceMarkerDto> markers = parseSpliceMarkers(entity.getSpliceMarkersJson());
        return new AudioEvidenceDto(
                0.0,
                0.0,
                entity.getPitchVariance(),
                0.0,
                0.0,
                0.0,
                0.0,
                entity.getPhaseDiscontinuity(),
                markers,
                Map.of("synthetic_voice_prob", entity.getSyntheticVoiceProb(), "analysis_status", entity.getAnalysisStatus().name())
        );
    }

    private String computeAssessment(AudioAnalysis entity, AudioEvidenceDto evidence) {
        AnalysisStatus status = entity.getAnalysisStatus();
        String modelVersion = entity.getModelVersion();
        Map<String, Object> details = (evidence != null) ? evidence.details() : null;

        boolean checkpointExplicitlyUnavailable = details != null && Boolean.FALSE.equals(details.get("checkpoint_loaded"));
        boolean versionUntrainedOrUnavailable = modelVersion != null && (
                modelVersion.contains("untrained") || modelVersion.contains("unavailable")
        );

        if (checkpointExplicitlyUnavailable || versionUntrainedOrUnavailable) {
            return "MODEL_UNAVAILABLE_INCONCLUSIVE";
        }
        if (status == AnalysisStatus.FAILED) {
            return "ANALYSIS_FAILED";
        }
        if (status == AnalysisStatus.PENDING || status == AnalysisStatus.PROCESSING) {
            return "IN_PROGRESS";
        }

        // Preserve explicit FastAPI verdict_category when available and verified
        if (details != null && details.get("verdict_category") instanceof String vc && !vc.isBlank()) {
            if ("Inconclusive".equalsIgnoreCase(vc)) {
                return "INCONCLUSIVE";
            }
            if ("Potentially Spliced".equalsIgnoreCase(vc)) {
                return "POTENTIALLY_SPLICED";
            }
            if ("Potentially Synthetic Voice".equalsIgnoreCase(vc)) {
                return entity.getSyntheticVoiceProb() >= 0.75
                        ? "HIGH_SYNTHETIC_VOICE_RISK"
                        : "SUSPICIOUS_VOICE_CLONING_INDICATORS";
            }
            if ("Likely Authentic".equalsIgnoreCase(vc)) {
                if (modelVersion == null || modelVersion.isBlank()) {
                    return "MODEL_UNAVAILABLE_INCONCLUSIVE";
                }
                return "LIKELY_AUTHENTIC_AUDIO";
            }
        }

        double syntheticProb = entity.getSyntheticVoiceProb();
        if (syntheticProb >= 0.75) {
            return "HIGH_SYNTHETIC_VOICE_RISK";
        }
        if (syntheticProb >= 0.50) {
            return "SUSPICIOUS_VOICE_CLONING_INDICATORS";
        }
        if (syntheticProb <= 0.25) {
            if (modelVersion == null || modelVersion.isBlank()) {
                return "MODEL_UNAVAILABLE_INCONCLUSIVE";
            }
            return "LIKELY_AUTHENTIC_AUDIO";
        }
        return "INCONCLUSIVE";
    }
}
