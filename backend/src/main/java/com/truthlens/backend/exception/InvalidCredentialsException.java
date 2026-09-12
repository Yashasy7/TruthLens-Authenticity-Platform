package com.truthlens.backend.exception;

/**
 * Thrown by {@code AuthService} when login fails because no account exists
 * for the supplied email or the password does not match.
 *
 * <p>A deliberately generic message is used to avoid revealing whether the
 * email exists in the system (prevents user enumeration attacks).</p>
 *
 * <p>Maps to HTTP 401 Unauthorized via {@code GlobalExceptionHandler}.</p>
 */
public class InvalidCredentialsException extends RuntimeException {

    public InvalidCredentialsException() {
        super("Invalid email or password.");
    }
}
