package com.truthlens.backend.repository;

import com.truthlens.backend.entity.AvSyncAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link AvSyncAnalysis} entities (Module 08).
 */
@Repository
public interface AvSyncAnalysisRepository extends JpaRepository<AvSyncAnalysis, UUID> {

    /**
     * Finds the synchronization analysis record associated with a given media asset.
     *
     * @param mediaId UUID of the media asset
     * @return {@link Optional} containing the analysis if found
     */
    Optional<AvSyncAnalysis> findByMediaId(UUID mediaId);

    /**
     * Checks whether an analysis record exists for the given media asset.
     *
     * @param mediaId UUID of the media asset
     * @return true if an analysis record exists
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Deletes the analysis record associated with a given media asset.
     *
     * @param mediaId UUID of the media asset
     */
    void deleteByMediaId(UUID mediaId);
}
