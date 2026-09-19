package com.truthlens.backend.exception;

/**
 * Exception thrown when a media record cannot be found by its UUID.
 *
 * <p>Mapped to HTTP 404 Not Found by {@link GlobalExceptionHandler}.</p>
 */
public class MediaNotFoundException extends RuntimeException {

    public MediaNotFoundException(String message) {
        super(message);
    }
}
