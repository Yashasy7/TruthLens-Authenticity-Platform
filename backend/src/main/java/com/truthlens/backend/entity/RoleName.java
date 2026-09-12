package com.truthlens.backend.entity;

/**
 * Represents the set of system-defined roles in TruthLens.
 *
 * <p>Exactly five roles are permitted, as specified in the project blueprint.
 * Stored as a {@code VARCHAR} in PostgreSQL via
 * {@link jakarta.persistence.EnumType#STRING}.</p>
 *
 * <ul>
 *   <li>{@link #USER}       — Standard registered user.</li>
 *   <li>{@link #ANALYST}    — Forensic analysis specialist.</li>
 *   <li>{@link #MODERATOR}  — Content and community moderator.</li>
 *   <li>{@link #ADMIN}      — Platform administrator.</li>
 *   <li>{@link #RESEARCHER} — Academic or independent researcher.</li>
 * </ul>
 */
public enum RoleName {

    /** Standard registered user with baseline access. */
    USER,

    /** Forensic analyst with access to analysis pipelines and results. */
    ANALYST,

    /** Moderator responsible for content and report review. */
    MODERATOR,

    /** Platform administrator with full management access. */
    ADMIN,

    /** Researcher with access to datasets and analytical tools. */
    RESEARCHER
}
