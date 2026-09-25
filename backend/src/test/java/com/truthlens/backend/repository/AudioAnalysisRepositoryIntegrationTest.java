package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AudioAnalysis;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("AudioAnalysisRepository — Real Database Integration Tests (Flyway V7)")
class AudioAnalysisRepositoryIntegrationTest {

    @Autowired
    private AudioAnalysisRepository audioAnalysisRepository;

    @Autowired
    private MediaRepository mediaRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private RoleRepository roleRepository;

    @Autowired
    private TestEntityManager entityManager;

    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = new User("audio_db_test@truthlens.org", "secret_hash", "Audio DB Tester");
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));
        testUser.getRoles().add(userRole);
        testUser = userRepository.saveAndFlush(testUser);
    }

    private Media createAudioMedia(String filename, String sha256) {
        Media media = new Media(
                testUser,
                filename,
                "storage/quarantine/" + filename,
                MediaType.AUDIO,
                "audio/wav",
                524288L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("Should persist and retrieve AudioAnalysis entity with all fields and timestamps")
    void shouldPersistAndRetrieveAudioAnalysis() {
        Media media = createAudioMedia("speech_sample.wav", "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890");

        AudioAnalysis analysis = new AudioAnalysis(media);
        analysis.setSyntheticVoiceProb(0.8542);
        analysis.setSpectrogramUrl("/artifacts/audio_spec_123.png");
        analysis.setPitchVariance(145.2);
        analysis.setPhaseDiscontinuity(0.72);
        analysis.setSpliceMarkersJson("[{\"timestamp_seconds\":1.25,\"score\":0.82,\"reason\":\"SPECTRAL_FLUX_JUMP\"}]");
        analysis.setEvidenceJson("{\"duration_seconds\":5.0,\"pitch_mean\":210.5}");
        analysis.setModelName("TruthLens-PyTorch-AASIST-AudioClassifier");
        analysis.setModelVersion("1.0.0-prod");
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);

        AudioAnalysis saved = audioAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        Optional<AudioAnalysis> retrievedOpt = audioAnalysisRepository.findById(saved.getId());
        assertThat(retrievedOpt).isPresent();

        AudioAnalysis retrieved = retrievedOpt.get();
        assertThat(retrieved.getSyntheticVoiceProb()).isEqualTo(0.8542);
        assertThat(retrieved.getSpectrogramUrl()).isEqualTo("/artifacts/audio_spec_123.png");
        assertThat(retrieved.getPitchVariance()).isEqualTo(145.2);
        assertThat(retrieved.getPhaseDiscontinuity()).isEqualTo(0.72);
        assertThat(retrieved.getModelName()).isEqualTo("TruthLens-PyTorch-AASIST-AudioClassifier");
        assertThat(retrieved.getModelVersion()).isEqualTo("1.0.0-prod");
        assertThat(retrieved.getAnalysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(retrieved.getCreatedAt()).isNotNull();
        assertThat(retrieved.getUpdatedAt()).isNotNull();
    }

    @Test
    @DisplayName("Should find AudioAnalysis by mediaId")
    void shouldFindByMediaId() {
        Media media = createAudioMedia("interview.wav", "0000000000000000000000000000000000000000000000000000000000000001");

        AudioAnalysis analysis = new AudioAnalysis(media);
        analysis.setSyntheticVoiceProb(0.1250);
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        audioAnalysisRepository.saveAndFlush(analysis);

        Optional<AudioAnalysis> found = audioAnalysisRepository.findByMediaId(media.getId());
        assertThat(found).isPresent();
        assertThat(found.get().getSyntheticVoiceProb()).isEqualTo(0.1250);
    }

    @Test
    @DisplayName("Should check existence by mediaId")
    void shouldCheckExistsByMediaId() {
        Media media = createAudioMedia("call.wav", "0000000000000000000000000000000000000000000000000000000000000002");

        assertThat(audioAnalysisRepository.existsByMediaId(media.getId())).isFalse();

        AudioAnalysis analysis = new AudioAnalysis(media);
        analysis.setSyntheticVoiceProb(0.40);
        audioAnalysisRepository.saveAndFlush(analysis);

        assertThat(audioAnalysisRepository.existsByMediaId(media.getId())).isTrue();
    }

    @Test
    @DisplayName("Should enforce UNIQUE constraint on media_id")
    void shouldEnforceUniqueMediaIdConstraint() {
        Media media = createAudioMedia("dup_check.wav", "0000000000000000000000000000000000000000000000000000000000000003");

        AudioAnalysis a1 = new AudioAnalysis(media);
        a1.setSyntheticVoiceProb(0.20);
        audioAnalysisRepository.saveAndFlush(a1);

        AudioAnalysis a2 = new AudioAnalysis(media);
        a2.setSyntheticVoiceProb(0.80);

        assertThatThrownBy(() -> audioAnalysisRepository.saveAndFlush(a2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Should enforce CHECK constraint on synthetic_voice_prob range [0.0, 1.0]")
    void shouldEnforceCheckConstraintOnSyntheticVoiceProb() {
        Media media = createAudioMedia("invalid_score.wav", "0000000000000000000000000000000000000000000000000000000000000004");

        AudioAnalysis invalidAnalysis = new AudioAnalysis(media);
        invalidAnalysis.setSyntheticVoiceProb(1.50); // Exceeds 1.0

        assertThatThrownBy(() -> audioAnalysisRepository.saveAndFlush(invalidAnalysis))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Should cascade delete AudioAnalysis when parent Media is deleted")
    void shouldCascadeDeleteWithMedia() {
        Media media = createAudioMedia("cascade_test.wav", "0000000000000000000000000000000000000000000000000000000000000005");

        AudioAnalysis analysis = new AudioAnalysis(media);
        analysis.setSyntheticVoiceProb(0.65);
        audioAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        assertThat(audioAnalysisRepository.existsByMediaId(media.getId())).isTrue();

        mediaRepository.deleteById(media.getId());
        entityManager.flush();
        entityManager.clear();

        assertThat(audioAnalysisRepository.existsByMediaId(media.getId())).isFalse();
    }

    @Test
    @DisplayName("Should find flagged synthetic audio records ordered by probability descending")
    void shouldFindFlaggedSyntheticAudio() {
        Media m1 = createAudioMedia("audio1.wav", "1111111111111111111111111111111111111111111111111111111111111111");
        Media m2 = createAudioMedia("audio2.wav", "2222222222222222222222222222222222222222222222222222222222222222");
        Media m3 = createAudioMedia("audio3.wav", "3333333333333333333333333333333333333333333333333333333333333333");

        AudioAnalysis a1 = new AudioAnalysis(m1);
        a1.setSyntheticVoiceProb(0.60);
        audioAnalysisRepository.saveAndFlush(a1);

        AudioAnalysis a2 = new AudioAnalysis(m2);
        a2.setSyntheticVoiceProb(0.95);
        audioAnalysisRepository.saveAndFlush(a2);

        AudioAnalysis a3 = new AudioAnalysis(m3);
        a3.setSyntheticVoiceProb(0.20); // Not flagged (< 0.50)
        audioAnalysisRepository.saveAndFlush(a3);

        List<AudioAnalysis> flagged = audioAnalysisRepository.findFlaggedSyntheticAudio(PageRequest.of(0, 10));
        assertThat(flagged).hasSize(2);
        assertThat(flagged.get(0).getSyntheticVoiceProb()).isEqualTo(0.95);
        assertThat(flagged.get(1).getSyntheticVoiceProb()).isEqualTo(0.60);
    }
}
