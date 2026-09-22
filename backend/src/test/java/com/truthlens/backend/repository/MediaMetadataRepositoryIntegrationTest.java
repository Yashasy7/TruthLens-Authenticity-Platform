package com.truthlens.backend.repository;

import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaMetadata;
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

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("MediaMetadataRepository — Real Database Integration Tests")
class MediaMetadataRepositoryIntegrationTest {

    @Autowired
    private MediaMetadataRepository mediaMetadataRepository;

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
        testUser = new User("meta_db_test@truthlens.org", "secret_hash", "Metadata DB Tester");
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));
        testUser.getRoles().add(userRole);
        testUser = userRepository.saveAndFlush(testUser);
    }

    private Media createMedia(String filename, String sha256) {
        Media media = new Media(
                testUser,
                filename,
                "quarantine/meta/" + filename,
                MediaType.IMAGE,
                "image/jpeg",
                2048L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("Persistence & Flyway V4 schema: can save and retrieve MediaMetadata with eager Media join")
    void saveAndRetrieve_success() {
        Media media = createMedia("photo1.jpg", "1111111111111111111111111111111111111111111111111111111111111111");

        MediaMetadata meta = new MediaMetadata(media);
        meta.setCameraMake("Nikon");
        meta.setCameraModel("D850");
        meta.setLensModel("AF-S NIKKOR 24-70mm f/2.8E ED VR");
        meta.setSoftwareTag("Firmware 1.20");
        meta.setCapturedAt(OffsetDateTime.now(ZoneOffset.UTC).minusDays(1));
        meta.setGpsLatitude(40.7128);
        meta.setGpsLongitude(-74.0060);
        meta.setWidth(6000);
        meta.setHeight(4000);
        meta.setRawJson("{\"Make\":\"Nikon\",\"Model\":\"D850\"}");
        meta.setAnomalyFlags("[]");
        meta.setHasAnomalies(false);
        meta.setAnomalyCount(0);
        meta.setForensicScore(0.0);
        meta.setExtractionEngine("JAVA_METADATA_EXTRACTOR");

        MediaMetadata saved = mediaMetadataRepository.saveAndFlush(meta);
        entityManager.clear();

        Optional<MediaMetadata> fetched = mediaMetadataRepository.findByMediaIdWithMedia(media.getId());
        assertThat(fetched).isPresent();
        assertThat(fetched.get().getCameraMake()).isEqualTo("Nikon");
        assertThat(fetched.get().getCameraModel()).isEqualTo("D850");
        assertThat(fetched.get().getWidth()).isEqualTo(6000);
        assertThat(fetched.get().getMedia().getId()).isEqualTo(media.getId());
        assertThat(fetched.get().getCreatedAt()).isNotNull();
        assertThat(fetched.get().getUpdatedAt()).isNotNull();
    }

    @Test
    @DisplayName("Foreign key ON DELETE CASCADE: deleting Media automatically deletes associated MediaMetadata")
    void cascadeDelete_success() {
        Media media = createMedia("photo_cascade.jpg", "2222222222222222222222222222222222222222222222222222222222222222");

        MediaMetadata meta = new MediaMetadata(media);
        meta.setCameraMake("Canon");
        meta.setRawJson("{}");
        mediaMetadataRepository.saveAndFlush(meta);
        entityManager.clear();

        // Delete parent media
        mediaRepository.deleteById(media.getId());
        entityManager.flush();
        entityManager.clear();

        Optional<MediaMetadata> metadataAfterDelete = mediaMetadataRepository.findByMediaId(media.getId());
        assertThat(metadataAfterDelete).isEmpty();
    }

    @Test
    @DisplayName("Unique constraint uq_metadata_media_id: duplicate MediaMetadata for same Media is rejected")
    void uniqueConstraint_duplicateMediaId_throwsException() {
        Media media = createMedia("photo_dup.jpg", "3333333333333333333333333333333333333333333333333333333333333333");

        MediaMetadata meta1 = new MediaMetadata(media);
        meta1.setCameraMake("Sony");
        meta1.setRawJson("{}");
        mediaMetadataRepository.saveAndFlush(meta1);

        MediaMetadata meta2 = new MediaMetadata(media);
        meta2.setCameraMake("Sony Duplicate");
        meta2.setRawJson("{}");

        assertThatThrownBy(() -> {
            mediaMetadataRepository.saveAndFlush(meta2);
        }).isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("Check constraint ck_metadata_forensic_score: forensicScore > 1.0 is rejected")
    void checkConstraint_forensicScoreRange_throwsException() {
        Media media = createMedia("photo_score.jpg", "4444444444444444444444444444444444444444444444444444444444444444");

        MediaMetadata meta = new MediaMetadata(media);
        meta.setRawJson("{}");
        meta.setForensicScore(1.50); // Violates check constraint (0.0 to 1.0)

        assertThatThrownBy(() -> {
            mediaMetadataRepository.saveAndFlush(meta);
        }).isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("findAnomalousWithMedia: retrieves anomalous records ordered by forensic score descending")
    void findAnomalousWithMedia_success() {
        Media media1 = createMedia("anom1.jpg", "5555555555555555555555555555555555555555555555555555555555555555");
        Media media2 = createMedia("anom2.jpg", "6666666666666666666666666666666666666666666666666666666666666666");

        MediaMetadata meta1 = new MediaMetadata(media1);
        meta1.setRawJson("{}");
        meta1.setHasAnomalies(true);
        meta1.setAnomalyCount(1);
        meta1.setForensicScore(0.35);
        mediaMetadataRepository.saveAndFlush(meta1);

        MediaMetadata meta2 = new MediaMetadata(media2);
        meta2.setRawJson("{}");
        meta2.setHasAnomalies(true);
        meta2.setAnomalyCount(2);
        meta2.setForensicScore(0.70);
        mediaMetadataRepository.saveAndFlush(meta2);

        entityManager.clear();

        List<MediaMetadata> results = mediaMetadataRepository.findAnomalousWithMedia(PageRequest.of(0, 10));

        assertThat(results).hasSize(2);
        assertThat(results.get(0).getForensicScore()).isEqualTo(0.70);
        assertThat(results.get(1).getForensicScore()).isEqualTo(0.35);
    }
}
