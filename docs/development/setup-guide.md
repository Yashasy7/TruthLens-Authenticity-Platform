# Development & Setup Guide

This guide describes how to configure your local development environment and run the **TruthLens Backend Service**.

---

## 1. System Prerequisites

Ensure the following tools are installed and accessible on your system:

| Dependency | Minimum Version | Verified Version | Notes |
| :--- | :--- | :--- | :--- |
| **Java JDK** | 21 LTS | Oracle JDK 21 / OpenJDK 21 | Ensure `JAVA_HOME` points to JDK 21. |
| **Apache Maven** | 3.9+ | Maven 3.9.9 | Build and dependency manager. |
| **PostgreSQL** | 16+ | PostgreSQL 16 or 17 | Relational database engine. |
| **Git** | 2.40+ | Latest | Version control. |

---

## 2. Environment Variables

The backend strictly avoids storing sensitive credentials in source code. All runtime configuration is resolved via environment variables:

| Variable Name | Required | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `TRUTHLENS_DB_URL` | Yes | `jdbc:postgresql://localhost:5432/truthlens` | JDBC connection string. |
| `TRUTHLENS_DB_USERNAME` | Yes | `postgres` | Database user account. |
| `TRUTHLENS_DB_PASSWORD` | Yes | `your_secret_password` | Database user password. |
| `TRUTHLENS_JWT_SECRET` | Yes | `404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970` | 256-bit HMAC-SHA256 signing secret. |
| `TRUTHLENS_JWT_EXPIRATION_MS` | No | `86400000` | Token lifetime in milliseconds (Default: 24 hours). |

### Setting Environment Variables (PowerShell)

```powershell
$env:TRUTHLENS_DB_URL = "jdbc:postgresql://localhost:5432/truthlens"
$env:TRUTHLENS_DB_USERNAME = "postgres"
$env:TRUTHLENS_DB_PASSWORD = "secretpassword"
$env:TRUTHLENS_JWT_SECRET = "404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970"
```

### Setting Environment Variables (Bash)

```bash
export TRUTHLENS_DB_URL="jdbc:postgresql://localhost:5432/truthlens"
export TRUTHLENS_DB_USERNAME="postgres"
export TRUTHLENS_DB_PASSWORD="secretpassword"
export TRUTHLENS_JWT_SECRET="404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970"
```

---

## 3. Database Initialization

1. Connect to PostgreSQL via `psql` or pgAdmin:
   ```sql
   CREATE DATABASE truthlens;
   ```
2. You do **not** need to manually execute SQL scripts. Flyway will automatically run `V1__create_authentication_schema.sql` on the first application startup, creating tables and seeding default system roles.

---

## 4. Building and Running the Backend

All commands should be executed inside the `backend/` directory:

### 4.1 Verify Compilation
```bash
cd backend
mvn clean compile
```

### 4.2 Execute the Test Suite
The test suite executes 57 unit, slice, and integration tests:
```bash
mvn test
```

### 4.3 Run the Application
```bash
mvn spring-boot:run
```
The application starts by default on port `8080`.

---

## 5. Verifying the Service

Once running, verify endpoint connectivity using `curl`:

### Register an Account
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Password123!", "fullName": "Test User"}'
```

### Authenticate (Login)
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Password123!"}'
```

### Retrieve Profile
```bash
curl -X GET http://localhost:8080/api/users/me \
  -H "Authorization: Bearer <TOKEN_RETURNED_FROM_LOGIN>"
```
