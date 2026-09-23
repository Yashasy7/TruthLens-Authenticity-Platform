package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.entity.VideoAnalysis;
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
@DisplayName("VideoAnalysisRepository — Real Database Integration Tests (Flyway V6)")
class VideoAnalysisRepositoryIntegrationTest {

    @Autowired
    private VideoAnalysisRepository videoAnalysisRepository;

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
        testUser = new User("vid_db_test@truthlens.org", "secret_hash", "Video DB Tester");
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
                1048576L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("Flyway V6 schema & Persistence: save and retrieve VideoAnalysis with eager Media join")
    void saveAndRetrieve_success() {
        Media media = createVideoMedia("interview.mp4", "bbbb1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        VideoAnalysis analysis = new VideoAnalysis(media);
        analysis.setDeepfakeProb(0.82);
        analysis.setFaceCount(2);
        analysis.setTotalFramesSampled(15);
        analysis.setSuspiciousTimestampsJson("[{\"timestamp_seconds\":1.5,\"frame_index\":3,\"score\":0.85,\"reason\":\"HIGH_SYNTHETIC_FACE_PROBABILITY\"}]");
        analysis.setFrameScoresJson("[{\"frame_index\":3,\"timestamp_seconds\":1.5,\"deepfake_score\":0.85,\"temporal_inconsistency\":0.60,\"faces_detected\":2,\"is_suspicious\":true}]");
        analysis.setAnalysisStatus(AnalysisStatus.COMPLETED);
        analysis.setModelVersion("TruthLens-VideoDeepfakeClassifier-0.1.0-dev");

        VideoAnalysis saved = videoAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        Optional<VideoAnalysis> retrieved = videoAnalysisRepository.findByMediaId(media.getId());
        assertThat(retrieved).isPresent();
        assertThat(retrieved.get().getId()).isEqualTo(saved.getId());
        assertThat(retrieved.get().getDeepfakeProb()).isEqualTo(0.82);
        assertThat(retrieved.get().getFaceCount()).isEqualTo(2);
        assertThat(retrieved.get().getTotalFramesSampled()).isEqualTo(15);
        assertThat(retrieved.get().getAnalysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(retrieved.get().getModelVersion()).isEqualTo("TruthLens-VideoDeepfakeClassifier-0.1.0-dev");
    }

    @Test
    @DisplayName("Unique media_id constraint: inserting duplicate analysis record throws DataIntegrityViolationException")
    void duplicateMediaId_throwsException() {
        Media media = createVideoMedia("clip.mp4", "cccc1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        VideoAnalysis first = new VideoAnalysis(media);
        first.setDeepfakeProb(0.30);
        videoAnalysisRepository.saveAndFlush(first);

        VideoAnalysis second = new VideoAnalysis(media);
        second.setDeepfakeProb(0.40);

        assertThatThrownBy(() -> videoAnalysisRepository.saveAndFlush(second))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Foreign Key Cascade: deleting Media cascade-deletes associated VideoAnalysis")
    void cascadeDelete_mediaRemoved_removesVideoAnalysis() {
        Media media = createVideoMedia("temp_deepfake.mp4", "dddd1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        VideoAnalysis analysis = new VideoAnalysis(media);
        analysis.setDeepfakeProb(0.95);
        videoAnalysisRepository.saveAndFlush(analysis);
        entityManager.clear();

        assertThat(videoAnalysisRepository.existsByMediaId(media.getId())).isTrue();

        mediaRepository.deleteById(media.getId());
        entityManager.flush();
        entityManager.clear();

        assertThat(videoAnalysisRepository.existsByMediaId(media.getId())).isFalse();
    }

    @Test
    @DisplayName("Probability Bounds Check: negative deepfake_prob violates DB check constraint")
    void checkConstraint_negativeDeepfakeProb_throwsException() {
        Media media = createVideoMedia("invalid_prob.mp4", "eeee1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        VideoAnalysis invalid = new VideoAnalysis(media);
        invalid.setDeepfakeProb(-0.1);

        assertThatThrownBy(() -> videoAnalysisRepository.saveAndFlush(invalid))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Probability Bounds Check: deepfake_prob > 1.0 violates DB check constraint")
    void checkConstraint_excessiveDeepfakeProb_throwsException() {
        Media media = createVideoMedia("excessive_prob.mp4", "ffff1111222233334444555566667777888899990000aaaabbbbccccddddeeee");

        VideoAnalysis invalid = new VideoAnalysis(media);
        invalid.setDeepfakeProb(1.5);

        assertThatThrownBy(() -> videoAnalysisRepository.saveAndFlush(invalid))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Query flagged deepfakes: returns records with probability >= 0.50")
    void findFlaggedDeepfakes_returnsElevatedScores() {
        Media cleanMedia = createVideoMedia("clean.mp4", "00001111222233334444555566667777888899990000aaaabbbbccccddddeeee");
        VideoAnalysis clean = new VideoAnalysis(cleanMedia);
        clean.setDeepfakeProb(0.15);
        videoAnalysisRepository.saveAndFlush(clean);

        Media suspiciousMedia = createVideoMedia("suspicious.mp4", "11111111222233334444555566667777888899990000aaaabbbbccccddddeeee");
        VideoAnalysis suspicious = new VideoAnalysis(suspiciousMedia);
        suspicious.setDeepfakeProb(0.85);
        videoAnalysisRepository.saveAndFlush(suspicious);

        List<VideoAnalysis> flagged = videoAnalysisRepository.findFlaggedDeepfakes(PageRequest.of(0, 10));
        assertThat(flagged).hasSize(1);
        assertThat(flagged.get(0).getMedia().getId()).isEqualTo(suspiciousMedia.getId());
    }
}
