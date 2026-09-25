package com.truthlens.backend.repository;

import com.truthlens.backend.entity.RevokedToken;
import com.truthlens.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link RevokedToken} entities.
 *
 * <p>The authentication filter (a later stage) will call
 * {@link #existsByTokenIdentifier(String)} on every authenticated request to
 * determine whether the presented JWT has been revoked. This check must be
 * fast — the {@code token_identifier} column carries both a unique constraint
 * and a dedicated index in the Flyway migration schema.</p>
 */
@Repository
public interface RevokedTokenRepository extends JpaRepository<RevokedToken, UUID> {

    /**
     * Checks whether a revocation record exists for the given token identifier.
     *
     * <p>This is the critical hot path: called by the JWT authentication filter
     * on every protected API request. The indexed {@code token_identifier}
     * column ensures sub-millisecond lookup at scale.</p>
     *
     * @param tokenIdentifier the JWT {@code jti} claim or equivalent identifier
     * @return {@code true} if the token has been revoked, {@code false} otherwise
     */
    boolean existsByTokenIdentifier(String tokenIdentifier);

    /**
     * Retrieves all revocation records associated with a specific user.
     *
     * <p>Useful for administrative revocation of all sessions belonging to a
     * user (e.g., on password reset or account suspension).</p>
     *
     * @param user the user whose revoked tokens should be retrieved
     * @return a list of revoked token records for the user (may be empty)
     */
    java.util.List<RevokedToken> findAllByUser(User user);

    /**
     * Deletes all revocation records whose {@code expiresAt} timestamp is
     * before the given cutoff time.
     *
     * <p>Used by a scheduled cleanup task (a later operational stage) to
     * remove expired revocation records from the database. Expired tokens
     * are inherently invalid regardless of revocation status, so their
     * records no longer serve a purpose.</p>
     *
     * @param cutoff the cutoff timestamp; records with {@code expiresAt} before
     *               this value will be deleted
     */
    void deleteAllByExpiresAtBefore(OffsetDateTime cutoff);
}
