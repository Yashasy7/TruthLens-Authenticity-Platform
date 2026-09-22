package com.truthlens.backend.service.fingerprint;

import com.truthlens.backend.dto.DuplicateDetailResponse;
import com.truthlens.backend.dto.MediaHashResponse;
import com.truthlens.backend.entity.MatchType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaHash;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.MediaHashRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.util.Optional;
import java.util.UUID;

/**
 * Service orchestrating multimedia fingerprint generation, persistence, and duplicate queries.
 */
@Service
public class MediaFingerprintService {

    private static final Logger log = LoggerFactory.getLogger(MediaFingerprintService.class);

    private final MediaRepository mediaRepository;
    private final MediaHashRepository mediaHashRepository;
    private final UserRepository userRepository;
    private final StorageService storageService;
    private final PerceptualHashService perceptualHashService;
    private final AcousticFingerprintService acousticFingerprintService;
    private final DuplicateDetectionService duplicateDetectionService;

    public MediaFingerprintService(
            MediaRepository mediaRepository,
            MediaHashRepository mediaHashRepository,
            UserRepository userRepository,
            StorageService storageService,
            PerceptualHashService perceptualHashService,
            AcousticFingerprintService acousticFingerprintService,
            DuplicateDetectionService duplicateDetectionService) {
        this.mediaRepository = mediaRepository;
        this.mediaHashRepository = mediaHashRepository;
        this.userRepository = userRepository;
        this.storageService = storageService;
        this.perceptualHashService = perceptualHashService;
        this.acousticFingerprintService = acousticFingerprintService;
        this.duplicateDetectionService = duplicateDetectionService;
    }

    /**
     * Generates all applicable fingerprints for an ingested media item,
     * performs duplicate detection, and persists the {@link MediaHash} record.
     * Idempotent and thread-safe against concurrent generation races (S-03).
     *
     * @param media the ingested media entity
     * @return {@link MediaHashResponse} containing generated fingerprints and match status
     */
    @Transactional
    public MediaHashResponse generateAndSaveFingerprint(Media media) {
        if (media == null) {
            throw new IllegalArgumentException("Media entity must not be null");
        }

        // Check if fingerprint already exists
        Optional<MediaHash> existing = mediaHashRepository.findByMediaId(media.getId());
        if (existing.isPresent()) {
            return toResponse(existing.get(), null);
        }

        String sha256Hash = media.getSha256Hash();
        String phash = null;
        String phashVector = null;
        String chromaprint = null;

        // Generate perceptual or acoustic fingerprints based on media category
        if (media.getMediaType() == MediaType.IMAGE) {
            try (InputStream is = storageService.load(media.getStoragePath())) {
                phash = perceptualHashService.generateDHash(is);
                phashVector = perceptualHashService.toVectorRepresentation(phash);
            } catch (Exception e) {
                log.warn("Failed to generate perceptual hash for media '{}': {}", media.getId(), e.getMessage());
            }
        } else if (media.getMediaType() == MediaType.AUDIO) {
            try (InputStream is = storageService.load(media.getStoragePath())) {
                chromaprint = acousticFingerprintService.generateAcousticFingerprint(is);
            } catch (Exception e) {
                log.warn("Failed to generate acoustic fingerprint for media '{}': {}", media.getId(), e.getMessage());
            }
        }

        // Detect duplicates against historical fingerprints
        DuplicateDetectionService.DuplicateResult duplicateResult =
                duplicateDetectionService.detectDuplicate(media, sha256Hash, phash, chromaprint);

        MediaHash mediaHash = new MediaHash(media, sha256Hash, phash, phashVector, chromaprint, null);
        if (duplicateResult.isDuplicate()) {
            mediaHash.setDuplicateMatch(
                    duplicateResult.duplicateOf(),
                    duplicateResult.matchType(),
                    duplicateResult.similarityScore()
            );
        }

        MediaHash saved;
        try {
            saved = mediaHashRepository.saveAndFlush(mediaHash);
        } catch (DataIntegrityViolationException dive) {
            // Concurrent fingerprint generation race condition handled safely (S-03)
            log.warn("Concurrent fingerprint persistence race for media '{}'; returning existing record", media.getId());
            saved = mediaHashRepository.findByMediaId(media.getId()).orElseThrow(() -> dive);
        }

        log.info("Persisted fingerprint for media '{}': isDuplicate={}, matchType={}, similarity={}",
                media.getId(), saved.isDuplicate(), saved.getMatchType(), saved.getSimilarityScore());

        return toResponse(saved, null);
    }

