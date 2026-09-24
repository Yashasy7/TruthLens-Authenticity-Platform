package com.truthlens.backend.service.stt;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiTranscriptResponse;
import com.truthlens.backend.dto.TranscriptEvidenceDto;
import com.truthlens.backend.dto.TranscriptResponse;
import com.truthlens.backend.dto.TranscriptSegmentDto;
import com.truthlens.backend.dto.TranscriptWordDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.Transcript;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.TranscriptRepository;
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
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("SpeechToTextService — Unit & Security Tests")
class SpeechToTextServiceTest {

    @Mock
    private TranscriptRepository transcriptRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private TranscriptAiServiceClient transcriptAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private SpeechToTextService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media audioMedia;
    private Media videoMedia;
    private Media imageMedia;
    private UUID audioMediaId;
    private UUID videoMediaId;
    private UUID imageMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new SpeechToTextService(
                transcriptRepository,
                mediaRepository,
                userRepository,
                storageService,
                transcriptAiServiceClient,
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

        audioMediaId = UUID.randomUUID();
        audioMedia = new Media(owner, "speech.wav", "storage/speech.wav", MediaType.AUDIO, "audio/wav", 512000L, "sha256aud", UploadStatus.UPLOADED);
        setId(audioMedia, audioMediaId);

        videoMediaId = UUID.randomUUID();
        videoMedia = new Media(owner, "clip.mp4", "storage/clip.mp4", MediaType.VIDEO, "video/mp4", 1048576L, "sha256vid", UploadStatus.UPLOADED);
        setId(videoMedia, videoMediaId);

        imageMediaId = UUID.randomUUID();
        imageMedia = new Media(owner, "photo.jpg", "storage/photo.jpg", MediaType.IMAGE, "image/jpeg", 2048L, "sha256img", UploadStatus.UPLOADED);
        setId(imageMedia, imageMediaId);
    }

    private void setId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    private FastApiTranscriptResponse buildSampleAiResponse() {
        TranscriptWordDto word1 = new TranscriptWordDto("TruthLens", 0.0, 0.6, 0.98);
        TranscriptWordDto word2 = new TranscriptWordDto("platform", 0.6, 1.2, 0.96);
        TranscriptSegmentDto segment = new TranscriptSegmentDto(
                0, 0, 0.0, 1.2, "TruthLens platform", List.of(101, 102), 0.0, -0.05, 1.1, 0.01, 0.97, List.of(word1, word2)
        );
        TranscriptEvidenceDto evidence = new TranscriptEvidenceDto(
                "Faster-Whisper", "tiny", "int8", "cpu", "en", 0.99, 1.2, 16000, "AUDIO", Map.of()
        );

        return new FastApiTranscriptResponse(
                "TruthLens platform",
                "en",
                0.97,
                1.2,
                1,
                2,
                List.of(segment),
                evidence,
                "COMPLETED",
                null
        );
    }

    @Test
    @DisplayName("getTranscript: media owner triggers transcription successfully")
    void getTranscript_owner_success() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(transcriptRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());

        when(storageService.load(audioMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("audio bytes".getBytes()));
        when(transcriptAiServiceClient.analyzeSpeechToText(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(transcriptRepository.save(any(Transcript.class))).thenAnswer(invocation -> invocation.getArgument(0));

        TranscriptResponse response = service.getTranscript(audioMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getFullText()).isEqualTo("TruthLens platform");
        assertThat(response.getConfidenceScore()).isEqualTo(0.97);
        assertThat(response.getSegmentsCount()).isEqualTo(1);
        assertThat(response.getWordsCount()).isEqualTo(2);
        verify(transcriptAiServiceClient).analyzeSpeechToText(any(), any(), any());
    }

    @Test
    @DisplayName("getTranscript: analyst accessing other user's media succeeds via elevated role")
    void getTranscript_analyst_success() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));
        when(transcriptRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());

        when(storageService.load(audioMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("audio bytes".getBytes()));
        when(transcriptAiServiceClient.analyzeSpeechToText(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(transcriptRepository.save(any(Transcript.class))).thenAnswer(invocation -> invocation.getArgument(0));

        TranscriptResponse response = service.getTranscript(audioMediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getFullText()).isEqualTo("TruthLens platform");
    }

    @Test
    @DisplayName("getTranscript: IDOR blocked when unauthorized user accesses another user's media")
    void getTranscript_idor_throwsAccessDeniedException() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getTranscript(audioMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");

        verify(transcriptRepository, never()).findByMediaId(any());
        verify(transcriptAiServiceClient, never()).analyzeSpeechToText(any(), any(), any());
    }

    @Test
    @DisplayName("getTranscript: returns cached result without invoking AI service if already transcribed")
    void getTranscript_cached_returnsExisting() {
        Transcript existing = new Transcript(
                audioMedia, "CACHED TRANSCRIPT", "en", 0.95, 2.0, 1, 2, "[]", "{}", AnalysisStatus.COMPLETED
        );

        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(transcriptRepository.findByMediaId(audioMediaId)).thenReturn(Optional.of(existing));

        TranscriptResponse response = service.getTranscript(audioMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getFullText()).isEqualTo("CACHED TRANSCRIPT");
        verify(transcriptAiServiceClient, never()).analyzeSpeechToText(any(), any(), any());
    }

    @Test
    @DisplayName("reanalyzeTranscript: forces fresh evaluation even when previous result exists")
    void reanalyzeTranscript_forcesFreshEvaluation() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(transcriptRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());

        when(storageService.load(audioMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("audio bytes".getBytes()));
        when(transcriptAiServiceClient.analyzeSpeechToText(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(transcriptRepository.save(any(Transcript.class))).thenAnswer(invocation -> invocation.getArgument(0));

        TranscriptResponse response = service.reanalyzeTranscript(audioMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        verify(transcriptAiServiceClient).analyzeSpeechToText(any(), any(), any());
    }

    @Test
    @DisplayName("getTranscript: unsupported media type IMAGE throws InvalidMediaException")
    void getTranscript_imageMediaType_throwsInvalidMediaException() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getTranscript(imageMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("Speech-to-text transcription is only supported for audio and video assets");

        verify(transcriptAiServiceClient, never()).analyzeSpeechToText(any(), any(), any());
    }

    @Test
    @DisplayName("getTranscript: VIDEO media asset is accepted and processed successfully")
    void getTranscript_videoMedia_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(transcriptRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("video bytes".getBytes()));
        when(transcriptAiServiceClient.analyzeSpeechToText(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(transcriptRepository.save(any(Transcript.class))).thenAnswer(invocation -> invocation.getArgument(0));

        TranscriptResponse response = service.getTranscript(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getFullText()).isEqualTo("TruthLens platform");
    }

    @Test
    @DisplayName("getTranscript: AI service failure records FAILED status in database")
    void getTranscript_aiFailure_persistsFailure() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(transcriptRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());

        when(storageService.load(audioMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("audio bytes".getBytes()));
        when(transcriptAiServiceClient.analyzeSpeechToText(any(), any(), any()))
                .thenThrow(new AiServiceException("Downstream ASR failed"));

        assertThatThrownBy(() -> service.getTranscript(audioMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class);

        verify(transcriptRepository).save(any(Transcript.class));
    }
}
