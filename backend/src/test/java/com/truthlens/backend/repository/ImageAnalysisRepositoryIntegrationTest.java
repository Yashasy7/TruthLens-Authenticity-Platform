package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ImageAnalysis;
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
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("ImageAnalysisRepository — Real Database Integration Tests")
class ImageAnalysisRepositoryIntegrationTest {

    @Autowired
    private ImageAnalysisRepository imageAnalysisRepository;

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
        testUser = new User("img_db_test@truthlens.org", "secret_hash", "Image DB Tester");
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));
        testUser.getRoles().add(userRole);
        testUser = userRepository.saveAndFlush(testUser);
    }

    private Media createMedia(String filename, String sha256) {
        Media media = new Media(
                testUser,
                filename,
                "quarantine/image/" + filename,
                MediaType.IMAGE,
                "image/jpeg",
                4096L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("Flyway V5 schema & Persistence: save and retrieve ImageAnalysis with eager Media join")
    void saveAndRetrieve_success() {
        Media media = createMedia("photo1.jpg", "aaaa1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis analysis = new ImageAnalysis(media);
        analysis.setAiProb(0.85);
        analysis.setManipulationProb(0.42);
        analysis.setElaHeatmapUrl("quarantine/analysis/ela/sample1.png");
        analysis.setGradcamHeatmapUrl("quarantine/analysis/gradcam/sample1.png");
        analysis.setNoiseVariance(18.5);
        analysis.setFftAnomalyScore(0.35);
        analysis.setCopyMoveDetected(true);
        analysis.setSplicingDetected(false);
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelVersion("TruthLens-DiffusionClassifier-0.1.0-dev");
        analysis.setEvidenceJson("{\"noiseVariance\":18.5,\"fftAnomalyScore\":0.35}");

        ImageAnalysis saved = imageAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        Optional<ImageAnalysis> retrieved = imageAnalysisRepository.findByMediaId(media.getId());
        assertThat(retrieved).isPresent();
        assertThat(retrieved.get().getId()).isEqualTo(saved.getId());
        assertThat(retrieved.get().getAiProb()).isEqualTo(0.85);
        assertThat(retrieved.get().getManipulationProb()).isEqualTo(0.42);
        assertThat(retrieved.get().getElaHeatmapUrl()).isEqualTo("quarantine/analysis/ela/sample1.png");
        assertThat(retrieved.get().getGradcamHeatmapUrl()).isEqualTo("quarantine/analysis/gradcam/sample1.png");
        assertThat(retrieved.get().getNoiseVariance()).isEqualTo(18.5);
        assertThat(retrieved.get().getFftAnomalyScore()).isEqualTo(0.35);
        assertThat(retrieved.get().isCopyMoveDetected()).isTrue();
        assertThat(retrieved.get().isSplicingDetected()).isFalse();
        assertThat(retrieved.get().getAnalysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(retrieved.get().getModelVersion()).isEqualTo("TruthLens-DiffusionClassifier-0.1.0-dev");
        assertThat(retrieved.get().getEvidenceJson()).contains("noiseVariance");

        // Verify eager join
        Optional<ImageAnalysis> eagerlyFetched = imageAnalysisRepository.findByMediaIdWithMedia(media.getId());
        assertThat(eagerlyFetched).isPresent();
        assertThat(eagerlyFetched.get().getMedia().getOriginalFilename()).isEqualTo("photo1.jpg");
    }

    @Test
    @DisplayName("Unique constraint on media_id: duplicate analysis row for same media must fail")
    void duplicateMediaId_failsUniqueConstraint() {
        Media media = createMedia("photo2.jpg", "bbbb1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis analysis1 = new ImageAnalysis(media);
        analysis1.setAiProb(0.10);
        analysis1.setManipulationProb(0.05);
        imageAnalysisRepository.saveAndFlush(analysis1);

        ImageAnalysis analysis2 = new ImageAnalysis(media);
        analysis2.setAiProb(0.90);
        analysis2.setManipulationProb(0.80);

        assertThatThrownBy(() -> imageAnalysisRepository.saveAndFlush(analysis2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Foreign Key Cascade: deleting media cascades and deletes associated ImageAnalysis")
    void deleteMedia_cascadesToImageAnalysis() {
        Media media = createMedia("photo3.jpg", "cccc1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis analysis = new ImageAnalysis(media);
        analysis.setAiProb(0.30);
        analysis.setManipulationProb(0.20);
        imageAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        assertThat(imageAnalysisRepository.findByMediaId(media.getId())).isPresent();

        mediaRepository.deleteById(media.getId());
        entityManager.flush();
        entityManager.clear();

        assertThat(imageAnalysisRepository.findByMediaId(media.getId())).isEmpty();
    }

    @Test
    @DisplayName("CHECK constraint: ai_prob must be between 0.0 and 1.0")
    void aiProbConstraint_violatesBounds() {
        Media media = createMedia("photo4.jpg", "dddd1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis invalid = new ImageAnalysis(media);
        invalid.setAiProb(1.5); // Invalid: > 1.0

        assertThatThrownBy(() -> imageAnalysisRepository.saveAndFlush(invalid))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("CHECK constraint: manipulation_prob must be between 0.0 and 1.0")
    void manipulationProbConstraint_violatesBounds() {
        Media media = createMedia("photo5.jpg", "eeee1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis invalid = new ImageAnalysis(media);
        invalid.setManipulationProb(-0.1); // Invalid: < 0.0

        assertThatThrownBy(() -> imageAnalysisRepository.saveAndFlush(invalid))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Query methods: findFlaggedManipulations filters by probability thresholds")
    void findFlaggedManipulations_filtersCorrectly() {
        Media m1 = createMedia("low.jpg", "11111111222233334444555566667777888899990000aaaabbbbccccddddeeee");
        Media m2 = createMedia("high_ai.jpg", "22221111222233334444555566667777888899990000aaaabbbbccccddddeeee");
        Media m3 = createMedia("high_manip.jpg", "33331111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        ImageAnalysis a1 = new ImageAnalysis(m1);
        a1.setAiProb(0.1);
        a1.setManipulationProb(0.1);
        imageAnalysisRepository.saveAndFlush(a1);

        ImageAnalysis a2 = new ImageAnalysis(m2);
        a2.setAiProb(0.85);
        a2.setManipulationProb(0.15);
        a2.setCopyMoveDetected(true); // Flagged via copy-move
        imageAnalysisRepository.saveAndFlush(a2);

        ImageAnalysis a3 = new ImageAnalysis(m3);
        a3.setAiProb(0.2);
        a3.setManipulationProb(0.9); // Flagged via manipulationProb >= 0.50
        imageAnalysisRepository.saveAndFlush(a3);

        List<ImageAnalysis> flagged = imageAnalysisRepository.findFlaggedManipulations(PageRequest.of(0, 10));
        assertThat(flagged).hasSize(2);
        assertThat(flagged).extracting(ImageAnalysis::getId)
                .containsExactlyInAnyOrder(a2.getId(), a3.getId());
    }
}
