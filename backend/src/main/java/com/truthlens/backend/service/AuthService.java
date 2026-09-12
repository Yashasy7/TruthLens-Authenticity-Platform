package com.truthlens.backend.service;

import com.truthlens.backend.dto.AuthResponse;
import com.truthlens.backend.dto.LoginRequest;
import com.truthlens.backend.dto.RegisterRequest;
import com.truthlens.backend.entity.AccountStatus;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AccountSuspendedException;
import com.truthlens.backend.exception.EmailAlreadyExistsException;
import com.truthlens.backend.exception.InvalidCredentialsException;
import com.truthlens.backend.exception.RoleNotFoundException;
import com.truthlens.backend.repository.RoleRepository;
import com.truthlens.backend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Set;
import java.util.stream.Collectors;

/**
 * Core authentication service for TruthLens — Stage 4.
 *
 * <p>Handles user registration and login. Responsibilities:</p>
 * <ul>
 *   <li>Email normalisation (trim + lowercase) applied consistently to both
 *       registration and login so that lookups are case-insensitive in practice.</li>
 *   <li>BCrypt password hashing on registration via the injected
 *       {@link PasswordEncoder}.</li>
 *   <li>Duplicate email detection before persistence.</li>
 *   <li>USER role assignment from the database seed data on registration.</li>
 *   <li>Credential verification and account status check on login.</li>
 * </ul>
 *
 * <p><strong>Stage boundary:</strong> JWT generation and Spring Security
 * {@code UserDetailsService} integration belong to Stage 5 and are absent here.</p>
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    private final UserRepository    userRepository;
    private final RoleRepository    roleRepository;
    private final PasswordEncoder   passwordEncoder;

    // -------------------------------------------------------------------------
    // Constructor injection — no field injection
    // -------------------------------------------------------------------------

    public AuthService(UserRepository userRepository,
                       RoleRepository roleRepository,
                       PasswordEncoder passwordEncoder) {
        this.userRepository  = userRepository;
        this.roleRepository  = roleRepository;
        this.passwordEncoder = passwordEncoder;
    }

    // -------------------------------------------------------------------------
    // Registration
    // -------------------------------------------------------------------------

    /**
     * Registers a new user account.
     *
     * <p>Registration flow:</p>
     * <ol>
     *   <li>Normalise email (trim + lowercase).</li>
     *   <li>Check for duplicate email — throw {@link EmailAlreadyExistsException}
     *       (HTTP 409) if taken.</li>
     *   <li>Hash the supplied password with BCrypt.</li>
     *   <li>Build a new {@link User} entity with status {@code ACTIVE}.</li>
     *   <li>Load the {@code USER} role from the database seed — throw
     *       {@link RoleNotFoundException} (HTTP 500) if missing.</li>
     *   <li>Assign the {@code USER} role to the new account.</li>
     *   <li>Persist and return a safe {@link AuthResponse}.</li>
     * </ol>
     *
     * @param request the registration request DTO (pre-validated by the controller)
     * @return a safe {@link AuthResponse} containing the new user's details
     * @throws EmailAlreadyExistsException if the email is already registered
     * @throws RoleNotFoundException       if the USER role is missing from the database
     */
    @Transactional
    public AuthResponse register(RegisterRequest request) {

        // Step 1 — Normalise email
        String email = normaliseEmail(request.getEmail());

        // Step 2 — Duplicate check
        if (userRepository.existsByEmail(email)) {
            throw new EmailAlreadyExistsException(email);
        }

        // Step 3 — Hash the password (BCrypt)
        String passwordHash = passwordEncoder.encode(request.getPassword());

        // Step 4 — Build User entity; set status to ACTIVE
        String fullName = request.getFullName() != null
                ? request.getFullName().strip()
                : null;

        User user = new User(email, passwordHash, fullName);
        user.setStatus(AccountStatus.ACTIVE);

        // Step 5 — Load the seeded USER role
        Role userRole = roleRepository.findByName(RoleName.USER)
                .orElseThrow(() -> new RoleNotFoundException(RoleName.USER.name()));

        // Step 6 — Assign role (within transaction, roles set is initialised)
        user.getRoles().add(userRole);

        // Step 7 — Persist
        User saved = userRepository.save(user);
        log.info("Registered new user: id={}, email={}", saved.getId(), saved.getEmail());

        return buildAuthResponse("Registration successful", saved);
    }

    // -------------------------------------------------------------------------
    // Login
    // -------------------------------------------------------------------------

    /**
     * Authenticates a user with email and password.
     *
     * <p>Login flow:</p>
     * <ol>
     *   <li>Normalise email (trim + lowercase).</li>
     *   <li>Look up the user by email — throw {@link InvalidCredentialsException}
     *       (HTTP 401) if not found (generic message to prevent user enumeration).</li>
     *   <li>Verify the supplied password against the stored BCrypt hash — throw
     *       {@link InvalidCredentialsException} (HTTP 401) on mismatch.</li>
     *   <li>Check account status — throw {@link AccountSuspendedException}
     *       (HTTP 403) if suspended.</li>
     *   <li>Return a safe {@link AuthResponse} (no JWT at this stage).</li>
     * </ol>
     *
     * @param request the login request DTO (pre-validated by the controller)
     * @return a safe {@link AuthResponse} containing the authenticated user's details
     * @throws InvalidCredentialsException if email is not found or password is wrong
     * @throws AccountSuspendedException   if the account is suspended
     */
    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {

        // Step 1 — Normalise email
        String email = normaliseEmail(request.getEmail());

        // Step 2 — Find user; generic error on miss (no enumeration)
        User user = userRepository.findByEmail(email)
                .orElseThrow(InvalidCredentialsException::new);

        // Step 3 — Verify password
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new InvalidCredentialsException();
        }

        // Step 4 — Check account status
        if (user.getStatus() == AccountStatus.SUSPENDED) {
            throw new AccountSuspendedException();
        }

        log.info("Successful login: id={}, email={}", user.getId(), user.getEmail());

        // Step 5 — Return safe response (JWT generation is Stage 5)
        return buildAuthResponse("Login successful", user);
    }

    // -------------------------------------------------------------------------
    // Private helpers
    // -------------------------------------------------------------------------

    /**
     * Normalises an email address for consistent storage and lookup.
     *
     * <p>Applies: strip leading/trailing whitespace, then convert to lowercase.
     * This ensures that {@code "  User@Example.COM  "} and {@code "user@example.com"}
     * resolve to the same account.</p>
     *
     * @param raw the raw email string from the request
     * @return the normalised email string
     */
    private String normaliseEmail(String raw) {
        return raw == null ? null : raw.strip().toLowerCase();
    }

    /**
     * Builds a safe {@link AuthResponse} from a persisted {@link User}.
     *
     * <p>The roles set is accessed here — callers must ensure this method is
     * invoked within an active transaction (or with an already-initialised
     * roles collection) to avoid a {@code LazyInitializationException}.</p>
     *
     * @param message a short human-readable result message
     * @param user    the user entity to map
     * @return the constructed {@link AuthResponse}
     */
    private AuthResponse buildAuthResponse(String message, User user) {
        Set<String> roleNames = user.getRoles().stream()
                .map(role -> role.getName().name())
                .collect(Collectors.toSet());

        return new AuthResponse(
                message,
                user.getId(),
                user.getEmail(),
                user.getFullName(),
                user.getStatus().name(),
                roleNames,
                user.getCreatedAt());
    }
}
