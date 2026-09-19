package com.truthlens.backend.exception;

import com.truthlens.backend.dto.ApiErrorResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

/**
 * Centralised REST exception handler for the TruthLens backend.
 *
 * <p>Maps domain exceptions and Spring validation errors to structured
 * {@link ApiErrorResponse} bodies. Stack traces and internal details are
 * never exposed to clients.</p>
 *
 * <p>Handled exceptions and their HTTP status codes:</p>
 * <ul>
 *   <li>{@link MethodArgumentNotValidException} → 400 Bad Request</li>
 *   <li>{@link EmailAlreadyExistsException}     → 409 Conflict</li>
 *   <li>{@link InvalidCredentialsException}     → 401 Unauthorized</li>
 *   <li>{@link AccountSuspendedException}       → 403 Forbidden</li>
 *   <li>{@link AccessDeniedException}           → 403 Forbidden</li>
 *   <li>{@link UserNotFoundException}           → 404 Not Found</li>
 *   <li>{@link RoleNotFoundException}           → 500 Internal Server Error</li>
 *   <li>{@link Exception} (catch-all)           → 500 Internal Server Error</li>
 * </ul>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    // -------------------------------------------------------------------------
    // Bean Validation failures — HTTP 400
    // -------------------------------------------------------------------------

    /**
     * Handles Jakarta Bean Validation failures from {@code @Valid} annotated
     * controller method parameters.
     *
     * <p>Field-level error messages are collected and concatenated into a single
     * client-safe message. No field values are included to avoid echoing
     * potentially sensitive input back to the caller.</p>
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse> handleValidationException(
            MethodArgumentNotValidException ex, HttpServletRequest request) {

        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .sorted()
                .collect(Collectors.joining("; "));

        log.debug("Validation failure on {}: {}", request.getRequestURI(), message);

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(new ApiErrorResponse(
                        HttpStatus.BAD_REQUEST.value(),
                        "VALIDATION_ERROR",
                        message,
                        request.getRequestURI()));
    }

    // -------------------------------------------------------------------------
    // Domain exceptions
    // -------------------------------------------------------------------------

    /**
     * Handles duplicate-email registration attempts — HTTP 409 Conflict.
     */
    @ExceptionHandler(EmailAlreadyExistsException.class)
    public ResponseEntity<ApiErrorResponse> handleEmailAlreadyExists(
            EmailAlreadyExistsException ex, HttpServletRequest request) {

        log.debug("Registration conflict on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ApiErrorResponse(
                        HttpStatus.CONFLICT.value(),
                        "EMAIL_ALREADY_EXISTS",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles invalid credentials during login — HTTP 401 Unauthorized.
     */
    @ExceptionHandler(InvalidCredentialsException.class)
    public ResponseEntity<ApiErrorResponse> handleInvalidCredentials(
            InvalidCredentialsException ex, HttpServletRequest request) {

        log.debug("Authentication failure on {}", request.getRequestURI());

        return ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(new ApiErrorResponse(
                        HttpStatus.UNAUTHORIZED.value(),
                        "INVALID_CREDENTIALS",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles suspended account login attempts — HTTP 403 Forbidden.
     */
    @ExceptionHandler(AccountSuspendedException.class)
    public ResponseEntity<ApiErrorResponse> handleAccountSuspended(
            AccountSuspendedException ex, HttpServletRequest request) {

        log.debug("Suspended account login attempt on {}", request.getRequestURI());

        return ResponseEntity
                .status(HttpStatus.FORBIDDEN)
                .body(new ApiErrorResponse(
                        HttpStatus.FORBIDDEN.value(),
                        "ACCOUNT_SUSPENDED",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles access-denied authorization failures — HTTP 403 Forbidden.
     */
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiErrorResponse> handleAccessDenied(
            AccessDeniedException ex, HttpServletRequest request) {

        log.debug("Access denied on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.FORBIDDEN)
                .body(new ApiErrorResponse(
                        HttpStatus.FORBIDDEN.value(),
                        "FORBIDDEN",
                        "Access denied. You do not have permission to access this resource.",
                        request.getRequestURI()));
    }

    /**
     * Handles user account not found — HTTP 404 Not Found.
     */
    @ExceptionHandler(UserNotFoundException.class)
    public ResponseEntity<ApiErrorResponse> handleUserNotFound(
            UserNotFoundException ex, HttpServletRequest request) {

        log.debug("User not found on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ApiErrorResponse(
                        HttpStatus.NOT_FOUND.value(),
                        "USER_NOT_FOUND",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles missing system role configuration — HTTP 500 Internal Server Error.
     * This indicates a database seeding problem, not a client error.
     */
    @ExceptionHandler(RoleNotFoundException.class)
    public ResponseEntity<ApiErrorResponse> handleRoleNotFound(
            RoleNotFoundException ex, HttpServletRequest request) {

        // Log at ERROR level — this is a server-side misconfiguration.
        log.error("System role configuration error on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiErrorResponse(
                        HttpStatus.INTERNAL_SERVER_ERROR.value(),
                        "CONFIGURATION_ERROR",
                        "A server configuration error occurred. Please contact the administrator.",
                        request.getRequestURI()));
    }

    // -------------------------------------------------------------------------
    // Module 02 — Media Ingestion exceptions
    // -------------------------------------------------------------------------

    /**
     * Handles invalid media, unsupported MIME types, or empty uploads — HTTP 400 Bad Request.
     */
    @ExceptionHandler(InvalidMediaException.class)
    public ResponseEntity<ApiErrorResponse> handleInvalidMedia(
            InvalidMediaException ex, HttpServletRequest request) {

        log.debug("Invalid media upload on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(new ApiErrorResponse(
                        HttpStatus.BAD_REQUEST.value(),
                        "INVALID_MEDIA",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles file size limit exceeded — HTTP 413 Payload Too Large.
     */
    @ExceptionHandler({FileSizeExceededException.class, org.springframework.web.multipart.MaxUploadSizeExceededException.class})
    public ResponseEntity<ApiErrorResponse> handleFileSizeExceeded(
            Exception ex, HttpServletRequest request) {

        log.debug("File size exceeded limit on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.PAYLOAD_TOO_LARGE)
                .body(new ApiErrorResponse(
                        HttpStatus.PAYLOAD_TOO_LARGE.value(),
                        "FILE_SIZE_EXCEEDED",
                        "The uploaded file exceeds the configured maximum upload size limit.",
                        request.getRequestURI()));
    }

    /**
     * Handles media record not found — HTTP 404 Not Found.
     */
    @ExceptionHandler(MediaNotFoundException.class)
    public ResponseEntity<ApiErrorResponse> handleMediaNotFound(
            MediaNotFoundException ex, HttpServletRequest request) {

        log.debug("Media not found on {}: {}", request.getRequestURI(), ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ApiErrorResponse(
                        HttpStatus.NOT_FOUND.value(),
                        "MEDIA_NOT_FOUND",
                        ex.getMessage(),
                        request.getRequestURI()));
    }

    /**
     * Handles quarantined storage or I/O failures — HTTP 500 Internal Server Error.
     */
    @ExceptionHandler(StorageException.class)
    public ResponseEntity<ApiErrorResponse> handleStorageException(
            StorageException ex, HttpServletRequest request) {

        log.error("Storage failure on {}: {}", request.getRequestURI(), ex.getMessage(), ex);

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiErrorResponse(
                        HttpStatus.INTERNAL_SERVER_ERROR.value(),
                        "STORAGE_ERROR",
                        "An error occurred while handling media storage. The operation was aborted.",
                        request.getRequestURI()));
    }

    // -------------------------------------------------------------------------
    // Catch-all — HTTP 500
    // -------------------------------------------------------------------------

    /**
     * Catch-all handler for unexpected exceptions.
     * Logs the full exception server-side but returns only a generic message to
     * the client to prevent information disclosure.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleGenericException(
            Exception ex, HttpServletRequest request) {

        log.error("Unexpected error on {}: {}", request.getRequestURI(), ex.getMessage(), ex);

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiErrorResponse(
                        HttpStatus.INTERNAL_SERVER_ERROR.value(),
                        "INTERNAL_SERVER_ERROR",
                        "An unexpected error occurred. Please try again later.",
                        request.getRequestURI()));
    }
}
