package com.truthlens.backend.service.image;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiImageAnalysisResponse;
import com.truthlens.backend.dto.ImageAnalysisResponse;
import com.truthlens.backend.dto.ImageEvidenceDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ImageAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.ImageAnalysisRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageKeyGenerator;
import com.truthlens.backend.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("ImageAuthenticityService — Unit & Security Tests")
class ImageAuthenticityServiceTest {

    @Mock
    private ImageAnalysisRepository imageAnalysisRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private StorageKeyGenerator storageKeyGenerator;

    @Mock
    private AiServiceClient aiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private ImageAuthenticityService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media imageMedia;
    private Media videoMedia;
    private UUID imageMediaId;
    private UUID videoMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new ImageAuthenticityService(
                imageAnalysisRepository,
                mediaRepository,
                userRepository,
                storageService,
                storageKeyGenerator,
                aiServiceClient,
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

        imageMediaId = UUID.randomUUID();
        imageMedia = new Media(
                owner,
                "test.jpg",
                "quarantine/image/test.jpg",
                MediaType.IMAGE,
                "image/jpeg",
                2048L,
                "a1b2c3d4e5f67890",
                UploadStatus.UPLOADED
        );
        setEntityId(imageMedia, imageMediaId);

        videoMediaId = UUID.randomUUID();
        videoMedia = new Media(
                owner,
                "test.mp4",
                "quarantine/video/test.mp4",
                MediaType.VIDEO,
                "video/mp4",
                10240L,
                "0987f6e5d4c3b2a1",
                UploadStatus.UPLOADED
        );
        setEntityId(videoMedia, videoMediaId);
    }

    private void setEntityId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    @Test
    @DisplayName("getImageAnalysis: performs analysis on-demand when not cached")
    void getImageAnalysis_onDemandExecution_success() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        byte[] rawImage = "fake-jpg-content".getBytes();
        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(rawImage));

        String dummyBase64 = Base64.getEncoder().encodeToString("fake-png".getBytes());
        FastApiImageAnalysisResponse aiResponse = new FastApiImageAnalysisResponse(
                0.88,
                0.12,
                15.2,
                0.22,
                false,
                false,
                "DiffusionClassifierNet",
                "TruthLens-DiffusionClassifier-0.1.0-dev",
                dummyBase64,
                dummyBase64,
                Map.of("noiseVariance", 15.2, "fftAnomalyScore", 0.22),
                "COMPLETED"
        );
        when(aiServiceClient.analyzeImage(any(), eq("test.jpg"), eq("image/jpeg"))).thenReturn(aiResponse);
        when(storageKeyGenerator.generateKey(any(), anyString()))
                .thenReturn("quarantine/image/ela.png")
                .thenReturn("quarantine/image/gradcam.png");
        when(storageService.store(any(), anyString(), anyString(), anyLong()))
                .thenReturn("quarantine/image/ela.png")
                .thenReturn("quarantine/image/gradcam.png");

        when(imageAnalysisRepository.saveAndFlush(any(ImageAnalysis.class))).thenAnswer(invocation -> {
            ImageAnalysis a = invocation.getArgument(0);
            setEntityId(a, UUID.randomUUID());
            return a;
        });

        ImageAnalysisResponse response = service.getImageAnalysis(imageMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.aiProb()).isEqualTo(0.88);
        assertThat(response.manipulationProb()).isEqualTo(0.12);
        assertThat(response.authenticityAssessment()).isEqualTo("HIGH_SYNTHETIC_RISK");
        assertThat(response.analysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.elaHeatmapUrl()).contains("/artifacts/ela");
        assertThat(response.gradcamHeatmapUrl()).contains("/artifacts/gradcam");
    }

    @Test
    @DisplayName("getImageAnalysis: returns existing cached record without re-calling AI service")
    void getImageAnalysis_returnsCached_withoutReanalysis() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        ImageAnalysis cached = new ImageAnalysis(imageMedia);
        cached.setAiProb(0.15);
        cached.setManipulationProb(0.10);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.of(cached));

        ImageAnalysisResponse response = service.getImageAnalysis(imageMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.aiProb()).isEqualTo(0.15);
        assertThat(response.manipulationProb()).isEqualTo(0.10);
        assertThat(response.authenticityAssessment()).isEqualTo("LOW_ANOMALY_LEVEL");

        verify(aiServiceClient, never()).analyzeImage(any(), any(), any());
    }

    @Test
    @DisplayName("IDOR Protection: unauthorized non-owner user cannot access analysis")
    void idor_blockedForUnauthorizedUser() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getImageAnalysis(imageMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");
    }

    @Test
    @DisplayName("Role Elevation: privileged ANALYST can access any user's analysis")
    void elevatedRole_analystCanAccess() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));

        ImageAnalysis cached = new ImageAnalysis(imageMedia);
        cached.setAiProb(0.60);
        cached.setManipulationProb(0.70);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.of(cached));

        ImageAnalysisResponse response = service.getImageAnalysis(imageMediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.aiProb()).isEqualTo(0.60);
    }

    @Test
    @DisplayName("Media Type Validation: non-image assets (video) must be rejected with InvalidMediaException")
    void nonImageMedia_rejectedWithInvalidMediaException() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getImageAnalysis(videoMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("Image authenticity analysis is only supported for image assets");
    }

    @Test
    @DisplayName("Downstream Failure: AI service failure records FAILED status and rethrows AiServiceException")
    void aiServiceFailure_recordsFailedStatusAndRethrows() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        byte[] rawImage = "fake-jpg-content".getBytes();
        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(rawImage));

        when(aiServiceClient.analyzeImage(any(), eq("test.jpg"), eq("image/jpeg")))
                .thenThrow(new AiServiceException("FastAPI connection timeout"));

        assertThatThrownBy(() -> service.getImageAnalysis(imageMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("FastAPI connection timeout");

        // Verify FAILED status is persisted
        verify(imageAnalysisRepository).saveAndFlush(any(ImageAnalysis.class));
    }

    @Test
    @DisplayName("getArtifactStream: streams existing visual artifact")
    void getArtifactStream_success() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        ImageAnalysis analysis = new ImageAnalysis(imageMedia);
        analysis.setElaHeatmapUrl("quarantine/image/ela.png");
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.of(analysis));
        when(storageService.exists("quarantine/image/ela.png")).thenReturn(true);
        when(storageService.load("quarantine/image/ela.png")).thenReturn(new ByteArrayInputStream(new byte[]{1, 2, 3}));

        InputStream stream = service.getArtifactStream(imageMediaId, "ela", owner.getEmail());
        assertThat(stream).isNotNull();
    }

    @Test
    @DisplayName("getArtifactStream: rejects unknown artifact types")
    void getArtifactStream_unknownType_throwsException() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        ImageAnalysis analysis = new ImageAnalysis(imageMedia);
        when(imageAnalysisRepository.findByMediaId(imageMediaId)).thenReturn(Optional.of(analysis));

        assertThatThrownBy(() -> service.getArtifactStream(imageMediaId, "invalid_type", owner.getEmail()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsupported artifact type");
    }
}
