package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.AvSyncAnalysis;
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
import org.springframework.test.context.TestPropertySource;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("AvSyncAnalysisRepository — Real Database Integration Tests (Flyway V8)")
class AvSyncAnalysisRepositoryIntegrationTest {

    @Autowired
    private AvSyncAnalysisRepository avSyncAnalysisRepository;

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
        testUser = new User("av_db_test@truthlens.org", "secret_hash", "AV Sync DB Tester");
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));
        testUser.getRoles().add(userRole);
        testUser = userRepository.saveAndFlush(testUser);
    }

    private Media createVideoMedia(String filename, String sha256) {
        Media media = new Media(
                testUser,
                filename,
                "quarantine/video/" + filename,
                MediaType.VIDEO,
                "video/mp4",
                2097152L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("Flyway V8 schema & Persistence: save and retrieve AvSyncAnalysis with eager Media join")
    void saveAndRetrieve_success() {
        Media media = createVideoMedia("interview_sync.mp4", "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff");

        AvSyncAnalysis analysis = new AvSyncAnalysis(media);
        analysis.setSyncScore(0.85);
        analysis.setLipOffsetMs(-25.0);
        analysis.setConfidence(0.90);
        analysis.setMismatchSegmentsJson("[{\"start_time\":1.0,\"end_time\":2.0,\"offset_ms\":-25.0,\"confidence\":0.80,\"reason\":\"Normal speech\"}]");
        analysis.setEvidenceJson("{\"detected_faces_count\":1,\"envelope_correlation\":0.82,\"syncnet_min_distance\":0.45}");
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelName("TruthLens-PyTorch-SyncNet-DualStream");
        analysis.setModelVersion("TruthLens-SyncNet-v1.0-dev");

        AvSyncAnalysis saved = avSyncAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        Optional<AvSyncAnalysis> retrieved = avSyncAnalysisRepository.findByMediaId(media.getId());
        assertThat(retrieved).isPresent();
        assertThat(retrieved.get().getId()).isEqualTo(saved.getId());
        assertThat(retrieved.get().getSyncScore()).isEqualTo(0.85);
        assertThat(retrieved.get().getLipOffsetMs()).isEqualTo(-25.0);
        assertThat(retrieved.get().getConfidence()).isEqualTo(0.90);
        assertThat(retrieved.get().getAnalysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(retrieved.get().getModelName()).isEqualTo("TruthLens-PyTorch-SyncNet-DualStream");
        assertThat(retrieved.get().getModelVersion()).isEqualTo("TruthLens-SyncNet-v1.0-dev");
    }

    @Test
    @DisplayName("Unique media_id constraint: cannot insert two analyses for same media asset")
    void uniqueConstraint_duplicateMediaId_throwsException() {
        Media media = createVideoMedia("duplicate_sync.mp4", "222233334444555566667777888899990000aaaabbbbccccddddeeeeffff1111");

        AvSyncAnalysis analysis1 = new AvSyncAnalysis(media);
        analysis1.setSyncScore(0.70);
        avSyncAnalysisRepository.saveAndFlush(analysis1);

        AvSyncAnalysis analysis2 = new AvSyncAnalysis(media);
        analysis2.setSyncScore(0.40);

        assertThatThrownBy(() -> avSyncAnalysisRepository.saveAndFlush(analysis2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Check constraint: sync_score must be between 0.0 and 1.0")
    void checkConstraint_invalidSyncScore_throwsException() {
        Media media = createVideoMedia("invalid_score.mp4", "33334444555566667777888899990000aaaabbbbccccddddeeeeffff11112222");

        AvSyncAnalysis analysis = new AvSyncAnalysis(media);
        analysis.setSyncScore(1.50); // Out of bounds

        assertThatThrownBy(() -> avSyncAnalysisRepository.saveAndFlush(analysis))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Foreign Key Cascade: deleting media cascades to delete associated AvSyncAnalysis")
    void cascadeDelete_mediaDeletionDeletesAnalysis() {
        Media media = createVideoMedia("cascade_media.mp4", "4444555566667777888899990000aaaabbbbccccddddeeeeffff111122223333");

        AvSyncAnalysis analysis = new AvSyncAnalysis(media);
        analysis.setSyncScore(0.92);
        avSyncAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        assertThat(avSyncAnalysisRepository.existsByMediaId(media.getId())).isTrue();

        mediaRepository.deleteById(media.getId());
        entityManager.flush();
        entityManager.clear();

        assertThat(avSyncAnalysisRepository.existsByMediaId(media.getId())).isFalse();
    }
}
