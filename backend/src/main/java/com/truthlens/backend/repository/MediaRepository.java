package com.truthlens.backend.repository;

import com.truthlens.backend.entity.Media;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link Media} entities.
 */
@Repository
public interface MediaRepository extends JpaRepository<Media, UUID> {

    /**
     * Finds all media uploaded by a specific user.
     *
     * @param userId the user's UUID
     * @return list of media records
     */
    List<Media> findByUploaderIdOrderByCreatedAtDesc(UUID userId);

    /**
     * Finds paged media uploaded by a specific user.
     *
     * @param userId   the user's UUID
     * @param pageable pagination parameters
     * @return page of media records
     */
    Page<Media> findByUploaderId(UUID userId, Pageable pageable);

    /**
     * Finds a media record by its SHA-256 hash.
     * Supports future duplicate detection (Module 03).
     *
     * @param sha256Hash 64-character lowercase hexadecimal hash
     * @return optional matching media record
     */
    Optional<Media> findFirstBySha256Hash(String sha256Hash);

    /**
     * Checks whether media with the given SHA-256 hash has already been ingested.
     *
     * @param sha256Hash 64-character lowercase hexadecimal hash
     * @return true if media with this hash exists
     */
    boolean existsBySha256Hash(String sha256Hash);
}
