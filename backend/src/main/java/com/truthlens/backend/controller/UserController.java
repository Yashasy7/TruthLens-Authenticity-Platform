package com.truthlens.backend.controller;

import com.truthlens.backend.dto.UpdateProfileRequest;
import com.truthlens.backend.dto.UserProfileResponse;
import com.truthlens.backend.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for authenticated user profile operations — Stage 7.
 *
 * <p>Base path: {@code /api/users}</p>
 *
 * <p>All endpoints operate strictly on the authenticated identity from the
 * Spring Security context. No client-supplied user ID is accepted.</p>
 *
 * <ul>
 *   <li>{@code GET /api/users/me} — retrieve the current user's profile</li>
 *   <li>{@code PUT /api/users/me} — update the current user's editable profile fields</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * Retrieves the profile of the currently authenticated user.
     *
     * @param authentication the authenticated principal established by Spring Security
     * @return HTTP 200 OK with safe {@link UserProfileResponse} body
     */
    @GetMapping("/me")
    public ResponseEntity<UserProfileResponse> getCurrentUserProfile(Authentication authentication) {
        String email = authentication.getName();
        UserProfileResponse profile = userService.getProfile(email);
        return ResponseEntity.ok(profile);
    }

    /**
     * Updates editable profile fields for the currently authenticated user.
     *
     * @param authentication the authenticated principal established by Spring Security
     * @param request        the profile update request (validated by Bean Validation)
     * @return HTTP 200 OK with updated {@link UserProfileResponse} body
     */
    @PutMapping("/me")
    public ResponseEntity<UserProfileResponse> updateCurrentUserProfile(
            Authentication authentication,
            @Valid @RequestBody UpdateProfileRequest request) {
        String email = authentication.getName();
        UserProfileResponse updatedProfile = userService.updateProfile(email, request);
        return ResponseEntity.ok(updatedProfile);
    }
}
