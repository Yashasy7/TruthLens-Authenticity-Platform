package com.truthlens.backend.service.fingerprint;

import com.truthlens.backend.entity.MatchType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaHash;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.repository.MediaHashRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("DuplicateDetectionService — Unit Tests (F-02, F-05, P-01)")
class DuplicateDetectionServiceTest {

    @Mock
    private MediaHashRepository mediaHashRepository;

    private PerceptualHashService perceptualHashService;
    private AcousticFingerprintService acousticFingerprintService;
    private DuplicateDetectionService duplicateDetectionService;

    private User user;
    private Media currentMedia;
    private Media existingMedia;
    private UUID currentMediaId;
    private UUID existingMediaId;

    @BeforeEach
    void setUp() throws Exception {
        perceptualHashService = new PerceptualHashService(10);
        acousticFingerprintService = new AcousticFingerprintService();
        duplicateDetectionService = new DuplicateDetectionService(
                mediaHashRepository,
                perceptualHashService,
                acousticFingerprintService
        );

        user = new User("user@truthlens.org", "hash", "Test User");
        currentMediaId = UUID.randomUUID();
        existingMediaId = UUID.randomUUID();

        currentMedia = new Media(user, "test.png", "path1", MediaType.IMAGE, "image/png", 100, "hash1", UploadStatus.UPLOADED);
        setPrivateField(currentMedia, "id", currentMediaId);

        existingMedia = new Media(user, "orig.png", "path2", MediaType.IMAGE, "image/png", 100, "hash1", UploadStatus.UPLOADED);
        setPrivateField(existingMedia, "id", existingMediaId);
    }

    private void setPrivateField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    @DisplayName("Detects exact duplicate using canonical earliest ordering (F-05)")
    void detectDuplicate_exactSha256Match_returnsExactDuplicateResult() {
        MediaHash existingHash = new MediaHash(existingMedia, "exact_sha256_hash", null, null);
        when(mediaHashRepository.findExactMatchesOrderedByEarliest("exact_sha256_hash", currentMediaId))
                .thenReturn(List.of(existingHash));

        DuplicateDetectionService.DuplicateResult result = duplicateDetectionService.detectDuplicate(
                currentMedia, "exact_sha256_hash", null, null
        );

        assertThat(result.isDuplicate()).isTrue();
        assertThat(result.matchType()).isEqualTo(MatchType.EXACT_SHA256);
        assertThat(result.similarityScore()).isEqualTo(1.0);
        assertThat(result.duplicateOf()).isEqualTo(existingMedia);
    }

    @Test
    @DisplayName("F-02 Regression: Calculates visual near-match similarity correctly from perceptual hash, not SHA-256")
    void detectDuplicate_nearMatchPHash_calculatesSimilarityCorrectly() {
        when(mediaHashRepository.findExactMatchesOrderedByEarliest("different_sha256", currentMediaId))
                .thenReturn(Collections.emptyList());

        String currentPhash = "0000000000000000";
        String candidatePhash = "0000000000000003"; // 2 bits difference out of 64

        MediaHash candidateHash = new MediaHash(existingMedia, "candidate_sha256_different_64_chars_long", candidatePhash, null);
        when(mediaHashRepository.findPerceptualCandidatesBounded(eq(currentMediaId), any(Pageable.class)))
                .thenReturn(List.of(candidateHash));

        DuplicateDetectionService.DuplicateResult result = duplicateDetectionService.detectDuplicate(
                currentMedia, "different_sha256", currentPhash, null
        );

        assertThat(result.isDuplicate()).isTrue();
        assertThat(result.matchType()).isEqualTo(MatchType.NEAR_MATCH_PHASH);
        // Distance is 2 -> similarity must be 1.0 - (2 / 64.0) = 0.96875
        double expectedSimilarity = 1.0 - (2.0 / 64.0);
        assertThat(result.similarityScore()).isEqualTo(expectedSimilarity);
        assertThat(result.duplicateOf()).isEqualTo(existingMedia);
    }

