package com.truthlens.backend.repository;

import com.truthlens.backend.entity.Transcript;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link Transcript} entities (Module 10).
 */
@Repository
public interface TranscriptRepository extends JpaRepository<Transcript, UUID> {

    @Query("SELECT t FROM Transcript t JOIN FETCH t.media WHERE t.media.id = :mediaId")
    Optional<Transcript> findByMediaId(@Param("mediaId") UUID mediaId);

    boolean existsByMediaId(UUID mediaId);
}
