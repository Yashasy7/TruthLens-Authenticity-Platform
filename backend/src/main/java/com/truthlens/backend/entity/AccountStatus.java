package com.truthlens.backend.entity;

/**
 * Represents the lifecycle status of a {@link User} account.
 *
 * <p>Stored as a {@code VARCHAR} in PostgreSQL via
 * {@link jakarta.persistence.EnumType#STRING} to ensure human-readable values
 * and forward-compatible schema evolution.</p>
 *
 * <ul>
 *   <li>{@link #ACTIVE} — Account is fully operational.</li>
 *   <li>{@link #SUSPENDED} — Account has been suspended by an administrator.</li>
 *   <li>{@link #PENDING_VERIFICATION} — Email verification has not yet been completed.</li>
 * </ul>
 */
public enum AccountStatus {

    /** Account is fully operational and can authenticate. */
    ACTIVE,

    /** Account has been suspended by a moderator or administrator. */
    SUSPENDED,

    /**
     * Account was registered but email verification has not been completed.
     * This is the initial status assigned at registration.
     */
    PENDING_VERIFICATION
}
