package com.truthlens.backend.service.claim;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.ClaimAnalysisResponse;
import com.truthlens.backend.dto.ClaimDto;
import com.truthlens.backend.dto.ClaimEntityDto;
import com.truthlens.backend.dto.ClaimEvidenceDto;
import com.truthlens.backend.dto.FastApiClaimResponse;
import com.truthlens.backend.dto.FastApiStructuredClaim;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Claim;
import com.truthlens.backend.entity.ClaimEntityType;
import com.truthlens.backend.entity.ClaimSourceType;
import com.truthlens.backend.entity.ClaimType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.OcrResult;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.Transcript;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.ClaimRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.OcrResultRepository;
import com.truthlens.backend.repository.TranscriptRepository;
import com.truthlens.backend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Core business service for Text & Claim Analysis (Module 11).
 *
 * <p>Consumes extracted text from OCR (Module 09) and Speech-to-Text Transcripts (Module 10)
 * to perform Named Entity Recognition (NER), sentence classification, and semantic claim
 * decomposition into Subject, Action, and Value triples.</p>
 */
@Service
public class TextClaimAnalysisService {

    private static final Logger log = LoggerFactory.getLogger(TextClaimAnalysisService.class);

    private final ClaimRepository claimRepository;
    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final OcrResultRepository ocrResultRepository;
    private final TranscriptRepository transcriptRepository;
    private final ClaimAiServiceClient claimAiServiceClient;
    private final ObjectMapper objectMapper;

    public TextClaimAnalysisService(
            ClaimRepository claimRepository,
            MediaRepository mediaRepository,
            UserRepository userRepository,
            OcrResultRepository ocrResultRepository,
            TranscriptRepository transcriptRepository,
            ClaimAiServiceClient claimAiServiceClient,
            ObjectMapper objectMapper) {
        this.claimRepository = claimRepository;
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.ocrResultRepository = ocrResultRepository;
        this.transcriptRepository = transcriptRepository;
        this.claimAiServiceClient = claimAiServiceClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieves claims for a target media asset.
     * Reuses cached records if already extracted; executes on-demand analysis if absent.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link ClaimAnalysisResponse}
     */
    @Transactional
    public ClaimAnalysisResponse getClaims(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);

