package com.truthlens.backend.controller;

import com.truthlens.backend.dto.AuthResponse;
import com.truthlens.backend.dto.LoginRequest;
import com.truthlens.backend.dto.RegisterRequest;
import com.truthlens.backend.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for authentication endpoints — Stage 4.
 *
 * <p>Base path: {@code /api/auth}</p>
 *
 * <p>Handles only HTTP/API concerns (routing, validation trigger, status codes).
 * All business logic is delegated to {@link AuthService}. Exception mapping is
 * handled centrally by {@code GlobalExceptionHandler}.</p>
 *
 * <p><strong>Endpoints:</strong></p>
 * <ul>
 *   <li>{@code POST /api/auth/register} — create a new user account</li>
 *   <li>{@code POST /api/auth/login}    — authenticate with email and password</li>
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
     * <p>Returns HTTP 200 OK on success. No JWT is issued at this stage —
     * the response contains only safe user information confirming authentication.
     * JWT generation is implemented in Stage 5.</p>
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
}
