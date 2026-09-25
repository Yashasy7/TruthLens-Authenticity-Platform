-- =============================================================================
-- V1__create_authentication_schema.sql
-- TruthLens — Module 01: Authentication, RBAC & User Management
-- Stage 3: Initial authentication schema migration.
--
-- Creates the four tables required for Module 01:
--   users         — registered user accounts
--   roles         — system-defined access roles
--   user_roles    — many-to-many join table (users ↔ roles)
--   revoked_tokens — revoked JWT identifiers
--
-- Also seeds the five predefined system roles with stable, reproducible UUIDs.
--
-- PostgreSQL 17.x compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Table: roles
-- Created before users because user_roles references it.
-- -----------------------------------------------------------------------------
CREATE TABLE roles (
    id          UUID        NOT NULL,
    name        VARCHAR(50) NOT NULL,
    description VARCHAR(255),

    CONSTRAINT pk_roles        PRIMARY KEY (id),
    CONSTRAINT uq_roles_name   UNIQUE      (name)
);

COMMENT ON TABLE  roles             IS 'System-defined access roles. Seeded at migration time; not modified at runtime.';
COMMENT ON COLUMN roles.id          IS 'UUID primary key.';
COMMENT ON COLUMN roles.name        IS 'Role name (USER, ANALYST, MODERATOR, ADMIN, RESEARCHER). Unique.';
COMMENT ON COLUMN roles.description IS 'Human-readable description of the role.';


-- -----------------------------------------------------------------------------
-- Table: users
-- Core user account table. Email is the authentication identifier.
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id            UUID         NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100),
    status        VARCHAR(30)  NOT NULL DEFAULT 'PENDING_VERIFICATION',
    created_at    TIMESTAMPTZ  NOT NULL,
    updated_at    TIMESTAMPTZ  NOT NULL,

    CONSTRAINT pk_users       PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE      (email),
    CONSTRAINT ck_users_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION'))
);

-- idx_users_email is intentionally omitted: the UNIQUE constraint on email
-- already creates an implicit unique index sufficient for login lookups.
CREATE INDEX idx_users_status ON users (status);

COMMENT ON TABLE  users               IS 'Registered TruthLens user accounts.';
COMMENT ON COLUMN users.id            IS 'UUID primary key.';
COMMENT ON COLUMN users.email         IS 'Authentication identifier. Unique per user.';
COMMENT ON COLUMN users.password_hash IS 'BCrypt hash of the user password. Never plaintext.';
COMMENT ON COLUMN users.full_name     IS 'Display name. Optional at registration.';
COMMENT ON COLUMN users.status        IS 'Account lifecycle status: ACTIVE, SUSPENDED, or PENDING_VERIFICATION.';
COMMENT ON COLUMN users.created_at    IS 'Timestamp (with timezone) when the account was created.';
COMMENT ON COLUMN users.updated_at    IS 'Timestamp (with timezone) when the account was last updated.';


-- -----------------------------------------------------------------------------
-- Table: user_roles
-- Join table for the many-to-many users ↔ roles relationship.
-- Composite primary key (user_id, role_id) prevents duplicate assignments.
-- ON DELETE CASCADE ensures rows are removed when a user or role is deleted.
-- -----------------------------------------------------------------------------
CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,

    CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id)
        REFERENCES roles (id)
        ON DELETE CASCADE
);

CREATE INDEX idx_user_roles_user_id ON user_roles (user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);

COMMENT ON TABLE  user_roles         IS 'Many-to-many join table: users ↔ roles.';
COMMENT ON COLUMN user_roles.user_id IS 'FK → users.id. Cascades on delete.';
COMMENT ON COLUMN user_roles.role_id IS 'FK → roles.id. Cascades on delete.';


-- -----------------------------------------------------------------------------
-- Table: revoked_tokens
-- Stores identifiers of revoked JWT tokens.
-- Only the token identifier (JWT jti claim) is stored — never the full token.
-- -----------------------------------------------------------------------------
CREATE TABLE revoked_tokens (
    id               UUID         NOT NULL,
    token_identifier VARCHAR(255) NOT NULL,
    user_id          UUID         NOT NULL,
    expires_at       TIMESTAMPTZ  NOT NULL,
    revoked_at       TIMESTAMPTZ  NOT NULL,
    reason           VARCHAR(100),

    CONSTRAINT pk_revoked_tokens              PRIMARY KEY (id),
    CONSTRAINT uq_revoked_tokens_token_id     UNIQUE      (token_identifier),
    CONSTRAINT fk_revoked_tokens_user         FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
);

-- idx_revoked_tokens_token_identifier is intentionally omitted: the UNIQUE
-- constraint on token_identifier already creates an implicit unique index
-- sufficient for the JWT filter's hot-path lookup.
-- Index on expires_at supports the scheduled cleanup job.
CREATE INDEX idx_revoked_tokens_expires_at ON revoked_tokens (expires_at);
CREATE INDEX idx_revoked_tokens_user_id    ON revoked_tokens (user_id);

COMMENT ON TABLE  revoked_tokens                  IS 'Revoked JWT token identifiers. Records are purged after expiry by a scheduled cleanup job.';
COMMENT ON COLUMN revoked_tokens.id               IS 'UUID primary key.';
COMMENT ON COLUMN revoked_tokens.token_identifier IS 'JWT jti claim or equivalent short token identifier. Never the full JWT string.';
COMMENT ON COLUMN revoked_tokens.user_id          IS 'FK → users.id. Cascades on delete.';
COMMENT ON COLUMN revoked_tokens.expires_at       IS 'When the original token was set to expire.';
COMMENT ON COLUMN revoked_tokens.revoked_at       IS 'When this revocation was recorded.';
COMMENT ON COLUMN revoked_tokens.reason           IS 'Short reason: LOGOUT, PASSWORD_RESET, ADMIN_REVOCATION, etc.';


-- =============================================================================
-- Seed data: five predefined system roles
--
-- UUIDs are stable and hardcoded so that the seed data is reproducible across
-- all environments (local, CI, staging, production).
-- Do NOT change these UUIDs after the first migration has been applied.
--
-- No default user is created here. User registration and role assignment
-- are handled by the authentication service in Stage 4.
-- =============================================================================
INSERT INTO roles (id, name, description) VALUES
    ('a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d', 'USER',
     'Standard registered user with baseline access to the TruthLens platform.'),
    ('b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e', 'ANALYST',
     'Forensic analyst with access to media analysis pipelines and detailed results.'),
    ('c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f', 'MODERATOR',
     'Content and community moderator responsible for report review and enforcement.'),
    ('d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a', 'ADMIN',
     'Platform administrator with full management and configuration access.'),
    ('e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b', 'RESEARCHER',
     'Academic or independent researcher with access to datasets and analytical tools.');
