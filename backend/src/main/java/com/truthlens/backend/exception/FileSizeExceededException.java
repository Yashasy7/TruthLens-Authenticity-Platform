package com.truthlens.backend.exception;

/**
 * Exception thrown when an uploaded file exceeds the configured maximum upload size.
 *
 * <p>Mapped to HTTP 413 Payload Too Large by {@link GlobalExceptionHandler}.</p>
 */
public class FileSizeExceededException extends RuntimeException {

    public FileSizeExceededException(String message) {
        super(message);
    }
}
