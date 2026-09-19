package com.truthlens.backend.exception;

/**
 * Exception thrown when storing, reading, or deleting a file in quarantined storage fails.
 *
 * <p>Mapped to HTTP 500 Internal Server Error by {@link GlobalExceptionHandler}.</p>
 */
public class StorageException extends RuntimeException {

    public StorageException(String message) {
        super(message);
    }

    public StorageException(String message, Throwable cause) {
        super(message, cause);
    }
}
