package com.truthlens.backend.service.fingerprint;

import com.truthlens.backend.dto.DuplicateDetailResponse;
import com.truthlens.backend.dto.MediaHashResponse;
import com.truthlens.backend.entity.MatchType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaHash;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.MediaHashRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("MediaFingerprintService — Unit & Remediation Tests (S-01, S-02, S-03, F-03)")
class MediaFingerprintServiceTest {

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private MediaHashRepository mediaHashRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private PerceptualHashService perceptualHashService;

    @Mock
    private AcousticFingerprintService acousticFingerprintService;

    @Mock
    private DuplicateDetectionService duplicateDetectionService;

    private MediaFingerprintService mediaFingerprintService;

    private User owner;
    private User otherUser;
    private User analyst;
    private User researcher;
    private Media media;
    private UUID mediaId;
    private final String ownerEmail = "owner@truthlens.org";

    @BeforeEach
    void setUp() throws Exception {
        mediaFingerprintService = new MediaFingerprintService(
                mediaRepository,
                mediaHashRepository,
                userRepository,
                storageService,
                perceptualHashService,
                acousticFingerprintService,
                duplicateDetectionService
        );

        owner = new User(ownerEmail, "hash", "Owner User");
        setPrivateField(owner, "id", UUID.randomUUID());
        owner.getRoles().add(new Role(RoleName.USER, "Standard user"));

        otherUser = new User("intruder@truthlens.org", "hash", "Intruder User");
        setPrivateField(otherUser, "id", UUID.randomUUID());
        otherUser.getRoles().add(new Role(RoleName.USER, "Standard user"));

        analyst = new User("analyst@truthlens.org", "hash", "Analyst User");
        setPrivateField(analyst, "id", UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Analyst"));

        researcher = new User("researcher@truthlens.org", "hash", "Researcher User");
        setPrivateField(researcher, "id", UUID.randomUUID());
        researcher.getRoles().add(new Role(RoleName.RESEARCHER, "Researcher"));

        mediaId = UUID.randomUUID();
        media = new Media(owner, "photo.jpg", "quarantine/photo.jpg", MediaType.IMAGE, "image/jpeg", 500, "sha256_photo", UploadStatus.UPLOADED);
        setPrivateField(media, "id", mediaId);
    }

    private void setPrivateField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    @DisplayName("Generates and persists fingerprints for an image file")
    void generateAndSaveFingerprint_imageMedia_success() throws Exception {
        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.empty());
        when(storageService.load("quarantine/photo.jpg")).thenReturn(new ByteArrayInputStream(new byte[]{1, 2, 3}));
        when(perceptualHashService.generateDHash(any(InputStream.class))).thenReturn("1234567890abcdef");
        when(perceptualHashService.toVectorRepresentation("1234567890abcdef")).thenReturn("vector_string_sample");
        when(duplicateDetectionService.detectDuplicate(eq(media), eq("sha256_photo"), eq("1234567890abcdef"), any()))
                .thenReturn(DuplicateDetectionService.DuplicateResult.noMatch());

        MediaHash savedEntity = new MediaHash(media, "sha256_photo", "1234567890abcdef", null);
        setPrivateField(savedEntity, "id", UUID.randomUUID());
        setPrivateField(savedEntity, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.saveAndFlush(any(MediaHash.class))).thenReturn(savedEntity);

        MediaHashResponse response = mediaFingerprintService.generateAndSaveFingerprint(media);

        assertThat(response).isNotNull();
        assertThat(response.mediaId()).isEqualTo(mediaId);
        assertThat(response.sha256Hash()).isEqualTo("sha256_photo");
        assertThat(response.phash()).isEqualTo("1234567890abcdef");
        assertThat(response.isDuplicate()).isFalse();

        verify(mediaHashRepository).saveAndFlush(any(MediaHash.class));
    }

    @Test
    @DisplayName("Owner can retrieve fingerprint for own media")
    void getFingerprint_ownerAccess_success() throws Exception {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail(ownerEmail)).thenReturn(Optional.of(owner));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        MediaHashResponse response = mediaFingerprintService.getFingerprint(mediaId, ownerEmail);

