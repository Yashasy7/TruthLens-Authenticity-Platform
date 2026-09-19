package com.truthlens.backend.service;

import com.truthlens.backend.dto.MediaResponse;
import com.truthlens.backend.dto.MediaUploadResponse;
import com.truthlens.backend.entity.AccountStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AccountSuspendedException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.StorageException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.hash.ChecksumService;
import com.truthlens.backend.service.storage.StorageKeyGenerator;
import com.truthlens.backend.service.storage.StorageService;
import com.truthlens.backend.service.validation.MediaValidationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.UUID;

/**
 * Service orchestrating secure multimedia upload, validation, hashing,
 * quarantined storage, and persistence for Module 02.
 */
@Service
public class MediaService {

    private static final Logger log = LoggerFactory.getLogger(MediaService.class);

    private final MediaRepository mediaRepository;
    private final UserRepository userRepository;
    private final MediaValidationService validationService;
    private final ChecksumService checksumService;
    private final StorageService storageService;
    private final StorageKeyGenerator storageKeyGenerator;

    public MediaService(MediaRepository mediaRepository,
                        UserRepository userRepository,
                        MediaValidationService validationService,
                        ChecksumService checksumService,
                        StorageService storageService,
                        StorageKeyGenerator storageKeyGenerator) {
        this.mediaRepository = mediaRepository;
        this.userRepository = userRepository;
        this.validationService = validationService;
        this.checksumService = checksumService;
        this.storageService = storageService;
        this.storageKeyGenerator = storageKeyGenerator;
    }

