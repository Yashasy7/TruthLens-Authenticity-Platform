package com.truthlens.backend.exception;

/**
 * Exception thrown when an uploaded file is invalid, corrupt, empty,
 * or has an unsupported MIME type.
 *
 * <p>Mapped to HTTP 400 Bad Request by {@link GlobalExceptionHandler}.</p>
 */
public class InvalidMediaException extends RuntimeException {

    public InvalidMediaException(String message) {
        super(message);
    }

    public InvalidMediaException(String message, Throwable cause) {
        super(message, cause);
    }
}
