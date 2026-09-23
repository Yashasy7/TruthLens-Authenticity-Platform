package com.truthlens.backend.service.audio;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.AudioAnalysisResponse;
import com.truthlens.backend.dto.AudioEvidenceDto;
import com.truthlens.backend.dto.AudioSpliceMarkerDto;
import com.truthlens.backend.dto.FastApiAudioAnalysisResponse;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AudioAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.AudioAnalysisRepository;
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
@DisplayName("AudioAuthenticityService — Unit & Security Tests")
class AudioAuthenticityServiceTest {

    @Mock
    private AudioAnalysisRepository audioAnalysisRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private AudioAiServiceClient audioAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private AudioAuthenticityService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media audioMedia;
    private Media videoMedia;
    private UUID audioMediaId;
    private UUID videoMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new AudioAuthenticityService(
                audioAnalysisRepository,
                mediaRepository,
                userRepository,
                storageService,
                audioAiServiceClient,
                objectMapper
        );

        owner = new User("owner@truthlens.org", "hash", "Owner User");
        setId(owner, UUID.randomUUID());
        owner.getRoles().add(new Role(RoleName.USER, "Standard User"));

        otherUser = new User("other@truthlens.org", "hash", "Other User");
        setId(otherUser, UUID.randomUUID());
        otherUser.getRoles().add(new Role(RoleName.USER, "Standard User"));

        analyst = new User("analyst@truthlens.org", "hash", "Analyst User");
        setId(analyst, UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Forensic Analyst"));

        audioMediaId = UUID.randomUUID();
        audioMedia = new Media(owner, "voice.wav", "quarantine/voice.wav", MediaType.AUDIO, "audio/wav", 1024L, "hash1", UploadStatus.UPLOADED);
        setId(audioMedia, audioMediaId);

        videoMediaId = UUID.randomUUID();
        videoMedia = new Media(owner, "clip.mp4", "quarantine/clip.mp4", MediaType.VIDEO, "video/mp4", 2048L, "hash2", UploadStatus.UPLOADED);
        setId(videoMedia, videoMediaId);
    }

    private void setId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    private FastApiAudioAnalysisResponse buildSampleFastApiResponse() {
        AudioSpliceMarkerDto marker = new AudioSpliceMarkerDto(1.2, 0.85, "SPECTRAL_FLUX_JUMP");
        AudioEvidenceDto evidence = new AudioEvidenceDto(
                4.0, 220.0, 150.0, 1800.0, 1500.0, 3600.0, 0.05, 0.70, List.of(marker), Map.of("pitch_anomaly", 0.75)
        );
        return new FastApiAudioAnalysisResponse(
                0.82, "/artifacts/spec_1.png", "base64img", 150.0, List.of(marker),
                "TruthLens-PyTorch-AASIST-AudioClassifier", "0.1.0-dev", evidence, "COMPLETED"
        );
    }

