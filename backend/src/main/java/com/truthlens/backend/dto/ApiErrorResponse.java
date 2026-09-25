package com.truthlens.backend.dto;

import java.time.OffsetDateTime;

/**
 * Structured error response DTO returned by the global exception handler.
 *
 * <p>Provides a consistent error envelope across all API error paths so that
 * clients can reliably parse error details without inspecting HTTP status codes
 * alone.</p>
 *
 * <p><strong>Security contract:</strong> this DTO must never include stack traces,
 * SQL errors, internal class names, password data, or any other sensitive
 * implementation detail.</p>
 */
public class ApiErrorResponse {

    /** HTTP status code mirrored in the body for client convenience. */
    private int status;

    /** Short machine-readable error code (e.g. {@code "EMAIL_ALREADY_EXISTS"}). */
    private String error;

    /** Human-readable message safe to display to end users. */
    private String message;

    /** The request path that produced the error. */
    private String path;

    /** Timestamp of when the error occurred. */
    private OffsetDateTime timestamp;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public ApiErrorResponse() {
    }

    public ApiErrorResponse(int status, String error, String message, String path) {
        this.status    = status;
        this.error     = error;
        this.message   = message;
        this.path      = path;
        this.timestamp = OffsetDateTime.now();
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public OffsetDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(OffsetDateTime timestamp) {
        this.timestamp = timestamp;
    }
}
