package com.truthlens.backend.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Internal verification controller for Role-Based Access Control (RBAC) — Stage 6.
 *
 * <p>Base path: {@code /api/rbac}</p>
 *
 * <p>These endpoints exist strictly to verify that method-level security
 * ({@code @PreAuthorize}) and role-based authorization function correctly.
 * They return minimal, harmless responses and contain no business logic.</p>
 *
 * <ul>
 *   <li>{@code GET /api/rbac/user} — requires {@code ROLE_USER}</li>
 *   <li>{@code GET /api/rbac/analyst} — requires {@code ROLE_ANALYST}</li>
 *   <li>{@code GET /api/rbac/moderator} — requires {@code ROLE_MODERATOR}</li>
 *   <li>{@code GET /api/rbac/admin} — requires {@code ROLE_ADMIN}</li>
 *   <li>{@code GET /api/rbac/researcher} — requires {@code ROLE_RESEARCHER}</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/rbac")
public class RbacTestController {

    /**
     * Test endpoint restricted to users with the USER role.
     *
     * @return HTTP 200 OK with confirmation message
     */
    @GetMapping("/user")
    @PreAuthorize("hasRole('USER')")
    public ResponseEntity<Map<String, String>> userAccess() {
        return ResponseEntity.ok(Map.of("message", "Authorized: USER"));
    }

    /**
     * Test endpoint restricted to users with the ANALYST role.
     *
     * @return HTTP 200 OK with confirmation message
     */
    @GetMapping("/analyst")
    @PreAuthorize("hasRole('ANALYST')")
    public ResponseEntity<Map<String, String>> analystAccess() {
        return ResponseEntity.ok(Map.of("message", "Authorized: ANALYST"));
    }

    /**
     * Test endpoint restricted to users with the MODERATOR role.
     *
     * @return HTTP 200 OK with confirmation message
     */
    @GetMapping("/moderator")
    @PreAuthorize("hasRole('MODERATOR')")
    public ResponseEntity<Map<String, String>> moderatorAccess() {
        return ResponseEntity.ok(Map.of("message", "Authorized: MODERATOR"));
    }

    /**
     * Test endpoint restricted to users with the ADMIN role.
     *
     * @return HTTP 200 OK with confirmation message
     */
    @GetMapping("/admin")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, String>> adminAccess() {
        return ResponseEntity.ok(Map.of("message", "Authorized: ADMIN"));
    }

    /**
     * Test endpoint restricted to users with the RESEARCHER role.
     *
     * @return HTTP 200 OK with confirmation message
     */
    @GetMapping("/researcher")
    @PreAuthorize("hasRole('RESEARCHER')")
    public ResponseEntity<Map<String, String>> researcherAccess() {
        return ResponseEntity.ok(Map.of("message", "Authorized: RESEARCHER"));
    }
}
