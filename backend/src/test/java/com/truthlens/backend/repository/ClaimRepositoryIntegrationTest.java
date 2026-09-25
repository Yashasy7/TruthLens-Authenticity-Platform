package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Claim;
import com.truthlens.backend.entity.ClaimEntityType;
import com.truthlens.backend.entity.ClaimSourceType;
import com.truthlens.backend.entity.ClaimType;
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

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("ClaimRepository — Integration & Schema Tests (Flyway V11)")
class ClaimRepositoryIntegrationTest {

    @Autowired
    private ClaimRepository claimRepository;

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

        testUser = new User("claim_analyst@truthlens.org", "HashedSecret123!", "Claim Analyst");
        testUser.getRoles().add(role);
        testUser = userRepository.saveAndFlush(testUser);

        testMedia = new Media(
                testUser,
                "evidence_speech.wav",
                "quarantine/evidence_speech.wav",
                MediaType.AUDIO,
                "audio/wav",
                32768L,
                "b1c2d3e4f5061728394a5b6c7d8e9f0123456789abcdef0123456789abcdef0",
                UploadStatus.UPLOADED
        );
        testMedia = mediaRepository.saveAndFlush(testMedia);
        entityManager.flush();
    }

    @Test
    @DisplayName("save: persists Claim record and generates UUID and audit timestamps")
    void save_persistsRecord() {
        Claim claim = new Claim(
                testMedia,
                "The Prime Minister announced a $5 billion package.",
                "the prime minister announced a $5 billion package.",
                ClaimType.FACTUAL_CLAIM,
                "The Prime Minister",
                "announced",
                "a $5 billion package",
                ClaimEntityType.MONEY,
                0.95,
                "111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
                ClaimSourceType.TRANSCRIPT,
                0,
                0,
                52,
                "[]",
                AnalysisStatus.COMPLETED
        );

        Claim saved = claimRepository.save(claim);
        entityManager.flush();

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(saved.getUpdatedAt()).isNotNull();
        assertThat(saved.getClaimText()).isEqualTo("The Prime Minister announced a $5 billion package.");
        assertThat(saved.getClaimType()).isEqualTo(ClaimType.FACTUAL_CLAIM);
        assertThat(saved.getEntityType()).isEqualTo(ClaimEntityType.MONEY);
        assertThat(saved.getSubject()).isEqualTo("The Prime Minister");
        assertThat(saved.getAction()).isEqualTo("announced");
        assertThat(saved.getValue()).isEqualTo("a $5 billion package");
    }

    @Test
    @DisplayName("findByMediaIdOrderBySentenceIndexAsc: retrieves claims ordered by sentence index")
    void findByMediaId_retrievesOrderedClaims() {
        Claim claim2 = new Claim(
                testMedia, "Sentence two claim.", "sentence two claim.",
                ClaimType.FACTUAL_CLAIM, "Subject 2", "Action 2", "Value 2",
                ClaimEntityType.GENERAL, 0.85, "hash222222222222222222222222222222222222222222222222222222222222",
                ClaimSourceType.TRANSCRIPT, 1, 25, 45, "[]", AnalysisStatus.COMPLETED
        );
        Claim claim1 = new Claim(
                testMedia, "Sentence one claim.", "sentence one claim.",
                ClaimType.FACTUAL_CLAIM, "Subject 1", "Action 1", "Value 1",
                ClaimEntityType.GENERAL, 0.90, "hash111111111111111111111111111111111111111111111111111111111111",
                ClaimSourceType.TRANSCRIPT, 0, 0, 20, "[]", AnalysisStatus.COMPLETED
        );

        claimRepository.save(claim2);
        claimRepository.save(claim1);
        entityManager.flush();

        List<Claim> retrieved = claimRepository.findByMediaIdOrderBySentenceIndexAsc(testMedia.getId());
        assertThat(retrieved).hasSize(2);
        assertThat(retrieved.get(0).getSentenceIndex()).isEqualTo(0);
        assertThat(retrieved.get(1).getSentenceIndex()).isEqualTo(1);
    }

    @Test
    @DisplayName("save: enforces uniqueness on (media_id, claim_hash)")
    void save_duplicateHash_throwsDataIntegrityViolationException() {
        String sameHash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

        Claim c1 = new Claim(
                testMedia, "Claim A", "claim a", ClaimType.FACTUAL_CLAIM,
                "Subj", "Act", "Val", ClaimEntityType.GENERAL, 0.9, sameHash,
                ClaimSourceType.TRANSCRIPT, 0, 0, 10, "[]", AnalysisStatus.COMPLETED
        );
        claimRepository.saveAndFlush(c1);

        Claim c2 = new Claim(
                testMedia, "Claim B with same hash", "claim a", ClaimType.FACTUAL_CLAIM,
                "Subj", "Act", "Val", ClaimEntityType.GENERAL, 0.9, sameHash,
                ClaimSourceType.TRANSCRIPT, 1, 11, 30, "[]", AnalysisStatus.COMPLETED
        );

        assertThatThrownBy(() -> claimRepository.saveAndFlush(c2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("deleteByMediaId: removes all claims for a given media asset")
    void deleteByMediaId_clearsAllClaims() {
        Claim claim = new Claim(
                testMedia, "Claim to delete", "claim to delete", ClaimType.FACTUAL_CLAIM,
                "Subj", "Act", "Val", ClaimEntityType.GENERAL, 0.9,
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                ClaimSourceType.TRANSCRIPT, 0, 0, 15, "[]", AnalysisStatus.COMPLETED
        );
        claimRepository.saveAndFlush(claim);
        assertThat(claimRepository.countByMediaId(testMedia.getId())).isEqualTo(1);

        claimRepository.deleteByMediaId(testMedia.getId());
        entityManager.flush();

        assertThat(claimRepository.countByMediaId(testMedia.getId())).isEqualTo(0);
    }

    @Test
    @DisplayName("cascade delete: deleting media cascades and removes its claims")
    void deleteMedia_cascadesToClaims() {
        Claim claim = new Claim(
                testMedia, "Cascade test claim", "cascade test claim", ClaimType.FACTUAL_CLAIM,
                "Subj", "Act", "Val", ClaimEntityType.GENERAL, 0.9,
                "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                ClaimSourceType.TRANSCRIPT, 0, 0, 20, "[]", AnalysisStatus.COMPLETED
        );
        claimRepository.save(claim);
        entityManager.flush();

        UUID mediaId = testMedia.getId();
        UUID claimId = claim.getId();
        entityManager.clear();

        mediaRepository.deleteById(mediaId);
        entityManager.flush();

        Optional<Claim> found = claimRepository.findById(claimId);
        assertThat(found).isEmpty();
    }
}
