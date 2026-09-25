package com.truthlens.backend.exception;

/**
 * Thrown by {@code AuthService} when the required {@code USER} role cannot be
 * found in the {@code roles} table during registration.
 *
 * <p>This indicates a misconfiguration — the Flyway V1 migration should have
 * seeded all five system roles. If this exception is thrown, the database is
 * in an unexpected state and the error is on the server side.</p>
 *
 * <p>Maps to HTTP 500 Internal Server Error via {@code GlobalExceptionHandler}.</p>
 */
public class RoleNotFoundException extends RuntimeException {

    public RoleNotFoundException(String roleName) {
        super("Required system role '" + roleName + "' is not configured. "
              + "Please verify the database seed data.");
    }
}