    @Test
    @DisplayName("T-02 Edge Case: Selects the closest candidate among multiple near-matches")
    void detectDuplicate_multipleCandidates_selectsClosestCandidate() throws Exception {
        when(mediaHashRepository.findExactMatchesOrderedByEarliest("different_sha256", currentMediaId))
                .thenReturn(Collections.emptyList());

        Media fartherMedia = new Media(user, "farther.png", "p3", MediaType.IMAGE, "image/png", 100, "h3", UploadStatus.UPLOADED);
        setPrivateField(fartherMedia, "id", UUID.randomUUID());

        String currentPhash = "0000000000000000";
        MediaHash candidate1 = new MediaHash(fartherMedia, "sha_far", "000000000000001f", null); // 5 bits different
        MediaHash candidate2 = new MediaHash(existingMedia, "sha_close", "0000000000000001", null); // 1 bit different

        when(mediaHashRepository.findPerceptualCandidatesBounded(eq(currentMediaId), any(Pageable.class)))
                .thenReturn(List.of(candidate1, candidate2));

        DuplicateDetectionService.DuplicateResult result = duplicateDetectionService.detectDuplicate(
                currentMedia, "different_sha256", currentPhash, null
        );

        assertThat(result.isDuplicate()).isTrue();
        assertThat(result.duplicateOf()).isEqualTo(existingMedia); // candidate2 chosen
        assertThat(result.similarityScore()).isEqualTo(1.0 - (1.0 / 64.0));
    }

    @Test
    @DisplayName("Detects acoustic duplicate for audio when chromaprint matches")
    void detectDuplicate_acousticMatch_returnsAcousticMatchResult() throws Exception {
        Media audioMedia = new Media(user, "clip.mp3", "audio/path", MediaType.AUDIO, "audio/mpeg", 200, "audio_sha", UploadStatus.UPLOADED);
        setPrivateField(audioMedia, "id", currentMediaId);

        when(mediaHashRepository.findExactMatchesOrderedByEarliest("audio_sha", currentMediaId))
                .thenReturn(Collections.emptyList());

        String chromaprint = "chroma-v1-000100020003";
        MediaHash candidateHash = new MediaHash(existingMedia, "other_sha", null, chromaprint);
        when(mediaHashRepository.findAcousticCandidatesBounded(eq(currentMediaId), any(Pageable.class)))
                .thenReturn(List.of(candidateHash));

        DuplicateDetectionService.DuplicateResult result = duplicateDetectionService.detectDuplicate(
                audioMedia, "audio_sha", null, chromaprint
        );

        assertThat(result.isDuplicate()).isTrue();
        assertThat(result.matchType()).isEqualTo(MatchType.ACOUSTIC_MATCH);
        assertThat(result.similarityScore()).isEqualTo(1.0);
        assertThat(result.duplicateOf()).isEqualTo(existingMedia);
    }

    @Test
    @DisplayName("Returns noMatch when no exact, visual, or acoustic match is found")
    void detectDuplicate_noMatch_returnsNotDuplicate() {
        when(mediaHashRepository.findExactMatchesOrderedByEarliest("unique_sha", currentMediaId))
                .thenReturn(Collections.emptyList());
        when(mediaHashRepository.findPerceptualCandidatesBounded(eq(currentMediaId), any(Pageable.class)))
                .thenReturn(Collections.emptyList());

        DuplicateDetectionService.DuplicateResult result = duplicateDetectionService.detectDuplicate(
                currentMedia, "unique_sha", "1234567890abcdef", null
        );

        assertThat(result.isDuplicate()).isFalse();
        assertThat(result.matchType()).isEqualTo(MatchType.NONE);
        assertThat(result.similarityScore()).isEqualTo(0.0);
        assertThat(result.duplicateOf()).isNull();
    }
}
