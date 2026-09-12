package com.truthlens.backend.controller;

import com.truthlens.backend.dto.AuthResponse;
import com.truthlens.backend.dto.LoginRequest;
import com.truthlens.backend.dto.LogoutResponse;
import com.truthlens.backend.dto.RegisterRequest;
import com.truthlens.backend.exception.InvalidCredentialsException;
import com.truthlens.backend.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for authentication endpoints — Stage 4 & 8.
 *
 * <p>Base path: {@code /api/auth}</p>
 *
 * <p>Handles only HTTP/API concerns (routing, validation trigger, status codes).
 * All business logic is delegated to {@link AuthService}. Exception mapping is
 * handled centrally by {@code GlobalExceptionHandler}.</p>
 *
 * <p><strong>Endpoints:</strong></p>
 * <ul>
 *   <li>{@code POST /api/auth/register} — create a new user account (public)</li>
 *   <li>{@code POST /api/auth/login}    — authenticate with email and password (public)</li>
 *   <li>{@code POST /api/auth/logout}   — revoke current JWT access token (authenticated)</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    // -------------------------------------------------------------------------
    // POST /api/auth/register
    // -------------------------------------------------------------------------

    /**
     * Registers a new user account.
     *
     * <p>{@code @Valid} triggers Jakarta Bean Validation on the request body.
     * Validation failures are handled by {@code GlobalExceptionHandler} and
     * returned as HTTP 400 with a structured error body before this method is
     * reached.</p>
     *
     * @param request the registration request (email, password, optional fullName)
     * @return HTTP 201 Created with a safe {@link AuthResponse} body
     */
    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(
            @Valid @RequestBody RegisterRequest request) {

        AuthResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    // -------------------------------------------------------------------------
    // POST /api/auth/login
    // -------------------------------------------------------------------------

    /**
     * Authenticates a user with email and password.
     *
     * <p>Returns HTTP 200 OK on success containing a signed JWT token.</p>
     *
     * @param request the login request (email, password)
     * @return HTTP 200 OK with a safe {@link AuthResponse} body
     */
    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(
            @Valid @RequestBody LoginRequest request) {

        AuthResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    // -------------------------------------------------------------------------
    // POST /api/auth/logout
    // -------------------------------------------------------------------------

    /**
     * Revokes the authenticated user's current JWT access token.
     *
     * <p>Requires authentication. Obtains the token from the {@code Authorization}
     * header and the user identity from Spring Security. Accepts no request body.</p>
     *
     * @param authHeader     the raw Authorization header containing the Bearer token
     * @param authentication the authenticated user identity
     * @return HTTP 200 OK with safe {@link LogoutResponse}
     */
    @PostMapping("/logout")
    public ResponseEntity<LogoutResponse> logout(
            @RequestHeader(name = HttpHeaders.AUTHORIZATION, required = false) String authHeader,
            Authentication authentication) {

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            throw new InvalidCredentialsException("Missing or malformed Bearer authorization header");
        }

        String token = authHeader.substring(7).trim();
        if (token.isEmpty()) {
            throw new InvalidCredentialsException("Missing or malformed Bearer authorization header");
        }

        String email = authentication.getName();
        authService.logout(token, email);

        return ResponseEntity.ok(new LogoutResponse("Logout successful"));
    }
}
