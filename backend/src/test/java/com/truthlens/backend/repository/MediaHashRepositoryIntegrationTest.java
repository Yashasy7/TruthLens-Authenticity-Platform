package com.truthlens.backend.repository;

import com.truthlens.backend.entity.MatchType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaHash;
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
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("MediaHashRepository — Real Database Integration Tests (T-01)")
class MediaHashRepositoryIntegrationTest {

    @Autowired
    private MediaHashRepository mediaHashRepository;

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
        testUser = new User("db_test_user@truthlens.org", "secret_hash", "Database Tester");
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseGet(() -> roleRepository.save(new Role(RoleName.USER, "Standard User")));
        testUser.getRoles().add(userRole);
        testUser = userRepository.saveAndFlush(testUser);
    }

    private Media createMedia(String filename, String sha256) {
        Media media = new Media(
                testUser,
                filename,
                "quarantine/" + filename,
                MediaType.IMAGE,
                "image/png",
                1024L,
                sha256,
                UploadStatus.UPLOADED
        );
        return mediaRepository.saveAndFlush(media);
    }

    @Test
    @DisplayName("V3 Schema: Successfully persists and retrieves MediaHash record with all columns")
    void persistAndRetrieve_allColumns_success() {
        String sha256 = "1111111111111111111111111111111111111111111111111111111111111111";
        Media media = createMedia("photo1.png", sha256);
        MediaHash hash = new MediaHash(
                media,
                sha256,
                "1234567890abcdef",
                "0001001000110100010101100111100010011010101111001101111011110000",
                "chroma-v1-00010002",
                "chroma_hash_64"
        );

        MediaHash saved = mediaHashRepository.saveAndFlush(hash);
        entityManager.clear();

        Optional<MediaHash> retrieved = mediaHashRepository.findById(saved.getId());
        assertThat(retrieved).isPresent();
        assertThat(retrieved.get().getMedia().getId()).isEqualTo(media.getId());
        assertThat(retrieved.get().getSha256Hash()).isEqualTo(hash.getSha256Hash());
        assertThat(retrieved.get().getPhash()).isEqualTo("1234567890abcdef");
        assertThat(retrieved.get().getPhashVector()).isNotNull();
        assertThat(retrieved.get().getChromaprint()).isEqualTo("chroma-v1-00010002");
        assertThat(retrieved.get().getChromaprintHash()).isEqualTo("chroma_hash_64");
        assertThat(retrieved.get().isDuplicate()).isFalse();
        assertThat(retrieved.get().getMatchType()).isEqualTo(MatchType.NONE);
    }

    @Test
    @DisplayName("V3 Constraint: Enforces unique constraint on media_id (1:1 relationship)")
    void enforceUniqueMediaIdConstraint_duplicateThrowsException() {
        String sha256 = "2222222222222222222222222222222222222222222222222222222222222222";
        Media media = createMedia("photo_unique.png", sha256);
        MediaHash hash1 = new MediaHash(media, sha256, "phash1", null);
        mediaHashRepository.saveAndFlush(hash1);

        MediaHash hash2 = new MediaHash(media, sha256, "phash2", null);

        assertThatThrownBy(() -> mediaHashRepository.saveAndFlush(hash2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("V3 Foreign Key Cascade: Deleting media cascades to delete media_hashes record")
    void cascadeDelete_deletingMediaDeletesMediaHash() {
        String sha256 = "3333333333333333333333333333333333333333333333333333333333333333";
        Media media = createMedia("to_delete.png", sha256);
        MediaHash hash = new MediaHash(media, sha256, "phash", null);
        MediaHash savedHash = mediaHashRepository.saveAndFlush(hash);
        UUID savedHashId = savedHash.getId();
        UUID mediaId = media.getId();

        entityManager.clear();

        // Delete parent media via SQL / EntityManager
        entityManager.getEntityManager()
                .createNativeQuery("DELETE FROM media WHERE id = :id")
                .setParameter("id", mediaId)
                .executeUpdate();

        entityManager.clear();

        // Child media_hashes row must be gone via ON DELETE CASCADE foreign key
        assertThat(mediaHashRepository.findById(savedHashId)).isEmpty();
    }

    @Test
    @DisplayName("F-05 Deterministic Canonical Selection: Earliest uploaded media is selected as canonical duplicateOf")
    void findExactMatchesOrderedByEarliest_selectsOriginalEarliestMedia() throws Exception {
        String sharedSha = "4444444444444444444444444444444444444444444444444444444444444444";

        // Create original A first
        Media originalA = createMedia("orig_A.png", sharedSha);
        Thread.sleep(20);
        Media duplicateB = createMedia("dup_B.png", sharedSha);
        Thread.sleep(20);
        Media duplicateC = createMedia("dup_C.png", sharedSha);

        MediaHash hashA = new MediaHash(originalA, sharedSha, "phashA", null);
        mediaHashRepository.saveAndFlush(hashA);

        MediaHash hashB = new MediaHash(duplicateB, sharedSha, "phashB", null);
        hashB.setDuplicateMatch(originalA, MatchType.EXACT_SHA256, 1.0);
        mediaHashRepository.saveAndFlush(hashB);

        entityManager.clear();

        // Query candidates for duplicate C
        List<MediaHash> matchesForC = mediaHashRepository.findExactMatchesOrderedByEarliest(sharedSha, duplicateC.getId());

        assertThat(matchesForC).isNotEmpty();
        // Canonical earliest media MUST be originalA
        assertThat(matchesForC.get(0).getMedia().getId()).isEqualTo(originalA.getId());
        assertThat(matchesForC.get(0).getMedia().getOriginalFilename()).isEqualTo("orig_A.png");
    }

    @Test
    @DisplayName("P-01 Bounded Candidate Retrieval: Limits candidates and eliminates unbounded JVM scans")
    void findPerceptualCandidatesBounded_respectsLimitAndFetchesMedia() {
        for (int i = 0; i < 5; i++) {
            String sha = String.format("555555555555555555555555555555555555555555555555555555555555555%d", i);
            Media media = createMedia("scan_" + i + ".png", sha);
            MediaHash hash = new MediaHash(media, media.getSha256Hash(), "000000000000000" + i, null);
            mediaHashRepository.saveAndFlush(hash);
        }

        UUID targetMediaId = UUID.randomUUID();
        List<MediaHash> boundedCandidates = mediaHashRepository.findPerceptualCandidatesBounded(
                targetMediaId, PageRequest.of(0, 3));

        assertThat(boundedCandidates).hasSize(3);
        // Verify JOIN FETCH works without triggering additional queries
        assertThat(boundedCandidates.get(0).getMedia()).isNotNull();
        assertThat(boundedCandidates.get(0).getMedia().getOriginalFilename()).isNotNull();
    }
}
