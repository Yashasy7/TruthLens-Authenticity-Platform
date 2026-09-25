package com.truthlens.backend.repository;

import com.truthlens.backend.entity.OcrResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link OcrResult} persistence and lookups.
 */
@Repository
public interface OcrResultRepository extends JpaRepository<OcrResult, UUID> {

    /**
     * Finds OCR analysis findings by the target media ID.
     *
     * @param mediaId UUID of the media asset
     * @return Optional containing {@link OcrResult} if present
     */
    Optional<OcrResult> findByMediaId(UUID mediaId);

    /**
     * Checks if an OCR analysis record exists for the given media ID.
     *
     * @param mediaId UUID of the media asset
     * @return true if record exists, false otherwise
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Deletes OCR analysis record for the specified media asset.
     *
     * @param mediaId UUID of the media asset
     */
    void deleteByMediaId(UUID mediaId);
}
