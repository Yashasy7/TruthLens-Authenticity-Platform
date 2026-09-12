package com.truthlens.backend.exception;

/**
 * Exception thrown when a user account cannot be found in the database.
 *
 * <p>Handled centrally by {@link GlobalExceptionHandler} and mapped to
 * HTTP 404 Not Found.</p>
 */
public class UserNotFoundException extends RuntimeException {

    public UserNotFoundException(String message) {
        super(message);
    }
}
