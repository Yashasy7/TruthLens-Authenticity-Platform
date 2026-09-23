package com.truthlens.backend.exception;

/**
 * Exception thrown when the internal AI/ML vision service encounters an error,
 * timeout, or unexpected response format during authenticity analysis.
 */
public class AiServiceException extends RuntimeException {

    public AiServiceException(String message) {
        super(message);
    }

    public AiServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}
