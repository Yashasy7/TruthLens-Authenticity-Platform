package com.truthlens.backend.repository;

import com.truthlens.backend.entity.ImageAnalysis;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link ImageAnalysis} entities.
 */
@Repository
public interface ImageAnalysisRepository extends JpaRepository<ImageAnalysis, UUID> {

    /**
     * Finds the image analysis record for a given media ID.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis if present
     */
    Optional<ImageAnalysis> findByMediaId(UUID mediaId);

    /**
     * Finds the image analysis record along with the eagerly fetched Media entity.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis with media if present
     */
    @Query("SELECT ia FROM ImageAnalysis ia JOIN FETCH ia.media WHERE ia.media.id = :mediaId")
    Optional<ImageAnalysis> findByMediaIdWithMedia(@Param("mediaId") UUID mediaId);

    /**
     * Checks if an image analysis record exists for the given media ID.
     *
     * @param mediaId the media entity identifier
     * @return true if analysis exists
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Retrieves all image analyses flagged as potentially manipulated, ordered by manipulation probability descending.
     *
     * @param pageable pagination specification
     * @return list of flagged image analyses
     */
    @Query("SELECT ia FROM ImageAnalysis ia JOIN FETCH ia.media WHERE ia.manipulationProb >= 0.50 OR ia.copyMoveDetected = true OR ia.splicingDetected = true ORDER BY ia.manipulationProb DESC")
    List<ImageAnalysis> findFlaggedManipulations(Pageable pageable);
}
