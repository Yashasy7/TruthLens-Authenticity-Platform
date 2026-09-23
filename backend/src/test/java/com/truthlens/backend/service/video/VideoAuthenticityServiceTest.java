package com.truthlens.backend.service.video;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiVideoAnalysisResponse;
import com.truthlens.backend.dto.FrameScoreDto;
import com.truthlens.backend.dto.SuspiciousTimestampDto;
import com.truthlens.backend.dto.VideoAnalysisResponse;
import com.truthlens.backend.dto.VideoEvidenceDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.entity.VideoAnalysis;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.repository.VideoAnalysisRepository;
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
@DisplayName("VideoAuthenticityService — Unit & Security Tests")
class VideoAuthenticityServiceTest {

    @Mock
    private VideoAnalysisRepository videoAnalysisRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private VideoAiServiceClient videoAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private VideoAuthenticityService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media videoMedia;
    private Media imageMedia;
    private UUID videoMediaId;
    private UUID imageMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new VideoAuthenticityService(
                videoAnalysisRepository,
                mediaRepository,
                userRepository,
                storageService,
                videoAiServiceClient,
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
                "deepfake_sample.mp4",
                "quarantine/video/deepfake_sample.mp4",
                MediaType.VIDEO,
                "video/mp4",
                2097152L,
                "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                UploadStatus.UPLOADED
        );
        setEntityId(videoMedia, videoMediaId);

        imageMediaId = UUID.randomUUID();
        imageMedia = new Media(
                owner,
                "photo.jpg",
                "quarantine/image/photo.jpg",
                MediaType.IMAGE,
                "image/jpeg",
                2048L,
                "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                UploadStatus.UPLOADED
        );
        setEntityId(imageMedia, imageMediaId);
    }

    private void setEntityId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    @Test
    @DisplayName("getVideoAnalysis: performs analysis on-demand when not cached")
    void getVideoAnalysis_onDemandExecution_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(videoAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        byte[] rawVideo = "fake-video-content".getBytes();
        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(rawVideo));

        SuspiciousTimestampDto st = new SuspiciousTimestampDto(2.0, 4, 0.90, "HIGH_SYNTHETIC_FACE_PROBABILITY");
        FrameScoreDto fs = new FrameScoreDto(4, 2.0, 0.90, 0.80, 1, true);
        VideoEvidenceDto ev = new VideoEvidenceDto(1, 10, 5.0, List.of(fs), List.of(st), Map.of());

        FastApiVideoAnalysisResponse aiResponse = new FastApiVideoAnalysisResponse(
                0.86,
                1,
                10,
                List.of(st),
                List.of(fs),
                "TruthLens-VideoDeepfakeClassifier",
                "TruthLens-VideoDeepfakeClassifier-0.1.0-dev",
                ev,
                "COMPLETED"
        );
        when(videoAiServiceClient.analyzeVideo(any(), eq("deepfake_sample.mp4"), eq("video/mp4")))
                .thenReturn(aiResponse);

        when(videoAnalysisRepository.saveAndFlush(any(VideoAnalysis.class))).thenAnswer(invocation -> {
            VideoAnalysis va = invocation.getArgument(0);
            setEntityId(va, UUID.randomUUID());
            return va;
        });

        VideoAnalysisResponse response = service.getVideoAnalysis(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.deepfakeProb()).isEqualTo(0.86);
        assertThat(response.faceCount()).isEqualTo(1);
        assertThat(response.totalFramesSampled()).isEqualTo(10);
        assertThat(response.authenticityAssessment()).isEqualTo("HIGH_DEEPFAKE_RISK");
        assertThat(response.analysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
    }

    @Test
    @DisplayName("getVideoAnalysis: returns existing cached record without re-calling AI service")
    void getVideoAnalysis_returnsCached_withoutReanalysis() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        VideoAnalysis cached = new VideoAnalysis(videoMedia);
        cached.setDeepfakeProb(0.12);
        cached.setFaceCount(1);
        cached.setTotalFramesSampled(8);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(videoAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(cached));

        VideoAnalysisResponse response = service.getVideoAnalysis(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.deepfakeProb()).isEqualTo(0.12);
        assertThat(response.authenticityAssessment()).isEqualTo("LOW_DEEPFAKE_RISK");

        verify(videoAiServiceClient, never()).analyzeVideo(any(), any(), any());
    }

    @Test
    @DisplayName("IDOR Protection: unauthorized non-owner user cannot access video analysis")
    void idor_blockedForUnauthorizedUser() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getVideoAnalysis(videoMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");
    }

    @Test
    @DisplayName("Role Elevation: privileged ANALYST can access any user's video analysis")
    void elevatedRole_analystCanAccess() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));

        VideoAnalysis cached = new VideoAnalysis(videoMedia);
        cached.setDeepfakeProb(0.70);
        cached.setFaceCount(2);
        cached.setTotalFramesSampled(20);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(videoAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(cached));

        VideoAnalysisResponse response = service.getVideoAnalysis(videoMediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.deepfakeProb()).isEqualTo(0.70);
        assertThat(response.authenticityAssessment()).isEqualTo("SUSPICIOUS_DEEPFAKE_INDICATORS");
    }

    @Test
    @DisplayName("Media Type Validation: non-video assets (image) must be rejected with InvalidMediaException")
    void nonVideoMedia_rejectedWithInvalidMediaException() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getVideoAnalysis(imageMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("Video deepfake analysis is only supported for video assets");
    }

    @Test
    @DisplayName("Downstream Failure: AI service failure records FAILED status and rethrows AiServiceException")
    void aiServiceFailure_recordsFailedStatusAndRethrows() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(videoAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        byte[] rawVideo = "fake-video-content".getBytes();
        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(rawVideo));

        when(videoAiServiceClient.analyzeVideo(any(), eq("deepfake_sample.mp4"), eq("video/mp4")))
                .thenThrow(new AiServiceException("FastAPI connection timeout"));

        assertThatThrownBy(() -> service.getVideoAnalysis(videoMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("FastAPI connection timeout");

        verify(videoAnalysisRepository).saveAndFlush(any(VideoAnalysis.class));
    }

    @Test
    @DisplayName("getTimeline: retrieves parsed suspicious timeline list")
    void getTimeline_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        VideoAnalysis analysis = new VideoAnalysis(videoMedia);
        analysis.setSuspiciousTimestampsJson("[{\"timestamp_seconds\":1.5,\"frame_index\":3,\"score\":0.82,\"reason\":\"HIGH_SYNTHETIC_FACE_PROBABILITY\"}]");
        when(videoAnalysisRepository.findByMediaId(videoMediaId)).thenReturn(Optional.of(analysis));

        List<SuspiciousTimestampDto> timeline = service.getTimeline(videoMediaId, owner.getEmail());
        assertThat(timeline).hasSize(1);
        assertThat(timeline.get(0).timestampSeconds()).isEqualTo(1.5);
        assertThat(timeline.get(0).reason()).isEqualTo("HIGH_SYNTHETIC_FACE_PROBABILITY");
    }
}
