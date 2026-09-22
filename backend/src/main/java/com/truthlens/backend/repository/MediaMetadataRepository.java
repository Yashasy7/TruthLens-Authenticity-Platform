package com.truthlens.backend.repository;

import com.truthlens.backend.entity.MediaMetadata;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link MediaMetadata} entities.
 */
@Repository
public interface MediaMetadataRepository extends JpaRepository<MediaMetadata, UUID> {

    /**
     * Finds the metadata record for a given media ID.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the metadata if present
     */
    Optional<MediaMetadata> findByMediaId(UUID mediaId);

    /**
     * Finds the metadata record along with eagerly fetched Media association.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the metadata if present
     */
    @Query("SELECT m FROM MediaMetadata m JOIN FETCH m.media WHERE m.media.id = :mediaId")
    Optional<MediaMetadata> findByMediaIdWithMedia(@Param("mediaId") UUID mediaId);

    /**
     * Checks if a metadata record exists for the given media ID.
     *
     * @param mediaId the media entity identifier
     * @return true if metadata exists
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Retrieves all metadata records that contain forensic anomalies, ordered by forensic score descending.
     *
     * @param pageable pagination specification
     * @return list of anomalous metadata records
     */
    @Query("SELECT m FROM MediaMetadata m JOIN FETCH m.media WHERE m.hasAnomalies = true ORDER BY m.forensicScore DESC")
    List<MediaMetadata> findAnomalousWithMedia(Pageable pageable);
}
