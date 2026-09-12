package com.truthlens.backend.repository;

import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link Role} entities.
 *
 * <p>Roles are predefined system constants seeded by the Flyway V1 migration.
 * This repository is used primarily to look up existing roles when assigning
 * them to users (e.g., granting {@code ROLE_USER} upon registration).</p>
 */
@Repository
public interface RoleRepository extends JpaRepository<Role, UUID> {

    /**
     * Retrieves a role by its name.
     *
     * <p>The primary use case is role assignment: the registration service
     * will call {@code findByName(RoleName.USER)} to fetch the default role
     * and add it to the newly created user's role set.</p>
     *
     * <p>The {@code name} column carries a unique constraint, so at most one
     * result is returned.</p>
     *
     * @param name the role name enum value
     * @return an {@link Optional} containing the matching role, or empty if not found
     */
    Optional<Role> findByName(RoleName name);
}
