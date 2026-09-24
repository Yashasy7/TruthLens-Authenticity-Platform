package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.Transcript;
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
class TranscriptRepositoryIntegrationTest {

    @Autowired
    private TranscriptRepository transcriptRepository;

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

        testUser = new User("stt_analyst@truthlens.org", "HashedSecret123!", "STT Analyst");
        testUser.getRoles().add(role);
        testUser = userRepository.saveAndFlush(testUser);

        testMedia = new Media(
                testUser,
                "speech.wav",
                "quarantine/speech.wav",
                MediaType.AUDIO,
                "audio/wav",
                16384L,
                "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
                UploadStatus.UPLOADED
        );
        testMedia = mediaRepository.saveAndFlush(testMedia);
        entityManager.flush();
    }

    @Test
    @DisplayName("save: persists Transcript record and generates UUID and audit timestamps")
    void save_persistsRecord() {
        Transcript transcript = new Transcript(
                testMedia,
                "This is a verified audio recording.",
                "en",
                0.96,
                3.5,
                1,
                6,
                "[{\"id\":0,\"start\":0.0,\"end\":3.5,\"text\":\"This is a verified audio recording.\"}]",
                "{\"model_name\":\"Faster-Whisper\",\"model_size\":\"tiny\"}",
                AnalysisStatus.COMPLETED
        );

        Transcript saved = transcriptRepository.save(transcript);
        entityManager.flush();

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(saved.getUpdatedAt()).isNotNull();
        assertThat(saved.getFullText()).isEqualTo("This is a verified audio recording.");
        assertThat(saved.getConfidenceScore()).isEqualTo(0.96);
        assertThat(saved.getSegmentsCount()).isEqualTo(1);
        assertThat(saved.getWordsCount()).isEqualTo(6);
    }

    @Test
    @DisplayName("findByMediaId: retrieves persisted transcript by media UUID")
    void findByMediaId_retrievesEntity() {
        Transcript transcript = new Transcript(
                testMedia,
                "Hello world verification.",
                "en",
                0.92,
                2.0,
                1,
                3,
                "[]",
                "{}",
                AnalysisStatus.COMPLETED
        );
        transcriptRepository.save(transcript);
        entityManager.flush();

        Optional<Transcript> found = transcriptRepository.findByMediaId(testMedia.getId());
        assertThat(found).isPresent();
        assertThat(found.get().getFullText()).isEqualTo("Hello world verification.");
        assertThat(found.get().getLanguage()).isEqualTo("en");
    }

    @Test
    @DisplayName("save: enforces unique constraint on media_id")
    void save_duplicateMediaId_throwsException() {
        Transcript t1 = new Transcript(
                testMedia, "Transcript 1", "en", 0.9, 1.0, 1, 2, "[]", "{}", AnalysisStatus.COMPLETED
        );
        transcriptRepository.saveAndFlush(t1);

        Transcript t2 = new Transcript(
                testMedia, "Transcript 2", "en", 0.8, 1.0, 1, 2, "[]", "{}", AnalysisStatus.COMPLETED
        );

        assertThatThrownBy(() -> transcriptRepository.saveAndFlush(t2))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    @DisplayName("cascade delete: deleting media cascades and removes transcripts record")
    void deleteMedia_cascadesToTranscript() {
        Transcript transcript = new Transcript(
                testMedia, "Cascade test transcript", "en", 0.95, 2.5, 1, 3, "[]", "{}", AnalysisStatus.COMPLETED
        );
        transcriptRepository.save(transcript);
        entityManager.flush();

        UUID mediaId = testMedia.getId();
        entityManager.clear();

        mediaRepository.deleteById(mediaId);
        entityManager.flush();

        Optional<Transcript> deletedRecord = transcriptRepository.findByMediaId(mediaId);
        assertThat(deletedRecord).isEmpty();
    }
}
