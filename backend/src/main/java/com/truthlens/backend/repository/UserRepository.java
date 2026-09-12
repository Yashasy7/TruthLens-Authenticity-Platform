package com.truthlens.backend.repository;

import com.truthlens.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link User} entities.
 *
 * <p>Provides standard CRUD operations inherited from {@link JpaRepository},
 * plus domain-specific query methods needed by the authentication layer.</p>
 *
 * <p>Additional query methods for authentication (e.g., lockout checks,
 * status validation) will be added in the authentication service stage
 * (Stage 4 / Stage 5) as required.</p>
 */
@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    /**
     * Retrieves a user by their email address.
     *
     * <p>This is the primary lookup method for authentication: the
     * {@code UserDetailsService} implementation (a later stage) will call this
     * method to load a user during the login flow.</p>
     *
     * <p>The query targets the {@code email} column, which carries a unique
     * constraint, so at most one result is returned.</p>
     *
     * @param email the email address to search for (case-sensitive)
     * @return an {@link Optional} containing the matching user, or empty if none
     */
    Optional<User> findByEmail(String email);

    /**
     * Checks whether a user with the given email already exists.
     *
     * <p>Used during registration to detect duplicate email addresses before
     * attempting to persist a new {@link User} record.</p>
     *
     * @param email the email address to check
     * @return {@code true} if a user with this email exists, {@code false} otherwise
     */
    boolean existsByEmail(String email);
}
