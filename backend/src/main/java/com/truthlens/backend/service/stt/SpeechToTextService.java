package com.truthlens.backend.service.stt;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiTranscriptResponse;
import com.truthlens.backend.dto.TranscriptEvidenceDto;
import com.truthlens.backend.dto.TranscriptResponse;
import com.truthlens.backend.dto.TranscriptSegmentDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.Transcript;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.TranscriptRepository;
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
 * Core business service for Speech-to-Text & Transcript Extraction (Module 10).
 *
 * <p>Enforces strict service-layer authorization and media validation:
 * <ul>
 *   <li>Only media owners or users with elevated roles (ANALYST, MODERATOR, ADMIN) can access or trigger transcription.</li>
 *   <li>Supports both {@link MediaType#AUDIO} and {@link MediaType#VIDEO} media assets.</li>
 * </ul>
 * </p>
 */
@Service
public class SpeechToTextService {

    private static final Logger log = LoggerFactory.getLogger(SpeechToTextService.class);

    private final TranscriptRepository transcriptRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final TranscriptAiServiceClient transcriptAiServiceClient;
    private final ObjectMapper objectMapper;

    public SpeechToTextService(
            TranscriptRepository transcriptRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            StorageService storageService,
            TranscriptAiServiceClient transcriptAiServiceClient,
            ObjectMapper objectMapper) {
        this.transcriptRepository = transcriptRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.transcriptAiServiceClient = transcriptAiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves Speech-to-Text findings for a media asset.
     * Reuses cached record if already analyzed; triggers on-demand transcription if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link TranscriptResponse}
     */
    @Transactional
    public TranscriptResponse getTranscript(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        return transcriptRepository.findByMediaId(mediaId)
                .map(this::toResponse)
                .orElseGet(() -> executeTranscription(media));
    }

    /**
     * Explicitly re-triggers Speech-to-Text transcription for a media asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return fresh {@link TranscriptResponse}
     */
    @Transactional
    public TranscriptResponse reanalyzeTranscript(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        return executeTranscription(media);
    }

    /**
     * Retrieves timestamped speech segments with phrase text and word-level alignment offsets.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return list of {@link TranscriptSegmentDto}
     */
    @Transactional(readOnly = true)
    public List<TranscriptSegmentDto> getSegments(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        Transcript transcript = transcriptRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No transcript analysis record found for media id: " + mediaId));

        return parseSegments(transcript.getTimestampSegmentsJson());
    }

    /**
     * Retrieves the raw full text transcript extracted from the audio/video media asset.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return raw transcribed full text string
     */
    @Transactional(readOnly = true)
    public String getFullText(UUID mediaId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        Transcript transcript = transcriptRepository.findByMediaId(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("No transcript analysis record found for media id: " + mediaId));

        return transcript.getFullText() != null ? transcript.getFullText() : "";
    }

    // -------------------------------------------------------------------------
    // Execution & Persistence
    // -------------------------------------------------------------------------

    private TranscriptResponse executeTranscription(Media media) {
        byte[] mediaBytes = loadMediaBytes(media);

        try {
            FastApiTranscriptResponse aiResponse = transcriptAiServiceClient.analyzeSpeechToText(
                    mediaBytes,
                    media.getOriginalFilename(),
                    media.getMimeType()
            );

            return persistTranscript(media, aiResponse);

        } catch (AiServiceException e) {
            log.error("AI service error during speech transcription for media {}: {}", media.getId(), e.getMessage());
            persistFailure(media, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Unexpected error during speech transcription for media {}: {}", media.getId(), e.getMessage(), e);
            persistFailure(media, e.getMessage());
            throw new AiServiceException("Speech-to-Text transcription pipeline failed: " + e.getMessage(), e);
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

    private TranscriptResponse persistTranscript(Media media, FastApiTranscriptResponse aiResponse) {
        String segmentsJson = null;
        try {
            if (aiResponse.getSegments() != null) {
                segmentsJson = objectMapper.writeValueAsString(aiResponse.getSegments());
            }
        } catch (Exception e) {
            log.warn("Failed to serialize transcript segments to JSON: {}", e.getMessage());
        }

        String evidenceJson = null;
        try {
            if (aiResponse.getEvidence() != null) {
                evidenceJson = objectMapper.writeValueAsString(aiResponse.getEvidence());
            }
        } catch (Exception e) {
            log.warn("Failed to serialize transcript evidence to JSON: {}", e.getMessage());
        }

        final String finalSegmentsJson = segmentsJson;
        final String finalEvidenceJson = evidenceJson;

        Transcript entity = transcriptRepository.findByMediaId(media.getId())
                .map(existing -> {
                    existing.setFullText(aiResponse.getFullText());
                    existing.setLanguage(aiResponse.getLanguage() != null ? aiResponse.getLanguage() : "en");
                    existing.setConfidenceScore(aiResponse.getConfidenceScore());
                    existing.setDurationSeconds(aiResponse.getDurationSeconds());
                    existing.setSegmentsCount(aiResponse.getSegmentsCount());
                    existing.setWordsCount(aiResponse.getWordsCount());
                    existing.setTimestampSegmentsJson(finalSegmentsJson);
                    existing.setEvidenceJson(finalEvidenceJson);
                    existing.setAnalysisStatus(AnalysisStatus.COMPLETED);
                    return existing;
                })
                .orElseGet(() -> new Transcript(
                        media,
                        aiResponse.getFullText(),
                        aiResponse.getLanguage(),
                        aiResponse.getConfidenceScore(),
                        aiResponse.getDurationSeconds(),
                        aiResponse.getSegmentsCount(),
                        aiResponse.getWordsCount(),
                        finalSegmentsJson,
                        finalEvidenceJson,
                        AnalysisStatus.COMPLETED
                ));

        try {
            entity = transcriptRepository.save(entity);
            log.info("Persisted Speech-to-Text transcript for media {}: segments={}, words={}, lang={}",
                    media.getId(), entity.getSegmentsCount(), entity.getWordsCount(), entity.getLanguage());
            return toResponse(entity);
        } catch (DataIntegrityViolationException e) {
            log.warn("Concurrent Speech-to-Text transcription detected for media {}; reloading existing record", media.getId());
            return transcriptRepository.findByMediaId(media.getId())
                    .map(this::toResponse)
                    .orElseThrow(() -> e);
        }
    }

    private void persistFailure(Media media, String errorMessage) {
        try {
            Transcript entity = transcriptRepository.findByMediaId(media.getId())
                    .orElseGet(() -> new Transcript(
                            media,
                            "",
                            "en",
                            0.0,
                            0.0,
                            0,
                            0,
                            "[]",
                            "{}",
                            AnalysisStatus.FAILED
                    ));
            entity.setAnalysisStatus(AnalysisStatus.FAILED);
            transcriptRepository.save(entity);
        } catch (Exception e) {
            log.warn("Failed to record Speech-to-Text analysis failure state for media {}: {}", media.getId(), e.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access speech transcript");
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
            log.warn("IDOR attempt blocked on Speech-to-Text transcript: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's transcript.");
        }

        if (media.getMediaType() != MediaType.AUDIO && media.getMediaType() != MediaType.VIDEO) {
            throw new InvalidMediaException("Speech-to-text transcription is only supported for audio and video assets. Target media type: " + media.getMediaType());
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response Mapping
    // -------------------------------------------------------------------------

    private TranscriptResponse toResponse(Transcript entity) {
        List<TranscriptSegmentDto> segments = parseSegments(entity.getTimestampSegmentsJson());
        TranscriptEvidenceDto evidence = parseEvidence(entity.getEvidenceJson());

        return new TranscriptResponse(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getFullText(),
                entity.getLanguage(),
                entity.getConfidenceScore(),
                entity.getDurationSeconds(),
                entity.getSegmentsCount(),
                entity.getWordsCount(),
                segments,
                evidence,
                entity.getAnalysisStatus(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private List<TranscriptSegmentDto> parseSegments(String json) {
        if (json == null || json.isBlank() || "[]".equals(json.trim())) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<TranscriptSegmentDto>>() {});
        } catch (Exception e) {
            log.warn("Failed to deserialize transcript segments JSON: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private TranscriptEvidenceDto parseEvidence(String json) {
        if (json == null || json.isBlank() || "{}".equals(json.trim())) {
            return new TranscriptEvidenceDto();
        }
        try {
            return objectMapper.readValue(json, TranscriptEvidenceDto.class);
        } catch (Exception e) {
            log.warn("Failed to deserialize transcript evidence JSON: {}", e.getMessage());
            return new TranscriptEvidenceDto();
        }
    }
}
