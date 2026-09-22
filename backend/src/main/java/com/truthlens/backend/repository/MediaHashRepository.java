package com.truthlens.backend.repository;

import com.truthlens.backend.entity.MediaHash;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link MediaHash} entities.
 *
 * <p>Provides indexed queries for exact cryptographic hashes, bounded perceptual
 * visual candidates, and acoustic fingerprint matching with deterministic canonical ordering.</p>
 */
@Repository
public interface MediaHashRepository extends JpaRepository<MediaHash, UUID> {

    /**
     * Finds the fingerprint record for a given media file.
     *
     * @param mediaId the media's unique identifier
     * @return Optional containing the MediaHash if found
     */
    Optional<MediaHash> findByMediaId(UUID mediaId);

    /**
     * Checks if a fingerprint record already exists for a media file.
     *
     * @param mediaId the media's unique identifier
     * @return true if already fingerprinted
     */
    boolean existsByMediaId(UUID mediaId);

    /**
     * Finds existing records matching the exact same SHA-256 cryptographic hash,
     * excluding the specified media item.
     *
     * @param sha256Hash cryptographic hash
     * @param mediaId    id of the media being checked
     * @return list of matching MediaHash records
     */
    List<MediaHash> findBySha256HashAndMediaIdNot(String sha256Hash, UUID mediaId);

    /**
     * Finds exact SHA-256 matches ordered deterministically by earliest creation date,
     * with UUID tie-breaker (F-05 canonical duplicate selection), using JOIN FETCH to eliminate N+1 queries (P-02).
     *
     * @param sha256Hash cryptographic hash
     * @param mediaId    id of the media being checked
     * @return list of matching MediaHash records, earliest first
     */
    @Query("SELECT mh FROM MediaHash mh JOIN FETCH mh.media m WHERE mh.sha256Hash = :sha256Hash AND m.id <> :mediaId ORDER BY m.createdAt ASC, m.id ASC")
    List<MediaHash> findExactMatchesOrderedByEarliest(@Param("sha256Hash") String sha256Hash, @Param("mediaId") UUID mediaId);

    /**
     * Finds candidate records that have a perceptual visual hash (pHash),
     * excluding the specified media item (unbounded backward-compatibility query).
     *
     * @param mediaId id of the media being checked
     * @return list of candidate MediaHash records
     */
    @Query("SELECT mh FROM MediaHash mh JOIN FETCH mh.media m WHERE mh.phash IS NOT NULL AND m.id <> :mediaId ORDER BY m.createdAt ASC, m.id ASC")
    List<MediaHash> findPerceptualCandidatesExcluding(@Param("mediaId") UUID mediaId);

    /**
     * Finds bounded candidate records that have a perceptual visual hash (pHash),
     * eliminating unbounded full-table memory loading (P-01) and N+1 queries (P-02).
     *
     * @param mediaId  id of the media being checked
     * @param pageable pagination / candidate limit constraint
     * @return list of candidate MediaHash records
     */
    @Query("SELECT mh FROM MediaHash mh JOIN FETCH mh.media m WHERE mh.phash IS NOT NULL AND m.id <> :mediaId ORDER BY m.createdAt ASC, m.id ASC")
    List<MediaHash> findPerceptualCandidatesBounded(@Param("mediaId") UUID mediaId, Pageable pageable);

    /**
     * Finds candidate records that have an acoustic fingerprint (chromaprint),
     * excluding the specified media item (unbounded backward-compatibility query).
     *
     * @param mediaId id of the media being checked
     * @return list of candidate MediaHash records
     */
    @Query("SELECT mh FROM MediaHash mh JOIN FETCH mh.media m WHERE mh.chromaprint IS NOT NULL AND m.id <> :mediaId ORDER BY m.createdAt ASC, m.id ASC")
    List<MediaHash> findAcousticCandidatesExcluding(@Param("mediaId") UUID mediaId);

    /**
     * Finds bounded candidate records that have an acoustic fingerprint (chromaprint),
     * eliminating unbounded full-table memory loading (P-01) and N+1 queries (P-02).
     *
     * @param mediaId  id of the media being checked
     * @param pageable pagination / candidate limit constraint
     * @return list of candidate MediaHash records
     */
    @Query("SELECT mh FROM MediaHash mh JOIN FETCH mh.media m WHERE mh.chromaprint IS NOT NULL AND m.id <> :mediaId ORDER BY m.createdAt ASC, m.id ASC")
    List<MediaHash> findAcousticCandidatesBounded(@Param("mediaId") UUID mediaId, Pageable pageable);

    /**
     * Finds all media hashes flagged as duplicates.
     *
     * @return list of duplicate MediaHash records
     */
    List<MediaHash> findByIsDuplicateTrue();
}
