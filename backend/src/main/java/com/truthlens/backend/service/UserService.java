package com.truthlens.backend.service;

import com.truthlens.backend.dto.UpdateProfileRequest;
import com.truthlens.backend.dto.UserProfileResponse;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Set;
import java.util.stream.Collectors;

/**
 * Service managing authenticated user profile operations for Stage 7.
 *
 * <p>Operates strictly on the authenticated user identity derived from the JWT.
 * Protected attributes (ID, email, roles, status, passwordHash, createdAt) cannot
 * be altered through this service. Only editable profile fields (such as
 * {@code fullName}) are mutable.</p>
 */
@Service
public class UserService {

    private static final Logger log = LoggerFactory.getLogger(UserService.class);

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Retrieves the profile of the user identified by the given email.
     *
     * @param email the authenticated user's normalized email address
     * @return a safe {@link UserProfileResponse} containing non-sensitive user attributes
     * @throws UserNotFoundException if no user exists with the given email
     */
    @Transactional(readOnly = true)
    public UserProfileResponse getProfile(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UserNotFoundException("User not found with email: " + email));

        return toProfileResponse(user);
    }

    /**
     * Updates the editable profile fields for the user identified by email.
     *
     * <p>At this stage, {@code fullName} is the editable profile attribute.
     * Protected attributes remain strictly unchanged. Email is read-only.</p>
     *
     * @param email   the authenticated user's normalized email address
     * @param request the profile update request DTO
     * @return updated safe {@link UserProfileResponse} DTO
     * @throws UserNotFoundException if no user exists with the given email
     */
    @Transactional
    public UserProfileResponse updateProfile(String email, UpdateProfileRequest request) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UserNotFoundException("User not found with email: " + email));

        if (request != null && request.getFullName() != null) {
            user.setFullName(request.getFullName().strip());
        }

        User savedUser = userRepository.save(user);
        log.debug("Updated profile for user: id={}", savedUser.getId());

        return toProfileResponse(savedUser);
    }

    /**
     * Maps a persisted {@link User} entity to a safe {@link UserProfileResponse}.
     *
     * <p>Password hash, JWT credentials, and sensitive internals are never exposed.</p>
     *
     * @param user the user entity
     * @return safe profile response DTO
     */
    private UserProfileResponse toProfileResponse(User user) {
        Set<String> roleNames = user.getRoles().stream()
                .map(role -> role.getName().name())
                .collect(Collectors.toSet());

        return new UserProfileResponse(
                user.getId(),
                user.getEmail(),
                user.getFullName(),
                user.getStatus().name(),
                roleNames,
                user.getCreatedAt(),
                user.getUpdatedAt());
    }
}
