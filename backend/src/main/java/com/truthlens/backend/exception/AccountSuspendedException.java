package com.truthlens.backend.exception;

/**
 * Thrown by {@code AuthService} when a login attempt is made for a user account
 * whose status is {@code SUSPENDED}.
 *
 * <p>Maps to HTTP 403 Forbidden via {@code GlobalExceptionHandler}.
 * Using 403 (rather than 401) clearly communicates that the credentials were
 * recognised but access is explicitly denied due to account status.</p>
 */
public class AccountSuspendedException extends RuntimeException {

    public AccountSuspendedException() {
        super("This account has been suspended. Please contact support.");
    }
}