        List<Claim> existingClaims = claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId);
        if (!existingClaims.isEmpty()) {
            return toResponse(media, existingClaims, null);
        }

        return executeClaimExtraction(media, null);
    }

    /**
     * Re-triggers claim analysis on a target media asset, replacing existing claims.
     *
     * @param mediaId          UUID of the media asset
     * @param currentUserEmail email of the authenticated caller
     * @param requestedSource  optional explicit source type hint (OCR, TRANSCRIPT, COMBINED)
     * @return fresh {@link ClaimAnalysisResponse}
     */
    @Transactional
    public ClaimAnalysisResponse reanalyzeClaims(UUID mediaId, String currentUserEmail, ClaimSourceType requestedSource) {
        Media media = authorizeAndValidateMedia(mediaId, currentUserEmail);
        claimRepository.deleteByMediaId(mediaId);
        return executeClaimExtraction(media, requestedSource);
    }

    /**
     * Retrieves an individual claim by ID with authorization verification.
     *
     * @param mediaId          UUID of the media asset
     * @param claimId          UUID of the claim record
     * @param currentUserEmail email of the authenticated caller
     * @return structured {@link ClaimDto}
     */
    @Transactional(readOnly = true)
    public ClaimDto getClaimById(UUID mediaId, UUID claimId, String currentUserEmail) {
        authorizeAndValidateMedia(mediaId, currentUserEmail);

        Claim claim = claimRepository.findById(claimId)
                .orElseThrow(() -> new MediaNotFoundException("Claim record not found with id: " + claimId));

        if (!claim.getMedia().getId().equals(mediaId)) {
            throw new InvalidMediaException("Claim " + claimId + " does not belong to media " + mediaId);
        }

        return toDto(claim);
    }

    /**
     * Executes ad-hoc claim extraction on arbitrary input text without requiring a saved media asset.
     *
     * @param text             raw input text
     * @param sourceType       origin identifier (DIRECT_TEXT, OCR, TRANSCRIPT)
     * @param language         language hint
     * @param currentUserEmail email of the authenticated caller
     * @return transient {@link ClaimAnalysisResponse}
     */
    public ClaimAnalysisResponse analyzeDirectText(String text, String sourceType, String language, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to analyze text");
        }

        if (text == null || text.isBlank()) {
            return new ClaimAnalysisResponse(
                    null,
                    ClaimSourceType.DIRECT_TEXT,
                    0,
                    0,
                    0,
                    Collections.emptyList(),
                    Collections.emptyList(),
                    new ClaimEvidenceDto("spaCy-en_core_web_sm", 0, 0, 0, 0.0, Map.of("is_empty", true)),
                    AnalysisStatus.COMPLETED,
                    OffsetDateTime.now(ZoneOffset.UTC)
            );
        }

        FastApiClaimResponse aiResponse = claimAiServiceClient.analyzeClaims(
                text,
                sourceType != null ? sourceType : "DIRECT_TEXT",
                language != null ? language : "en"
        );

        List<ClaimDto> claimDtos = aiResponse.getClaims().stream()
                .map(this::toTransientDto)
                .collect(Collectors.toList());

        return new ClaimAnalysisResponse(
                null,
                ClaimSourceType.DIRECT_TEXT,
                text.length(),
                aiResponse.getSentencesCount(),
                aiResponse.getClaimsCount(),
                claimDtos,
                aiResponse.getEntities(),
                aiResponse.getEvidence(),
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    // -------------------------------------------------------------------------
    // Execution & Persistence
    // -------------------------------------------------------------------------

    private ClaimAnalysisResponse executeClaimExtraction(Media media, ClaimSourceType requestedSource) {
        ResolvedSourceText sourceText = resolveSourceText(media, requestedSource);

        if (sourceText.text.isBlank()) {
            log.info("No source text available to extract claims for media {}", media.getId());
            return new ClaimAnalysisResponse(
                    media.getId(),
                    sourceText.sourceType,
                    0,
                    0,
                    0,
                    Collections.emptyList(),
                    Collections.emptyList(),
                    new ClaimEvidenceDto("spaCy-en_core_web_sm", 0, 0, 0, 0.0, Map.of("no_text", true)),
                    AnalysisStatus.COMPLETED,
                    OffsetDateTime.now(ZoneOffset.UTC)
            );
        }

        try {
            FastApiClaimResponse aiResponse = claimAiServiceClient.analyzeClaims(
                    sourceText.text,
                    sourceText.sourceType.name(),
                    "en"
            );

            List<Claim> entitiesToSave = new ArrayList<>();
            for (FastApiStructuredClaim sc : aiResponse.getClaims()) {
                String entitiesJson = serializeEntities(sc.getEntities());
                Claim claimEntity = new Claim(
                        media,
                        sc.getClaimText(),
                        sc.getNormalizedClaimText() != null ? sc.getNormalizedClaimText() : sc.getClaimText(),
                        parseClaimType(sc.getClaimType()),
                        sc.getSubject(),
                        sc.getAction(),
                        sc.getValue(),
                        parseEntityType(sc.getEntityType()),
                        sc.getConfidenceScore(),
                        sc.getClaimHash(),
                        sourceText.sourceType,
                        sc.getSentenceIndex(),
                        sc.getStartChar(),
                        sc.getEndChar(),
                        entitiesJson,
                        AnalysisStatus.COMPLETED
                );
                entitiesToSave.add(claimEntity);
            }

            List<Claim> savedEntities = claimRepository.saveAll(entitiesToSave);
            log.info("Persisted {} structured claims for media {}", savedEntities.size(), media.getId());

            return toResponse(media, savedEntities, aiResponse);

        } catch (AiServiceException e) {
            log.error("AI Claim service error during claim extraction for media {}: {}", media.getId(), e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Unexpected error during claim extraction for media {}: {}", media.getId(), e.getMessage(), e);
            throw new AiServiceException("Claim extraction pipeline failed: " + e.getMessage(), e);
        }
    }

    private ResolvedSourceText resolveSourceText(Media media, ClaimSourceType requestedSource) {
        Optional<Transcript> transcriptOpt = transcriptRepository.findByMediaId(media.getId());
        Optional<OcrResult> ocrOpt = ocrResultRepository.findByMediaId(media.getId());

        String transcriptText = transcriptOpt.map(Transcript::getFullText).orElse("").trim();
        String ocrText = ocrOpt.map(OcrResult::getExtractedText).orElse("").trim();

        if (requestedSource == ClaimSourceType.TRANSCRIPT && !transcriptText.isEmpty()) {
            return new ResolvedSourceText(transcriptText, ClaimSourceType.TRANSCRIPT);
        }
        if (requestedSource == ClaimSourceType.OCR && !ocrText.isEmpty()) {
            return new ResolvedSourceText(ocrText, ClaimSourceType.OCR);
        }

        // If both present
        if (!transcriptText.isEmpty() && !ocrText.isEmpty()) {
            String combined = transcriptText + "\n\n" + ocrText;
            return new ResolvedSourceText(combined, ClaimSourceType.COMBINED);
        }

        if (!transcriptText.isEmpty()) {
            return new ResolvedSourceText(transcriptText, ClaimSourceType.TRANSCRIPT);
        }

        if (!ocrText.isEmpty()) {
            return new ResolvedSourceText(ocrText, ClaimSourceType.OCR);
        }

        return new ResolvedSourceText("", requestedSource != null ? requestedSource : ClaimSourceType.DIRECT_TEXT);
    }

    private static class ResolvedSourceText {
        final String text;
        final ClaimSourceType sourceType;

        ResolvedSourceText(String text, ClaimSourceType sourceType) {
            this.text = text;
            this.sourceType = sourceType;
        }
    }

    // -------------------------------------------------------------------------
    // Authorization & Validation
    // -------------------------------------------------------------------------

    private Media authorizeAndValidateMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access claims analysis");
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
            log.warn("IDOR attempt blocked on Claim analysis: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's claims.");
        }

        return media;
    }

    // -------------------------------------------------------------------------
    // Response & DTO Mapping
    // -------------------------------------------------------------------------

    private ClaimAnalysisResponse toResponse(Media media, List<Claim> entities, FastApiClaimResponse aiResponse) {
        List<ClaimDto> dts = entities.stream()
                .map(this::toDto)
                .collect(Collectors.toList());

        List<ClaimEntityDto> allEntities = new ArrayList<>();
        if (aiResponse != null && aiResponse.getEntities() != null) {
            allEntities = aiResponse.getEntities();
        } else {
            // Aggregate from entities_json
            for (ClaimDto dto : dts) {
                allEntities.addAll(dto.getEntities());
            }
        }

        ClaimEvidenceDto evidence = (aiResponse != null && aiResponse.getEvidence() != null)
                ? aiResponse.getEvidence()
                : new ClaimEvidenceDto(
                        "spaCy-en_core_web_sm",
                        entities.size(),
                        entities.size(),
                        allEntities.size(),
                        0.0,
                        Map.of("loaded_from_db", true)
                );

        ClaimSourceType sourceType = entities.isEmpty() ? ClaimSourceType.DIRECT_TEXT : entities.get(0).getSourceType();
        OffsetDateTime created = entities.isEmpty() ? OffsetDateTime.now(ZoneOffset.UTC) : entities.get(0).getCreatedAt();

        return new ClaimAnalysisResponse(
                media.getId(),
                sourceType,
                entities.stream().mapToInt(c -> c.getClaimText().length()).sum(),
                entities.size(),
                entities.size(),
                dts,
                allEntities,
                evidence,
                AnalysisStatus.COMPLETED,
                created
        );
    }

    private ClaimDto toDto(Claim entity) {
        List<ClaimEntityDto> entities = parseEntities(entity.getEntitiesJson());

        return new ClaimDto(
                entity.getId(),
                entity.getMedia().getId(),
                entity.getClaimText(),
                entity.getNormalizedClaimText(),
                entity.getClaimType(),
                entity.getSubject(),
                entity.getAction(),
                entity.getValue(),
                entity.getEntityType(),
                entity.getConfidenceScore(),
                entity.getClaimHash(),
                entity.getSourceType(),
                entity.getSentenceIndex(),
                entity.getStartChar(),
                entity.getEndChar(),
                entities,
                entity.getAnalysisStatus(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private ClaimDto toTransientDto(FastApiStructuredClaim sc) {
        return new ClaimDto(
                null,
                null,
                sc.getClaimText(),
                sc.getNormalizedClaimText(),
                parseClaimType(sc.getClaimType()),
                sc.getSubject(),
                sc.getAction(),
                sc.getValue(),
                parseEntityType(sc.getEntityType()),
                sc.getConfidenceScore(),
                sc.getClaimHash(),
                ClaimSourceType.DIRECT_TEXT,
                sc.getSentenceIndex(),
                sc.getStartChar(),
                sc.getEndChar(),
                sc.getEntities(),
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    private String serializeEntities(List<ClaimEntityDto> entities) {
        if (entities == null || entities.isEmpty()) {
            return "[]";
        }
        try {
            return objectMapper.writeValueAsString(entities);
        } catch (Exception e) {
            log.warn("Failed to serialize entities JSON: {}", e.getMessage());
            return "[]";
        }
    }

    private List<ClaimEntityDto> parseEntities(String json) {
        if (json == null || json.isBlank() || "[]".equals(json.trim())) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<ClaimEntityDto>>() {});
        } catch (Exception e) {
            log.warn("Failed to deserialize entities JSON: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private ClaimType parseClaimType(String str) {
        if (str == null) return ClaimType.FACTUAL_CLAIM;
        try {
            return ClaimType.valueOf(str.toUpperCase());
        } catch (Exception e) {
            return ClaimType.FACTUAL_CLAIM;
        }
    }

    private ClaimEntityType parseEntityType(String str) {
        if (str == null) return ClaimEntityType.GENERAL;
        try {
            return ClaimEntityType.valueOf(str.toUpperCase());
        } catch (Exception e) {
            return ClaimEntityType.GENERAL;
        }
    }
}