    /**
     * Ingests an authenticated multimedia upload into quarantined storage and persists metadata.
     *
     * <p>Workflow:</p>
     * <ol>
     *   <li>Verify authenticated uploader identity and active status.</li>
     *   <li>Validate file presence, size, and magic-byte MIME type using Apache Tika.</li>
     *   <li>Calculate cryptographic SHA-256 hash from stream.</li>
     *   <li>Generate secure, isolated storage key.</li>
     *   <li>Store file into quarantined storage.</li>
     *   <li>Persist metadata in PostgreSQL. Compensating cleanup removes file if persistence fails.</li>
     * </ol>
     *
     * @param file      the uploaded multipart file
     * @param userEmail normalized email address of the authenticated uploader
     * @return safe {@link MediaUploadResponse} with verified metadata
     */
    public MediaUploadResponse uploadMedia(MultipartFile file, String userEmail) {
        // 1. Uploader lookup
        User uploader = userRepository.findByEmail(userEmail)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + userEmail));

        if (uploader.getStatus() == AccountStatus.SUSPENDED) {
            throw new AccountSuspendedException();
        }

        // 2. Validate file presence, limits, and real MIME type via Apache Tika
        MediaValidationService.ValidationResult validation = validationService.validate(file);

        // 3. Compute SHA-256 hash from actual content
        String sha256Hash;
        try (InputStream is = file.getInputStream()) {
            sha256Hash = checksumService.calculateSha256(is);
        } catch (IOException e) {
            throw new InvalidMediaException("Failed to read upload stream for cryptographic hashing", e);
        }

        // 4. Generate isolated, server-controlled storage key
        String storageKey = storageKeyGenerator.generateKey(
                validation.mediaType(),
                validation.mimeType()
        );

        // 5. Store file into quarantined storage
        try (InputStream is = file.getInputStream()) {
            storageService.store(is, storageKey, validation.mimeType(), validation.fileSize());
        } catch (IOException e) {
            throw new StorageException("Failed to read file stream while writing to quarantine", e);
        }

        // 6. Persist metadata to database with compensating rollback on failure
        Media savedMedia;
        try {
            Media media = new Media(
                    uploader,
                    validation.sanitizedFilename(),
                    storageKey,
                    validation.mediaType(),
                    validation.mimeType(),
                    validation.fileSize(),
                    sha256Hash,
                    UploadStatus.UPLOADED
            );

            savedMedia = mediaRepository.saveAndFlush(media);
            log.info("Ingested media: id={}, type={}, size={}, sha256={}, uploader={}",
                    savedMedia.getId(), savedMedia.getMediaType(), savedMedia.getFileSize(),
                    savedMedia.getSha256Hash(), uploader.getId());
        } catch (Exception e) {
            log.error("Database persistence failed for media at '{}'; executing compensating storage deletion",
                    storageKey, e);
            try {
                storageService.delete(storageKey);
            } catch (Exception deleteEx) {
                log.error("Compensating storage deletion failed for key '{}'", storageKey, deleteEx);
            }
            throw new StorageException("Failed to register media in database; quarantined file cleaned up", e);
        }

        return toUploadResponse("Media uploaded and quarantined successfully", savedMedia);
    }

    /**
     * Retrieves media metadata by UUID with implicit authorization from SecurityContext.
     *
     * @param mediaId the media's unique identifier
     * @return safe {@link MediaResponse}
     */
    @Transactional(readOnly = true)
    public MediaResponse getMediaById(UUID mediaId) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) {
            throw new AccessDeniedException("Access denied. Authentication required to access media.");
        }
        return getMediaById(mediaId, auth.getName());
    }

    /**
     * Retrieves media metadata by UUID with explicit authorization check against the caller.
     *
     * <p>Enforces object-level access control (IDOR defense):</p>
     * <ul>
     *   <li>Standard {@code ROLE_USER} may only access their own uploaded media.</li>
     *   <li>Elevated roles ({@code ROLE_ANALYST}, {@code ROLE_MODERATOR}, {@code ROLE_ADMIN})
     *       may access any media for forensic analysis and moderation.</li>
     * </ul>
     *
     * @param mediaId          the media's unique identifier
     * @param currentUserEmail normalized email of the caller
     * @return safe {@link MediaResponse}
     */
    @Transactional(readOnly = true)
    public MediaResponse getMediaById(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Access denied. Authentication required to access media.");
        }

        Media media = mediaRepository.findById(mediaId)
                .orElseThrow(() -> new MediaNotFoundException("Media not found with id: " + mediaId));

        User currentUser = userRepository.findByEmail(currentUserEmail)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + currentUserEmail));

        boolean isOwner = media.getUploader().getId().equals(currentUser.getId());
        boolean isElevated = currentUser.getRoles().stream()
                .anyMatch(r -> r.getName() == RoleName.ANALYST ||
                               r.getName() == RoleName.MODERATOR ||
                               r.getName() == RoleName.ADMIN);

        if (!isOwner && !isElevated) {
            log.warn("IDOR attempt blocked: User '{}' (id={}) attempted to access media '{}' owned by '{}'",
                    currentUserEmail, currentUser.getId(), mediaId, media.getUploader().getId());
            throw new AccessDeniedException("Access denied. You do not have permission to access this media.");
        }

        return toMediaResponse(media);
    }

    /**
     * Retrieves all media records uploaded by a given user.
     *
     * @param userEmail normalized user email
     * @return list of {@link MediaResponse}
     */
    @Transactional(readOnly = true)
    public List<MediaResponse> getMediaForUser(String userEmail) {
        User user = userRepository.findByEmail(userEmail)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + userEmail));

        return mediaRepository.findByUploaderIdOrderByCreatedAtDesc(user.getId())
                .stream()
                .map(this::toMediaResponse)
                .toList();
    }

    /**
     * Maps a {@link Media} entity to a {@link MediaUploadResponse}.
     */
    private MediaUploadResponse toUploadResponse(String message, Media media) {
        return new MediaUploadResponse(
                message,
                media.getId(),
                media.getUploader().getId(),
                media.getOriginalFilename(),
                media.getStoragePath(),
                media.getMediaType().name(),
                media.getMimeType(),
                media.getFileSize(),
                media.getSha256Hash(),
                media.getUploadStatus().name(),
                media.getCreatedAt()
        );
    }

    /**
     * Maps a {@link Media} entity to a {@link MediaResponse}.
     */
    private MediaResponse toMediaResponse(Media media) {
        return new MediaResponse(
                media.getId(),
                media.getUploader().getId(),
                media.getOriginalFilename(),
                media.getStoragePath(),
                media.getMediaType().name(),
                media.getMimeType(),
                media.getFileSize(),
                media.getSha256Hash(),
                media.getUploadStatus().name(),
                media.getCreatedAt(),
                media.getUpdatedAt()
        );
    }
}
