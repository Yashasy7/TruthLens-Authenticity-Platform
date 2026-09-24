package com.truthlens.backend.service.avsync;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.AvSyncAnalysisResponse;
import com.truthlens.backend.dto.AvSyncEvidenceDto;
import com.truthlens.backend.dto.FastApiAvSyncResponse;
import com.truthlens.backend.dto.MismatchSegmentDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AvSyncAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.AvSyncAnalysisRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.util.List;
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
@DisplayName("AvSyncAnalysisService — Unit & Security Tests")
class AvSyncAnalysisServiceTest {

    @Mock
    private AvSyncAnalysisRepository avSyncAnalysisRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private AvSyncAiServiceClient avSyncAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private AvSyncAnalysisService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media videoMedia;
    private Media imageMedia;
    private UUID videoMediaId;
    private UUID imageMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new AvSyncAnalysisService(
                avSyncAnalysisRepository,
                mediaRepository,
                userRepository,
                storageService,
                avSyncAiServiceClient,
                objectMapper
        );

        owner = new User("owner@truthlens.org", "hash", "Owner User");
        setEntityId(owner, UUID.randomUUID());
        owner.getRoles().add(new Role(RoleName.USER, "Standard User"));

        otherUser = new User("other@truthlens.org", "hash", "Other User");
        setEntityId(otherUser, UUID.randomUUID());
        otherUser.getRoles().add(new Role(RoleName.USER, "Standard User"));

        analyst = new User("analyst@truthlens.org", "hash", "Analyst User");
        setEntityId(analyst, UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Analyst"));

        videoMediaId = UUID.randomUUID();
        videoMedia = new Media(
                owner,
                "speech_video.mp4",
                "quarantine/video/speech_video.mp4",
                MediaType.VIDEO,
                "video/mp4",
                5242880L,
                "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
                UploadStatus.UPLOADED
        );
        setEntityId(videoMedia, videoMediaId);

        imageMediaId = UUID.randomUUID();
        imageMedia = new Media(
                owner,
                "photo.jpg",
                "quarantine/images/photo.jpg",
                MediaType.IMAGE,
                "image/jpeg",
                102400L,
                "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
                UploadStatus.UPLOADED
        );
        setEntityId(imageMedia, imageMediaId);
    }

    private void setEntityId(Object entity, UUID id) throws Exception {
        Field idField = entity.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(entity, id);
    }

    @Test
    @DisplayName("getAvSyncAnalysis: returns cached analysis if present without calling AI client")
    void getAvSyncAnalysis_cached_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        AvSyncAnalysis cached = new AvSyncAnalysis(videoMedia);
        cached.setSyncScore(0.85);
        cached.setLipOffsetMs(-20.0);
        cached.setConfidence(0.92);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        cached.setModelName("TruthLens-PyTorch-SyncNet-DualStream");

        when(avSyncAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(cached));

        AvSyncAnalysisResponse response = service.getAvSyncAnalysis(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getSyncScore()).isEqualTo(0.85);
        assertThat(response.getLipOffsetMs()).isEqualTo(-20.0);
        assertThat(response.getAssessment()).isEqualTo("SYNCHRONIZED");
        verify(avSyncAiServiceClient, never()).analyzeAvSync(any(), any(), any());
    }

    @Test
    @DisplayName("getAvSyncAnalysis: on-demand execution invokes AI service and persists result")
    void getAvSyncAnalysis_onDemand_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(avSyncAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        byte[] fakeBytes = new byte[]{1, 2, 3, 4};
        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(fakeBytes));

        FastApiAvSyncResponse aiResponse = new FastApiAvSyncResponse();
        aiResponse.setSyncScore(0.89);
        aiResponse.setLipOffsetMs(10.0);
        aiResponse.setConfidence(0.95);
        aiResponse.setModelName("TruthLens-PyTorch-SyncNet-DualStream");
        aiResponse.setModelVersion("TruthLens-SyncNet-v1.0-dev");
        aiResponse.setMismatchSegments(List.of(new MismatchSegmentDto(0.0, 1.0, 10.0, 0.9, "Consistent")));

        when(avSyncAiServiceClient.analyzeAvSync(eq(fakeBytes), eq("speech_video.mp4"), eq("video/mp4")))
                .thenReturn(aiResponse);

        when(avSyncAnalysisRepository.saveAndFlush(any(AvSyncAnalysis.class))).thenAnswer(inv -> inv.getArgument(0));

        AvSyncAnalysisResponse response = service.getAvSyncAnalysis(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getSyncScore()).isEqualTo(0.89);
        assertThat(response.getLipOffsetMs()).isEqualTo(10.0);
        assertThat(response.getAssessment()).isEqualTo("SYNCHRONIZED");
        assertThat(response.getMismatchSegments()).hasSize(1);
    }

    @Test
    @DisplayName("IDOR Protection: unauthorized non-owner non-analyst blocked with AccessDeniedException")
    void getAvSyncAnalysis_idor_blocked() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getAvSyncAnalysis(videoMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");

        verify(avSyncAnalysisRepository, never()).findByMediaId(any());
        verify(avSyncAiServiceClient, never()).analyzeAvSync(any(), any(), any());
    }

    @Test
    @DisplayName("Elevated Role Access: Analyst can view and analyze any user's video")
    void getAvSyncAnalysis_analyst_permitted() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));

        AvSyncAnalysis cached = new AvSyncAnalysis(videoMedia);
        cached.setSyncScore(0.90);
        when(avSyncAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(cached));

        AvSyncAnalysisResponse response = service.getAvSyncAnalysis(videoMediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getSyncScore()).isEqualTo(0.90);
    }

    @Test
    @DisplayName("Media Type Validation: non-video asset throws InvalidMediaException")
    void getAvSyncAnalysis_wrongMediaType_throwsException() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getAvSyncAnalysis(imageMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("only supported for video assets");
    }

    @Test
    @DisplayName("AI Failure Handling: records FAILED status in database when AI service throws error")
    void getAvSyncAnalysis_aiFailure_recordsFailedStatus() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(avSyncAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        byte[] fakeBytes = new byte[]{1, 2, 3, 4};
        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(fakeBytes));
        when(avSyncAiServiceClient.analyzeAvSync(any(), any(), any()))
                .thenThrow(new AiServiceException("FastAPI connection timeout"));

        assertThatThrownBy(() -> service.getAvSyncAnalysis(videoMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class);

        verify(avSyncAnalysisRepository).saveAndFlush(any(AvSyncAnalysis.class));
    }

    @Test
    @DisplayName("getEvidence: retrieves granular evidence for authorized user")
    void getEvidence_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        AvSyncAnalysis analysis = new AvSyncAnalysis(videoMedia);
        analysis.setEvidenceJson("{\"detected_faces_count\":2,\"envelope_correlation\":0.78,\"syncnet_min_distance\":0.41}");
        when(avSyncAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(analysis));

        AvSyncEvidenceDto evidence = service.getEvidence(videoMediaId, owner.getEmail());

        assertThat(evidence).isNotNull();
        assertThat(evidence.getDetectedFacesCount()).isEqualTo(2);
        assertThat(evidence.getEnvelopeCorrelation()).isEqualTo(0.78);
        assertThat(evidence.getSyncnetMinDistance()).isEqualTo(0.41);
    }
}
