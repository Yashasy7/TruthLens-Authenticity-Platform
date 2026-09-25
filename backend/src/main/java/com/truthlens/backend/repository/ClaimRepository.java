package com.truthlens.backend.repository;

import com.truthlens.backend.entity.Claim;
import com.truthlens.backend.entity.ClaimType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link Claim} entity management (Module 11).
 */
@Repository
public interface ClaimRepository extends JpaRepository<Claim, UUID> {

    List<Claim> findByMediaIdOrderBySentenceIndexAsc(UUID mediaId);

    Optional<Claim> findByMediaIdAndClaimHash(UUID mediaId, String claimHash);

    List<Claim> findByMediaIdAndClaimType(UUID mediaId, ClaimType claimType);

    void deleteByMediaId(UUID mediaId);

    long countByMediaId(UUID mediaId);
}