    /**
     * Explicitly generates or re-evaluates fingerprints and duplicate status for a media file (F-03).
     * Re-runs duplicate detection against the current catalog and updates the duplicate status.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return refreshed {@link MediaHashResponse}
     */
    @Transactional
    public MediaHashResponse generateOrReevaluateFingerprint(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        Optional<MediaHash> existingOpt = mediaHashRepository.findByMediaId(mediaId);
        if (existingOpt.isEmpty()) {
            MediaHashResponse response = generateAndSaveFingerprint(media);
            MediaHash saved = mediaHashRepository.findByMediaId(mediaId).orElseThrow();
            return toResponse(saved, currentUserEmail);
        }

        MediaHash mediaHash = existingOpt.get();

        // Ensure perceptual / acoustic hashes are present if missing
        if (media.getMediaType() == MediaType.IMAGE && (mediaHash.getPhash() == null || mediaHash.getPhash().isBlank())) {
            try (InputStream is = storageService.load(media.getStoragePath())) {
                String phash = perceptualHashService.generateDHash(is);
                mediaHash.setPhash(phash);
                mediaHash.setPhashVector(perceptualHashService.toVectorRepresentation(phash));
            } catch (Exception e) {
                log.warn("Failed to generate missing perceptual hash for media '{}': {}", mediaId, e.getMessage());
            }
        } else if (media.getMediaType() == MediaType.AUDIO && (mediaHash.getChromaprint() == null || mediaHash.getChromaprint().isBlank())) {
            try (InputStream is = storageService.load(media.getStoragePath())) {
                String chromaprint = acousticFingerprintService.generateAcousticFingerprint(is);
                mediaHash.setChromaprint(chromaprint);
            } catch (Exception e) {
                log.warn("Failed to generate missing acoustic fingerprint for media '{}': {}", mediaId, e.getMessage());
            }
        }

        // Re-evaluate duplicate detection against the current catalog
        DuplicateDetectionService.DuplicateResult duplicateResult = duplicateDetectionService.detectDuplicate(
                media, mediaHash.getSha256Hash(), mediaHash.getPhash(), mediaHash.getChromaprint()
        );

        if (duplicateResult.isDuplicate()) {
            mediaHash.setDuplicateMatch(
                    duplicateResult.duplicateOf(),
                    duplicateResult.matchType(),
                    duplicateResult.similarityScore()
            );
        } else {
            mediaHash.setDuplicate(false);
            mediaHash.setDuplicateOf(null);
            mediaHash.setMatchType(MatchType.NONE);
            mediaHash.setSimilarityScore(0.0);
        }

        MediaHash updated = mediaHashRepository.saveAndFlush(mediaHash);
        log.info("Re-evaluated fingerprint for media '{}': isDuplicate={}, matchType={}, similarity={}",
                mediaId, updated.isDuplicate(), updated.getMatchType(), updated.getSimilarityScore());

        return toResponse(updated, currentUserEmail);
    }

    /**
     * Retrieves the fingerprint record for a media item with object-level authorization.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return safe {@link MediaHashResponse}
     */
    @Transactional
    public MediaHashResponse getFingerprint(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaHash mediaHash = mediaHashRepository.findByMediaId(mediaId)
                .orElseGet(() -> {
                    // Lazy generation if not present
                    generateAndSaveFingerprint(media);
                    return mediaHashRepository.findByMediaId(mediaId).orElseThrow();
                });

        return toResponse(mediaHash, currentUserEmail);
    }