        assertThat(response).isNotNull();
        assertThat(response.mediaId()).isEqualTo(mediaId);
        assertThat(response.sha256Hash()).isEqualTo("sha256_photo");
    }

    @Test
    @DisplayName("Blocks IDOR: Non-owner with ROLE_USER cannot retrieve media fingerprint")
    void getFingerprint_nonOwnerRoleUser_throwsAccessDeniedException() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("intruder@truthlens.org")).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> mediaFingerprintService.getFingerprint(mediaId, "intruder@truthlens.org"))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission to access this media's fingerprint");
    }

    @Test
    @DisplayName("S-01 Authorization: ROLE_RESEARCHER can access their own media fingerprint")
    void getFingerprint_researcherOwnMedia_success() throws Exception {
        Media researcherMedia = new Media(researcher, "dataset.png", "q/dataset.png", MediaType.IMAGE, "image/png", 200, "sha_res", UploadStatus.UPLOADED);
        UUID resMediaId = UUID.randomUUID();
        setPrivateField(researcherMedia, "id", resMediaId);

        when(mediaRepository.findById(resMediaId)).thenReturn(Optional.of(researcherMedia));
        when(userRepository.findByEmail("researcher@truthlens.org")).thenReturn(Optional.of(researcher));

        MediaHash existing = new MediaHash(researcherMedia, "sha_res", "phash_res", null);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(resMediaId)).thenReturn(Optional.of(existing));

        MediaHashResponse response = mediaFingerprintService.getFingerprint(resMediaId, "researcher@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.mediaId()).isEqualTo(resMediaId);
    }

    @Test
    @DisplayName("S-01 Authorization: ROLE_RESEARCHER blocked from accessing other users' media")
    void getFingerprint_researcherOtherUserMedia_throwsAccessDeniedException() {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("researcher@truthlens.org")).thenReturn(Optional.of(researcher));

        assertThatThrownBy(() -> mediaFingerprintService.getFingerprint(mediaId, "researcher@truthlens.org"))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission to access this media's fingerprint");
    }

    @Test
    @DisplayName("Allows elevated ROLE_ANALYST to retrieve media fingerprint for investigation")
    void getFingerprint_elevatedAnalyst_success() throws Exception {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("analyst@truthlens.org")).thenReturn(Optional.of(analyst));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        MediaHashResponse response = mediaFingerprintService.getFingerprint(mediaId, "analyst@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.mediaId()).isEqualTo(mediaId);
    }

    @Test
    @DisplayName("S-02 Privacy: Standard user gets duplicateOfMediaId = null when duplicating another user's media")
    void getDuplicateDetails_crossUserStandardUser_masksDuplicateOfMediaId() throws Exception {
        Media originalMedia = new Media(otherUser, "secret_source.jpg", "path", MediaType.IMAGE, "image/jpeg", 500, "hash", UploadStatus.UPLOADED);
        UUID origId = UUID.randomUUID();
        setPrivateField(originalMedia, "id", origId);

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail(ownerEmail)).thenReturn(Optional.of(owner));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        existing.setDuplicateMatch(originalMedia, MatchType.EXACT_SHA256, 1.0);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        DuplicateDetailResponse response = mediaFingerprintService.getDuplicateDetails(mediaId, ownerEmail);

        assertThat(response).isNotNull();
        assertThat(response.isDuplicate()).isTrue();
        assertThat(response.matchType()).isEqualTo("EXACT_SHA256");
        // S-02 Remediation: duplicateOfMediaId MUST be null for cross-user regular users!
        assertThat(response.duplicateOfMediaId()).isNull();
        assertThat(response.duplicateOfFilename()).isEqualTo("Verified Reference Item");
    }

    @Test
    @DisplayName("S-02 Privacy: Elevated analyst receives duplicateOfMediaId and original filename")
    void getDuplicateDetails_elevatedAnalyst_revealsDuplicateOfMediaIdAndFilename() throws Exception {
        Media originalMedia = new Media(otherUser, "evidence_original.jpg", "path", MediaType.IMAGE, "image/jpeg", 500, "hash", UploadStatus.UPLOADED);
        UUID origId = UUID.randomUUID();
        setPrivateField(originalMedia, "id", origId);

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("analyst@truthlens.org")).thenReturn(Optional.of(analyst));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        existing.setDuplicateMatch(originalMedia, MatchType.NEAR_MATCH_PHASH, 0.95);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        DuplicateDetailResponse response = mediaFingerprintService.getDuplicateDetails(mediaId, "analyst@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.isDuplicate()).isTrue();
        assertThat(response.duplicateOfMediaId()).isEqualTo(origId);
        assertThat(response.duplicateOfFilename()).isEqualTo("evidence_original.jpg");
    }

    @Test
    @DisplayName("S-02 Privacy: User querying media that duplicates their own upload retains duplicateOfMediaId")
    void getDuplicateDetails_sameUserDuplicate_retainsDuplicateOfMediaId() throws Exception {
        Media ownOriginalMedia = new Media(owner, "my_first_upload.jpg", "path", MediaType.IMAGE, "image/jpeg", 500, "hash", UploadStatus.UPLOADED);
        UUID ownOrigId = UUID.randomUUID();
        setPrivateField(ownOriginalMedia, "id", ownOrigId);

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail(ownerEmail)).thenReturn(Optional.of(owner));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        existing.setDuplicateMatch(ownOriginalMedia, MatchType.EXACT_SHA256, 1.0);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        DuplicateDetailResponse response = mediaFingerprintService.getDuplicateDetails(mediaId, ownerEmail);

        assertThat(response).isNotNull();
        assertThat(response.duplicateOfMediaId()).isEqualTo(ownOrigId);
        assertThat(response.duplicateOfFilename()).isEqualTo("my_first_upload.jpg");
    }

    @Test
    @DisplayName("F-03 Re-evaluation: POST generateOrReevaluateFingerprint re-runs duplicate detection against new catalog")
    void generateOrReevaluateFingerprint_existingRecord_reEvaluatesDuplicates() throws Exception {
        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail(ownerEmail)).thenReturn(Optional.of(owner));

        MediaHash existing = new MediaHash(media, "sha256_photo", "phash123", null);
        existing.setDuplicate(false);
        setPrivateField(existing, "id", UUID.randomUUID());
        setPrivateField(existing, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaHashRepository.findByMediaId(mediaId)).thenReturn(Optional.of(existing));

        Media newDuplicateCandidate = new Media(otherUser, "orig.jpg", "p", MediaType.IMAGE, "image/jpeg", 500, "sha256_photo", UploadStatus.UPLOADED);
        setPrivateField(newDuplicateCandidate, "id", UUID.randomUUID());

        // A new duplicate is now detected in the catalog
        when(duplicateDetectionService.detectDuplicate(eq(media), eq("sha256_photo"), eq("phash123"), any()))
                .thenReturn(new DuplicateDetectionService.DuplicateResult(true, newDuplicateCandidate, MatchType.EXACT_SHA256, 1.0));
        when(mediaHashRepository.saveAndFlush(existing)).thenReturn(existing);

        MediaHashResponse response = mediaFingerprintService.generateOrReevaluateFingerprint(mediaId, ownerEmail);

        assertThat(response).isNotNull();
        assertThat(existing.isDuplicate()).isTrue();
        assertThat(existing.getMatchType()).isEqualTo(MatchType.EXACT_SHA256);
        assertThat(existing.getSimilarityScore()).isEqualTo(1.0);
        verify(mediaHashRepository).saveAndFlush(existing);
    }

    @Test
    @DisplayName("S-03 Concurrency: Unique constraint violation race is handled safely without throwing 500")
    void generateAndSaveFingerprint_concurrencyRace_returnsExistingRecord() throws Exception {
        when(mediaHashRepository.findByMediaId(mediaId))
                .thenReturn(Optional.empty()) // first check: not found
                .thenReturn(Optional.of(new MediaHash(media, "sha256_photo", "phash", null))); // second check after race: found

        when(duplicateDetectionService.detectDuplicate(eq(media), any(), any(), any()))
                .thenReturn(DuplicateDetectionService.DuplicateResult.noMatch());

        when(mediaHashRepository.saveAndFlush(any(MediaHash.class)))
                .thenThrow(new DataIntegrityViolationException("duplicate key value violates unique constraint uq_media_hashes_media_id"));

        MediaHashResponse response = mediaFingerprintService.generateAndSaveFingerprint(media);

        assertThat(response).isNotNull();
        assertThat(response.mediaId()).isEqualTo(mediaId);
    }

    @Test
    @DisplayName("Throws MediaNotFoundException when media ID does not exist")
    void getFingerprint_mediaNotFound_throwsException() {
        UUID missingId = UUID.randomUUID();
        when(mediaRepository.findById(missingId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> mediaFingerprintService.getFingerprint(missingId, ownerEmail))
                .isInstanceOf(MediaNotFoundException.class)
                .hasMessageContaining("Media not found");
    }
}
