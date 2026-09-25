package com.truthlens.backend.exception;

/**
 * Thrown by {@code AuthService} when a registration attempt uses an email
 * address that is already associated with an existing user account.
 *
 * <p>Maps to HTTP 409 Conflict via {@code GlobalExceptionHandler}.</p>
 */
public class EmailAlreadyExistsException extends RuntimeException {

    public EmailAlreadyExistsException(String email) {
        super("An account with email '" + email + "' already exists.");
    }
}
