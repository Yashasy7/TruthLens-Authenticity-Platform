package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.OcrResult;
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
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
class OcrResultRepositoryIntegrationTest {

    @Autowired
    private OcrResultRepository ocrResultRepository;

    @Autowired
    private MediaRepository mediaRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private RoleRepository roleRepository;

    @Autowired
    private TestEntityManager entityManager;

    private User testUser;
    private Media testMedia;

    @BeforeEach
    void setUp() {
        Role role = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));

        testUser = new User("ocr_analyst@truthlens.org", "HashedSecret123!", "OCR Analyst");
        testUser.getRoles().add(role);
        testUser = userRepository.saveAndFlush(testUser);

        testMedia = new Media(
                testUser,
                "banner.png",
                "quarantine/banner.png",
                MediaType.IMAGE,
                "image/png",
                1024L,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                UploadStatus.UPLOADED
        );
        testMedia = mediaRepository.saveAndFlush(testMedia);
        entityManager.flush();
    }

    @Test
    @DisplayName("save: persists OcrResult record and generates UUID and audit timestamps")
    void save_persistsRecord() {
        OcrResult result = new OcrResult(
                testMedia,
                "BREAKING NEWS ALERT",
                "en",
                0.95,
                1,
                "[{\"text\":\"BREAKING NEWS ALERT\",\"confidence\":0.95}]",
                "{\"engine\":\"EasyOCR\"}",
                AnalysisStatus.COMPLETED
        );

        OcrResult saved = ocrResultRepository.save(result);
        entityManager.flush();

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(saved.getUpdatedAt()).isNotNull();
        assertThat(saved.getExtractedText()).isEqualTo("BREAKING NEWS ALERT");
        assertThat(saved.getConfidenceScore()).isEqualTo(0.95);
        assertThat(saved.getRegionsCount()).isEqualTo(1);
    }

    @Test
    @DisplayName("findByMediaId: retrieves persisted analysis by media UUID")
    void findByMediaId_retrievesEntity() {
        OcrResult result = new OcrResult(
                testMedia,
                "VERIFIED CONTENT",
                "en",
                0.88,
                1,
                "[]",
                "{}",
                AnalysisStatus.COMPLETED
        );
        ocrResultRepository.save(result);
        entityManager.flush();

        Optional<OcrResult> found = ocrResultRepository.findByMediaId(testMedia.getId());
        assertThat(found).isPresent();
        assertThat(found.get().getExtractedText()).isEqualTo("VERIFIED CONTENT");
        assertThat(found.get().getLanguage()).isEqualTo("en");
    }

    @Test
    @DisplayName("save: enforces unique constraint on media_id")
    void save_duplicateMediaId_throwsException() {
        OcrResult result1 = new OcrResult(
                testMedia, "TEXT 1", "en", 0.9, 1, "[]", "{}", AnalysisStatus.COMPLETED
        );
        ocrResultRepository.saveAndFlush(result1);

        OcrResult result2 = new OcrResult(
                testMedia, "TEXT 2", "en", 0.8, 1, "[]", "{}", AnalysisStatus.COMPLETED
        );

        assertThatThrownBy(() -> ocrResultRepository.saveAndFlush(result2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("cascade delete: deleting media cascades and removes ocr_results record")
    void deleteMedia_cascadesToOcrResult() {
        OcrResult result = new OcrResult(
                testMedia, "NEWS BANNER", "en", 0.92, 1, "[]", "{}", AnalysisStatus.COMPLETED
        );
        ocrResultRepository.save(result);
        entityManager.flush();

        UUID mediaId = testMedia.getId();
        entityManager.clear();

        mediaRepository.deleteById(mediaId);
        entityManager.flush();

        Optional<OcrResult> deletedRecord = ocrResultRepository.findByMediaId(mediaId);
        assertThat(deletedRecord).isEmpty();
    }
}