    @Test
    @DisplayName("getAudioAnalysis: returns cached analysis without invoking AI client")
    void getAudioAnalysis_returnsCached() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        AudioAnalysis cached = new AudioAnalysis(audioMedia);
        cached.setSyntheticVoiceProb(0.78);
        cached.setPitchVariance(120.0);
        cached.setSpectrogramUrl("/artifacts/cached.png");
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.of(cached));

        AudioAnalysisResponse response = service.getAudioAnalysis(audioMediaId, owner.getEmail());

        assertThat(response.syntheticVoiceProb()).isEqualTo(0.78);
        assertThat(response.authenticityAssessment()).isEqualTo("HIGH_SYNTHETIC_VOICE_RISK");
        verify(audioAiServiceClient, never()).analyzeAudio(any(), any(), any());
    }

    @Test
    @DisplayName("getAudioAnalysis: executes analysis when not cached and persists result")
    void getAudioAnalysis_triggersExecutionIfAbsent() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());
        when(storageService.load("quarantine/voice.wav")).thenReturn(new ByteArrayInputStream(new byte[]{1, 2, 3}));

        FastApiAudioAnalysisResponse aiResult = buildSampleFastApiResponse();
        when(audioAiServiceClient.analyzeAudio(any(), any(), any())).thenReturn(aiResult);
        when(audioAnalysisRepository.saveAndFlush(any(AudioAnalysis.class))).thenAnswer(inv -> inv.getArgument(0));

        AudioAnalysisResponse response = service.getAudioAnalysis(audioMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.syntheticVoiceProb()).isEqualTo(0.82);
        assertThat(response.spectrogramBase64()).isEqualTo("base64img");
        assertThat(response.authenticityAssessment()).isEqualTo("HIGH_SYNTHETIC_VOICE_RISK");
        verify(audioAnalysisRepository).saveAndFlush(any(AudioAnalysis.class));
    }

    @Test
    @DisplayName("reanalyzeAudio: forces AI execution even if cached analysis exists")
    void reanalyzeAudio_forcesExecution() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(storageService.load("quarantine/voice.wav")).thenReturn(new ByteArrayInputStream(new byte[]{1, 2, 3}));

        FastApiAudioAnalysisResponse aiResult = buildSampleFastApiResponse();
        when(audioAiServiceClient.analyzeAudio(any(), any(), any())).thenReturn(aiResult);
        when(audioAnalysisRepository.saveAndFlush(any(AudioAnalysis.class))).thenAnswer(inv -> inv.getArgument(0));

        AudioAnalysisResponse response = service.reanalyzeAudio(audioMediaId, owner.getEmail());

        assertThat(response.syntheticVoiceProb()).isEqualTo(0.82);
        verify(audioAiServiceClient).analyzeAudio(any(), any(), any());
    }

    @Test
    @DisplayName("Security: IDOR protection blocks non-owner, non-elevated user")
    void getAudioAnalysis_idorBlocked_throwsAccessDenied() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getAudioAnalysis(audioMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");

        verify(audioAiServiceClient, never()).analyzeAudio(any(), any(), any());
    }

    @Test
    @DisplayName("Security: elevated ANALYST role can access non-owned media analysis")
    void getAudioAnalysis_analystAllowed_succeeds() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));

        AudioAnalysis cached = new AudioAnalysis(audioMedia);
        cached.setSyntheticVoiceProb(0.15);
        cached.setAnalysisStatus(AnalysisStatus.COMPLETED);
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.of(cached));

        AudioAnalysisResponse response = service.getAudioAnalysis(audioMediaId, analyst.getEmail());

        assertThat(response.syntheticVoiceProb()).isEqualTo(0.15);
        assertThat(response.authenticityAssessment()).isEqualTo("LIKELY_AUTHENTIC_AUDIO");
    }

    @Test
    @DisplayName("Validation: non-audio media throws InvalidMediaException")
    void getAudioAnalysis_wrongMediaType_throwsInvalidMedia() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getAudioAnalysis(videoMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("only supported for audio assets");
    }

    @Test
    @DisplayName("Error Handling: AI service failure marks FAILED status and rethrows")
    void getAudioAnalysis_aiServiceFailure_savesFailedAnalysis() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.empty());
        when(storageService.load("quarantine/voice.wav")).thenReturn(new ByteArrayInputStream(new byte[]{1, 2, 3}));

        when(audioAiServiceClient.analyzeAudio(any(), any(), any()))
                .thenThrow(new AiServiceException("PyTorch worker timed out"));

        assertThatThrownBy(() -> service.getAudioAnalysis(audioMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("PyTorch worker timed out");

        verify(audioAnalysisRepository).saveAndFlush(any(AudioAnalysis.class));
    }

    @Test
    @DisplayName("getEvidence: retrieves and parses granular evidence")
    void getEvidence_success() throws Exception {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        AudioEvidenceDto evidenceDto = new AudioEvidenceDto(
                5.0, 210.0, 95.0, 1900.0, 1600.0, 3900.0, 0.04, 0.45, List.of(), Map.of()
        );
        AudioAnalysis analysis = new AudioAnalysis(audioMedia);
        analysis.setEvidenceJson(objectMapper.writeValueAsString(evidenceDto));
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.of(analysis));

        AudioEvidenceDto result = service.getEvidence(audioMediaId, owner.getEmail());

        assertThat(result).isNotNull();
        assertThat(result.pitchMean()).isEqualTo(210.0);
        assertThat(result.phaseDiscontinuityScore()).isEqualTo(0.45);
    }

    @Test
    @DisplayName("getSpliceMarkers: retrieves and parses splice markers")
    void getSpliceMarkers_success() throws Exception {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        AudioSpliceMarkerDto m1 = new AudioSpliceMarkerDto(2.1, 0.90, "SPECTRAL_FLUX_JUMP");
        AudioAnalysis analysis = new AudioAnalysis(audioMedia);
        analysis.setSpliceMarkersJson(objectMapper.writeValueAsString(List.of(m1)));
        when(audioAnalysisRepository.findByMediaId(audioMediaId)).thenReturn(Optional.of(analysis));

        List<AudioSpliceMarkerDto> markers = service.getSpliceMarkers(audioMediaId, owner.getEmail());

        assertThat(markers).hasSize(1);
        assertThat(markers.get(0).reason()).isEqualTo("SPECTRAL_FLUX_JUMP");
    }
}
