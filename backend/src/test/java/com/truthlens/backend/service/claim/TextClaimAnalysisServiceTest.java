package com.truthlens.backend.service.claim;

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
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.OcrResult;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.Transcript;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.ClaimRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.OcrResultRepository;
import com.truthlens.backend.repository.TranscriptRepository;
import com.truthlens.backend.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("TextClaimAnalysisService — Business Logic & Security Tests")
class TextClaimAnalysisServiceTest {

    @Mock
    private ClaimRepository claimRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private OcrResultRepository ocrResultRepository;

    @Mock
    private TranscriptRepository transcriptRepository;

    @Mock
    private ClaimAiServiceClient claimAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private TextClaimAnalysisService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private User moderator;
    private User researcher;

    private Media videoMedia;
    private UUID mediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new TextClaimAnalysisService(
                claimRepository,
                mediaRepository,
                userRepository,
                ocrResultRepository,
                transcriptRepository,
                claimAiServiceClient,
                objectMapper
        );

        owner = new User("owner@truthlens.org", "pass123", "Owner User");
        setId(owner, UUID.randomUUID());
        owner.getRoles().add(new Role(RoleName.USER, "Standard User"));

        otherUser = new User("other@truthlens.org", "pass123", "Other User");
        setId(otherUser, UUID.randomUUID());
        otherUser.getRoles().add(new Role(RoleName.USER, "Standard User"));

        analyst = new User("analyst@truthlens.org", "pass123", "Analyst User");
        setId(analyst, UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Analyst User"));

        moderator = new User("moderator@truthlens.org", "pass123", "Moderator User");
        setId(moderator, UUID.randomUUID());
        moderator.getRoles().add(new Role(RoleName.MODERATOR, "Moderator User"));

        researcher = new User("researcher@truthlens.org", "pass123", "Researcher User");
        setId(researcher, UUID.randomUUID());
        researcher.getRoles().add(new Role(RoleName.RESEARCHER, "Researcher User"));

        mediaId = UUID.randomUUID();
        videoMedia = new Media(owner, "clip.mp4", "storage/clip.mp4", MediaType.VIDEO, "video/mp4", 1048576L, "sha256vid", UploadStatus.UPLOADED);
        setId(videoMedia, mediaId);
    }

    private void setId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    private FastApiClaimResponse buildSampleAiResponse() {
        FastApiStructuredClaim claim = new FastApiStructuredClaim(
                "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "the prime minister announced a $5 billion stimulus in london on monday.",
                "FACTUAL_CLAIM",
                "The Prime Minister",
                "announced",
                "a $5 billion stimulus",
                "MONEY",
                0.95,
                "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
                0,
                0,
                71,
                List.of(new ClaimEntityDto("London", "GPE", "LOCATION", 53, 59))
        );

        return new FastApiClaimResponse(
                "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "TRANSCRIPT",
                1,
                1,
                List.of(claim),
                List.of(new ClaimEntityDto("London", "GPE", "LOCATION", 53, 59)),
                new ClaimEvidenceDto("spaCy-en_core_web_sm", 1, 1, 1, 0.05, Map.of()),
                "COMPLETED",
                null
        );
    }

