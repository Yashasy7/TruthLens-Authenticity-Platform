package com.truthlens.backend.repository;

import com.truthlens.backend.entity.VideoAnalysis;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link VideoAnalysis} entities (Module 06).
 */
@Repository
public interface VideoAnalysisRepository extends JpaRepository<VideoAnalysis, UUID> {

    /**
     * Finds the video analysis record for a given media ID.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis if present
     */
    Optional<VideoAnalysis> findByMediaId(UUID mediaId);

    /**
     * Finds the video analysis record along with the eagerly fetched Media entity.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis with media if present
     */
    @Query("SELECT va FROM VideoAnalysis va JOIN FETCH va.media WHERE va.media.id = :mediaId")
    Optional<VideoAnalysis> findByMediaIdWithMedia(@Param("mediaId") UUID mediaId);

    /**
     * Checks if a video analysis record exists for the given media ID.
     *
     * @param mediaId the media entity identifier
     * @return true if analysis exists
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Retrieves all video analyses with elevated deepfake probability, ordered by score descending.
     *
     * @param pageable pagination specification
     * @return list of flagged video analyses
     */
    @Query("SELECT va FROM VideoAnalysis va JOIN FETCH va.media WHERE va.deepfakeProb >= 0.50 ORDER BY va.deepfakeProb DESC")
    List<VideoAnalysis> findFlaggedDeepfakes(Pageable pageable);
}
