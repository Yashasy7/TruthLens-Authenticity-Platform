package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AudioAnalysis;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link AudioAnalysis} entities (Module 07).
 */
@Repository
public interface AudioAnalysisRepository extends JpaRepository<AudioAnalysis, UUID> {

    /**
     * Finds the audio analysis record for a given media ID.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis if present
     */
    Optional<AudioAnalysis> findByMediaId(UUID mediaId);

    /**
     * Finds the audio analysis record along with the eagerly fetched Media entity.
     *
     * @param mediaId the media entity identifier
     * @return an {@link Optional} containing the analysis with media if present
     */
    @Query("SELECT aa FROM AudioAnalysis aa JOIN FETCH aa.media WHERE aa.media.id = :mediaId")
    Optional<AudioAnalysis> findByMediaIdWithMedia(@Param("mediaId") UUID mediaId);

    /**
     * Checks if an audio analysis record exists for the given media ID.
     *
     * @param mediaId the media entity identifier
     * @return true if analysis exists
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Retrieves all audio analyses with elevated synthetic voice probability, ordered by score descending.
     *
     * @param pageable pagination specification
     * @return list of flagged audio analyses
     */
    @Query("SELECT aa FROM AudioAnalysis aa JOIN FETCH aa.media WHERE aa.syntheticVoiceProb >= 0.50 ORDER BY aa.syntheticVoiceProb DESC")
    List<AudioAnalysis> findFlaggedSyntheticAudio(Pageable pageable);
}