    @Test
    @DisplayName("getClaims: media owner retrieves claims on-demand when absent from DB")
    void getClaims_owner_onDemand_success() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId)).thenReturn(Collections.emptyList());

        Transcript transcript = new Transcript(
                videoMedia, "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "en", 0.95, 3.5, 1, 12, "[]", "{}", AnalysisStatus.COMPLETED
        );
        when(transcriptRepository.findByMediaId(mediaId)).thenReturn(Optional.of(transcript));
        when(ocrResultRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());

        when(claimAiServiceClient.analyzeClaims(any(), eq("TRANSCRIPT"), eq("en"))).thenReturn(buildSampleAiResponse());
        when(claimRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ClaimAnalysisResponse response = service.getClaims(mediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getClaimsCount()).isEqualTo(1);
        assertThat(response.getClaims().get(0).getClaimText()).contains("The Prime Minister announced");
        assertThat(response.getClaims().get(0).getClaimType()).isEqualTo(ClaimType.FACTUAL_CLAIM);
        verify(claimAiServiceClient).analyzeClaims(any(), eq("TRANSCRIPT"), eq("en"));
    }

    @Test
    @DisplayName("getClaims: returns cached claims from database without re-invoking AI service")
    void getClaims_cached_returnsExistingWithoutAiService() {
        Claim cachedClaim = new Claim(
                videoMedia, "Cached claim text", "cached claim text",
                ClaimType.FACTUAL_CLAIM, "Subject", "Action", "Value",
                ClaimEntityType.GENERAL, 0.90, "cachedhash123",
                ClaimSourceType.TRANSCRIPT, 0, 0, 17, "[]", AnalysisStatus.COMPLETED
        );

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId)).thenReturn(List.of(cachedClaim));

        ClaimAnalysisResponse response = service.getClaims(mediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getClaimsCount()).isEqualTo(1);
        assertThat(response.getClaims().get(0).getClaimText()).isEqualTo("Cached claim text");
        verify(claimAiServiceClient, never()).analyzeClaims(any(), any(), any());
    }

    @Test
    @DisplayName("reanalyzeClaims: deletes existing claims and triggers fresh extraction")
    void reanalyzeClaims_forcesDeletionAndNewAnalysis() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        Transcript transcript = new Transcript(
                videoMedia, "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "en", 0.95, 3.5, 1, 12, "[]", "{}", AnalysisStatus.COMPLETED
        );
        when(transcriptRepository.findByMediaId(mediaId)).thenReturn(Optional.of(transcript));
        when(ocrResultRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());

        when(claimAiServiceClient.analyzeClaims(any(), eq("TRANSCRIPT"), eq("en"))).thenReturn(buildSampleAiResponse());
        when(claimRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ClaimAnalysisResponse response = service.reanalyzeClaims(mediaId, owner.getEmail(), ClaimSourceType.TRANSCRIPT);

        assertThat(response).isNotNull();
        verify(claimRepository).deleteByMediaId(mediaId);
        verify(claimAiServiceClient).analyzeClaims(any(), eq("TRANSCRIPT"), eq("en"));
    }

    @Test
    @DisplayName("elevated roles: ROLE_ANALYST can access other user's media claims")
    void getClaims_analyst_canAccessOtherUserClaims() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));
        when(claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId)).thenReturn(Collections.emptyList());
        when(transcriptRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());
        when(ocrResultRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());

        ClaimAnalysisResponse response = service.getClaims(mediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getClaimsCount()).isEqualTo(0);
    }

    @Test
    @DisplayName("elevated roles: ROLE_MODERATOR can access other user's media claims")
    void getClaims_moderator_canAccessOtherUserClaims() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(moderator.getEmail())).thenReturn(Optional.of(moderator));
        when(claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId)).thenReturn(Collections.emptyList());
        when(transcriptRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());
        when(ocrResultRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());

        ClaimAnalysisResponse response = service.getClaims(mediaId, moderator.getEmail());

        assertThat(response).isNotNull();
    }

    @Test
    @DisplayName("IDOR protection: non-owner with ROLE_USER is blocked from accessing claims")
    void getClaims_idor_blocked_nonOwner_throwsAccessDeniedException() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getClaims(mediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");

        verify(claimRepository, never()).findByMediaIdOrderBySentenceIndexAsc(any());
        verify(claimAiServiceClient, never()).analyzeClaims(any(), any(), any());
    }

    @Test
    @DisplayName("IDOR protection: non-owner with ROLE_RESEARCHER is blocked from accessing claims")
    void getClaims_researcher_blocked_nonOwner_throwsAccessDeniedException() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(researcher.getEmail())).thenReturn(Optional.of(researcher));

        assertThatThrownBy(() -> service.getClaims(mediaId, researcher.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");
    }

    @Test
    @DisplayName("analyzeDirectText: executes ad-hoc text claim analysis without requiring media")
    void analyzeDirectText_success() {
        when(claimAiServiceClient.analyzeClaims(any(), eq("DIRECT_TEXT"), eq("en"))).thenReturn(buildSampleAiResponse());

        ClaimAnalysisResponse response = service.analyzeDirectText(
                "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "DIRECT_TEXT", "en", owner.getEmail()
        );

        assertThat(response).isNotNull();
        assertThat(response.getClaimsCount()).isEqualTo(1);
        assertThat(response.getClaims().get(0).getSubject()).isEqualTo("The Prime Minister");
    }

    @Test
    @DisplayName("getClaimById: validates claim belongs to the specified media")
    void getClaimById_wrongMedia_throwsInvalidMediaException() throws Exception {
        UUID claimId = UUID.randomUUID();
        Media otherMedia = new Media(owner, "other.mp4", "storage/other.mp4", MediaType.VIDEO, "video/mp4", 100L, "hash", UploadStatus.UPLOADED);
        setId(otherMedia, UUID.randomUUID());

        Claim claim = new Claim(otherMedia, "Text", "text", ClaimType.FACTUAL_CLAIM, "Subj", "Act", "Val", ClaimEntityType.GENERAL, 0.9, "hash", ClaimSourceType.TRANSCRIPT, 0, 0, 4, "[]", AnalysisStatus.COMPLETED);
        setId(claim, claimId);

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(claimRepository.findById(claimId)).thenReturn(Optional.of(claim));

        assertThatThrownBy(() -> service.getClaimById(mediaId, claimId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("does not belong to media");
    }

    @Test
    @DisplayName("source text resolution: combines OCR and Transcript text when both exist")
    void getClaims_combinesOcrAndTranscript() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(claimRepository.findByMediaIdOrderBySentenceIndexAsc(mediaId)).thenReturn(Collections.emptyList());

        Transcript transcript = new Transcript(videoMedia, "Spoken speech content.", "en", 0.9, 1.0, 1, 3, "[]", "{}", AnalysisStatus.COMPLETED);
        OcrResult ocrResult = new OcrResult(videoMedia, "Visual text overlay.", "en", 0.9, 1, "[]", "{}", AnalysisStatus.COMPLETED);

        when(transcriptRepository.findByMediaId(mediaId)).thenReturn(Optional.of(transcript));
        when(ocrResultRepository.findByMediaId(mediaId)).thenReturn(Optional.of(ocrResult));

        when(claimAiServiceClient.analyzeClaims(any(), eq("COMBINED"), eq("en"))).thenReturn(buildSampleAiResponse());
        when(claimRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ClaimAnalysisResponse response = service.getClaims(mediaId, owner.getEmail());

        assertThat(response).isNotNull();
        verify(claimAiServiceClient).analyzeClaims(eq("Spoken speech content.\n\nVisual text overlay."), eq("COMBINED"), eq("en"));
    }
}
