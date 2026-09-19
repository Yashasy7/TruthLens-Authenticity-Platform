package com.truthlens.backend.service;

import com.truthlens.backend.dto.MediaResponse;
import com.truthlens.backend.dto.MediaUploadResponse;
import com.truthlens.backend.entity.AccountStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AccountSuspendedException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.hash.ChecksumService;
import com.truthlens.backend.service.storage.StorageKeyGenerator;
import com.truthlens.backend.service.storage.StorageService;
import com.truthlens.backend.service.validation.MediaValidationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.access.AccessDeniedException;

import java.io.InputStream;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("MediaService — Unit Tests")
class MediaServiceTest {

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private MediaValidationService validationService;

    @Mock
    private ChecksumService checksumService;

    @Mock
    private StorageService storageService;

    @Mock
    private StorageKeyGenerator storageKeyGenerator;

    private MediaService mediaService;

    private User activeUser;
    private final String userEmail = "analyst@truthlens.org";
    private final UUID userId = UUID.randomUUID();

    @BeforeEach
    void setUp() throws Exception {
        mediaService = new MediaService(
                mediaRepository,
                userRepository,
                validationService,
                checksumService,
                storageService,
                storageKeyGenerator
        );

        activeUser = new User(userEmail, "hash", "Analyst One");
        activeUser.setStatus(AccountStatus.ACTIVE);
        setPrivateField(activeUser, "id", userId);
    }

    private void setPrivateField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    @DisplayName("Successfully ingests valid media into quarantine and saves metadata")
    void uploadMedia_validInput_success() throws Exception {
        byte[] content = "valid image content".getBytes();
        MockMultipartFile file = new MockMultipartFile("file", "evidence.jpg", "image/jpeg", content);

        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.of(activeUser));
        when(validationService.validate(file)).thenReturn(
                new MediaValidationService.ValidationResult(MediaType.IMAGE, "image/jpeg", "evidence.jpg", content.length)
        );
        when(checksumService.calculateSha256(any(InputStream.class))).thenReturn("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        when(storageKeyGenerator.generateKey(MediaType.IMAGE, "image/jpeg")).thenReturn("quarantine/image/20260919/uuid.jpg");
        when(storageService.store(any(InputStream.class), eq("quarantine/image/20260919/uuid.jpg"), eq("image/jpeg"), eq((long) content.length)))
                .thenReturn("quarantine/image/20260919/uuid.jpg");

        Media savedEntity = new Media(
                activeUser,
                "evidence.jpg",
                "quarantine/image/20260919/uuid.jpg",
                MediaType.IMAGE,
                "image/jpeg",
                content.length,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                UploadStatus.UPLOADED
        );
        UUID mediaId = UUID.randomUUID();
        setPrivateField(savedEntity, "id", mediaId);
        setPrivateField(savedEntity, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaRepository.saveAndFlush(any(Media.class))).thenReturn(savedEntity);

        MediaUploadResponse response = mediaService.uploadMedia(file, userEmail);

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(mediaId);
        assertThat(response.getUploaderId()).isEqualTo(userId);
        assertThat(response.getOriginalFilename()).isEqualTo("evidence.jpg");
        assertThat(response.getMediaType()).isEqualTo("IMAGE");
        assertThat(response.getMimeType()).isEqualTo("image/jpeg");
        assertThat(response.getSha256Hash()).isEqualTo("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        assertThat(response.getUploadStatus()).isEqualTo("UPLOADED");

        verify(storageService).store(any(InputStream.class), eq("quarantine/image/20260919/uuid.jpg"), eq("image/jpeg"), eq((long) content.length));
        verify(mediaRepository).saveAndFlush(any(Media.class));
    }

    @Test
    @DisplayName("Throws UserNotFoundException when uploader does not exist")
    void uploadMedia_userNotFound_throwsException() {
        MockMultipartFile file = new MockMultipartFile("file", "test.png", "image/png", new byte[10]);
        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> mediaService.uploadMedia(file, userEmail))
                .isInstanceOf(UserNotFoundException.class)
                .hasMessageContaining("User not found");

        verify(storageService, never()).store(any(), any(), any(), anyLong());
        verify(mediaRepository, never()).saveAndFlush(any());
    }