    /**
     * Retrieves duplicate detection analysis for a media item with privacy preservation (S-02) and IDOR protection.
     *
     * @param mediaId          the media identifier
     * @param currentUserEmail email of the caller
     * @return safe {@link DuplicateDetailResponse}
     */
    @Transactional
    public DuplicateDetailResponse getDuplicateDetails(UUID mediaId, String currentUserEmail) {
        Media media = authorizeAndGetMedia(mediaId, currentUserEmail);

        MediaHash mediaHash = mediaHashRepository.findByMediaId(mediaId)
                .orElseGet(() -> {
                    generateAndSaveFingerprint(media);
                    return mediaHashRepository.findByMediaId(mediaId).orElseThrow();
                });

        UUID duplicateOfId = null;
        String duplicateOfFilename = null;

        if (mediaHash.isDuplicate() && mediaHash.getDuplicateOf() != null) {
            User currentUser = userRepository.findByEmail(currentUserEmail)
                    .orElseThrow(() -> new UserNotFoundException("User not found: " + currentUserEmail));

            boolean isElevated = currentUser.getRoles().stream()
                    .anyMatch(r -> r.getName() == RoleName.ANALYST ||
                                   r.getName() == RoleName.MODERATOR ||
                                   r.getName() == RoleName.ADMIN);

            boolean isOwnDuplicate = mediaHash.getDuplicateOf().getUploader().getId().equals(currentUser.getId());

            // Protect cross-user privacy (S-02):
            // Only reveal duplicate media UUID and original filename if caller is elevated or owns both files
            if (isElevated || isOwnDuplicate) {
                duplicateOfId = mediaHash.getDuplicateOf().getId();
                duplicateOfFilename = mediaHash.getDuplicateOf().getOriginalFilename();
            } else {
                duplicateOfId = null;
                duplicateOfFilename = "Verified Reference Item";
            }
        }

        return new DuplicateDetailResponse(
                mediaId,
                mediaHash.isDuplicate(),
                mediaHash.getMatchType().name(),
                mediaHash.getSimilarityScore(),
                duplicateOfId,
                duplicateOfFilename,
                mediaHash.getCreatedAt()
        );
    }

    /**
     * Authorizes the caller against the target media item (IDOR protection).
     * Standard users and researchers may access their own uploads; elevated roles may access any media.
     */
    private Media authorizeAndGetMedia(UUID mediaId, String currentUserEmail) {
        if (currentUserEmail == null || currentUserEmail.isBlank()) {
            throw new AccessDeniedException("Authentication required to access media fingerprints");
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
            log.warn("IDOR attempt blocked on fingerprint query: User '{}' attempted to access media '{}'",
                    currentUserEmail, mediaId);
            throw new AccessDeniedException("Access denied. You do not have permission to access this media's fingerprint.");
        }

        return media;
    }

    private MediaHashResponse toResponse(MediaHash hash, String currentUserEmail) {
        UUID duplicateOfId = null;

        if (hash.isDuplicate() && hash.getDuplicateOf() != null) {
            if (currentUserEmail != null && !currentUserEmail.isBlank()) {
                Optional<User> userOpt = userRepository.findByEmail(currentUserEmail);
                if (userOpt.isPresent()) {
                    User user = userOpt.get();
                    boolean isElevated = user.getRoles().stream()
                            .anyMatch(r -> r.getName() == RoleName.ANALYST ||
                                           r.getName() == RoleName.MODERATOR ||
                                           r.getName() == RoleName.ADMIN);
                    boolean isOwnDuplicate = hash.getDuplicateOf().getUploader().getId().equals(user.getId());

                    // S-02: Mask internal UUID for cross-user regular users
                    if (isElevated || isOwnDuplicate) {
                        duplicateOfId = hash.getDuplicateOf().getId();
                    }
                } else {
                    duplicateOfId = hash.getDuplicateOf().getId();
                }
            } else {
                duplicateOfId = hash.getDuplicateOf().getId();
            }
        }

        return new MediaHashResponse(
                hash.getId(),
                hash.getMedia().getId(),
                hash.getSha256Hash(),
                hash.getPhash(),
                hash.getChromaprint(),
                hash.isDuplicate(),
                duplicateOfId,
                hash.getSimilarityScore(),
                hash.getMatchType().name(),
                hash.getCreatedAt()
        );
    }
}