    @Test
    @DisplayName("Throws AccountSuspendedException when uploader account is suspended")
    void uploadMedia_suspendedUser_throwsException() {
        activeUser.setStatus(AccountStatus.SUSPENDED);
        MockMultipartFile file = new MockMultipartFile("file", "test.png", "image/png", new byte[10]);
        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.of(activeUser));

        assertThatThrownBy(() -> mediaService.uploadMedia(file, userEmail))
                .isInstanceOf(AccountSuspendedException.class);

        verify(storageService, never()).store(any(), any(), any(), anyLong());
    }

    @Test
    @DisplayName("Performs compensating cleanup of quarantined storage if database persistence fails")
    void uploadMedia_dbFailure_deletesStoredQuarantinedFile() {
        byte[] content = "payload".getBytes();
        MockMultipartFile file = new MockMultipartFile("file", "evidence.jpg", "image/jpeg", content);

        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.of(activeUser));
        when(validationService.validate(file)).thenReturn(
                new MediaValidationService.ValidationResult(MediaType.IMAGE, "image/jpeg", "evidence.jpg", content.length)
        );
        when(checksumService.calculateSha256(any(InputStream.class))).thenReturn("hash123");
        when(storageKeyGenerator.generateKey(any(), any())).thenReturn("quarantine/image/uuid.jpg");

        // Storage succeeds
        when(storageService.store(any(), eq("quarantine/image/uuid.jpg"), any(), anyLong()))
                .thenReturn("quarantine/image/uuid.jpg");

        // DB saveAndFlush fails
        when(mediaRepository.saveAndFlush(any(Media.class))).thenThrow(new RuntimeException("DB connection timeout"));

        assertThatThrownBy(() -> mediaService.uploadMedia(file, userEmail))
                .isInstanceOf(StorageException.class)
                .hasMessageContaining("Failed to register media in database; quarantined file cleaned up");

        // Verify compensating cleanup was triggered!
        verify(storageService).delete("quarantine/image/uuid.jpg");
    }

    @Test
    @DisplayName("Retrieves media metadata by ID when accessed by the owner")
    void getMediaById_ownerAccess_returnsResponse() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "file.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);
        setPrivateField(media, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));
        setPrivateField(media, "updatedAt", OffsetDateTime.now(ZoneOffset.UTC));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.of(activeUser));

        MediaResponse response = mediaService.getMediaById(mediaId, userEmail);

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(mediaId);
        assertThat(response.getOriginalFilename()).isEqualTo("file.png");
    }

    @Test
    @DisplayName("Blocks IDOR: Non-owner with ROLE_USER cannot access other user's media")
    void getMediaById_otherUserRoleUser_throwsAccessDeniedException() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "secret.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);

        User attacker = new User("victim_stalker@truthlens.org", "hash", "Attacker");
        setPrivateField(attacker, "id", UUID.randomUUID());
        attacker.getRoles().add(new Role(RoleName.USER, "Standard user"));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("victim_stalker@truthlens.org")).thenReturn(Optional.of(attacker));

        assertThatThrownBy(() -> mediaService.getMediaById(mediaId, "victim_stalker@truthlens.org"))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission to access this media");
    }

    @Test
    @DisplayName("Allows elevated ROLE_ANALYST to access any user's media for forensic analysis")
    void getMediaById_analystRole_canAccessOtherUserMedia() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "investigate.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);
        setPrivateField(media, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));
        setPrivateField(media, "updatedAt", OffsetDateTime.now(ZoneOffset.UTC));

        User analyst = new User("forensic@truthlens.org", "hash", "Forensic Analyst");
        setPrivateField(analyst, "id", UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Analyst"));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("forensic@truthlens.org")).thenReturn(Optional.of(analyst));

        MediaResponse response = mediaService.getMediaById(mediaId, "forensic@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(mediaId);
    }

    @Test
    @DisplayName("Allows elevated ROLE_MODERATOR to access any user's media for moderation review")
    void getMediaById_moderatorRole_canAccessOtherUserMedia() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "flagged.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);
        setPrivateField(media, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));
        setPrivateField(media, "updatedAt", OffsetDateTime.now(ZoneOffset.UTC));

        User moderator = new User("moderator@truthlens.org", "hash", "Moderator");
        setPrivateField(moderator, "id", UUID.randomUUID());
        moderator.getRoles().add(new Role(RoleName.MODERATOR, "Moderator"));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("moderator@truthlens.org")).thenReturn(Optional.of(moderator));

        MediaResponse response = mediaService.getMediaById(mediaId, "moderator@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(mediaId);
    }

    @Test
    @DisplayName("Allows elevated ROLE_ADMIN to access any user's media for administrative audits")
    void getMediaById_adminRole_canAccessOtherUserMedia() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "audit.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);
        setPrivateField(media, "createdAt", OffsetDateTime.now(ZoneOffset.UTC));
        setPrivateField(media, "updatedAt", OffsetDateTime.now(ZoneOffset.UTC));

        User admin = new User("admin@truthlens.org", "hash", "Admin");
        setPrivateField(admin, "id", UUID.randomUUID());
        admin.getRoles().add(new Role(RoleName.ADMIN, "Admin"));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("admin@truthlens.org")).thenReturn(Optional.of(admin));

        MediaResponse response = mediaService.getMediaById(mediaId, "admin@truthlens.org");

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(mediaId);
    }

    @Test
    @DisplayName("Blocks ROLE_RESEARCHER from accessing another user's non-dataset uploaded media")
    void getMediaById_researcherRole_cannotAccessOtherUserMedia() throws Exception {
        UUID mediaId = UUID.randomUUID();
        Media media = new Media(
                activeUser, "private.png", "quarantine/path.png",
                MediaType.IMAGE, "image/png", 1024, "hash", UploadStatus.UPLOADED
        );
        setPrivateField(media, "id", mediaId);

        User researcher = new User("researcher@truthlens.org", "hash", "Researcher");
        setPrivateField(researcher, "id", UUID.randomUUID());
        researcher.getRoles().add(new Role(RoleName.RESEARCHER, "Researcher"));

        when(mediaRepository.findById(mediaId)).thenReturn(Optional.of(media));
        when(userRepository.findByEmail("researcher@truthlens.org")).thenReturn(Optional.of(researcher));

        assertThatThrownBy(() -> mediaService.getMediaById(mediaId, "researcher@truthlens.org"))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission to access this media");
    }

    @Test
    @DisplayName("Throws MediaNotFoundException when media ID does not exist")
    void getMediaById_notFound_throwsException() {
        UUID randomId = UUID.randomUUID();
        when(mediaRepository.findById(randomId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> mediaService.getMediaById(randomId, userEmail))
                .isInstanceOf(MediaNotFoundException.class)
                .hasMessageContaining("Media not found");
    }

    @Test
    @DisplayName("Retrieves all media uploaded by a specific user")
    void getMediaForUser_returnsUserMediaList() throws Exception {
        Media media1 = new Media(activeUser, "a.jpg", "path1", MediaType.IMAGE, "image/jpeg", 500, "h1", UploadStatus.UPLOADED);
        Media media2 = new Media(activeUser, "b.mp4", "path2", MediaType.VIDEO, "video/mp4", 5000, "h2", UploadStatus.UPLOADED);
        setPrivateField(media1, "id", UUID.randomUUID());
        setPrivateField(media2, "id", UUID.randomUUID());

        when(userRepository.findByEmail(userEmail)).thenReturn(Optional.of(activeUser));
        when(mediaRepository.findByUploaderIdOrderByCreatedAtDesc(userId)).thenReturn(List.of(media1, media2));

        List<MediaResponse> results = mediaService.getMediaForUser(userEmail);

        assertThat(results).hasSize(2);
        assertThat(results.get(0).getOriginalFilename()).isEqualTo("a.jpg");
        assertThat(results.get(1).getOriginalFilename()).isEqualTo("b.mp4");
    }
}
