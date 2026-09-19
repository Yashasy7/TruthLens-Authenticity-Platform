# TruthLens REST API: Authentication, User & RBAC

This document defines the exact HTTP REST API contracts implemented in **Module 01: Authentication, RBAC & User Management**.

---

## 1. Overview & Conventions

- **Base URL**: `http://localhost:8080` (default local port)
- **Protocol**: HTTP/1.1 (HTTPS in staging/production)
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token in `Authorization` header:
  ```http
  Authorization: Bearer <jwt_access_token>
  ```
- **Error Format**: All errors return a standardized `ApiErrorResponse` JSON body.

---

## 2. Authentication Endpoints (`/api/auth`)

### 2.1 User Registration

Creates a new user account. Upon successful registration, the account is automatically assigned the `USER` role.

- **URL**: `/api/auth/register`
- **Method**: `POST`
- **Access**: Public

#### Request Body
```json
{
  "email": "analyst.smith@example.com",
  "password": "SecurePassword123!",
  "fullName": "Agent Smith"
}
```

#### Field Constraints
| Field | Type | Required | Constraints |
| :--- | :--- | :--- | :--- |
| `email` | String | Yes | Valid email format, trimmed, max 255 chars |
| `password` | String | Yes | Minimum 8 characters, max 128 chars |
| `fullName` | String | No | Optional display name, max 100 chars |

#### Responses
- **201 Created**:
  ```json
  {
    "message": "Registration successful",
    "token": null,
    "tokenType": null,
    "userId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "analyst.smith@example.com",
    "fullName": "Agent Smith",
    "status": "ACTIVE",
    "roles": ["USER"],
    "createdAt": "2026-09-19T14:30:00Z"
  }
  ```
- **400 Bad Request**: Validation constraint failed (e.g., password < 8 characters or invalid email format).
- **409 Conflict**: Email is already registered.

---

### 2.2 User Login

Authenticates user credentials and returns a signed JWT access token.

- **URL**: `/api/auth/login`
- **Method**: `POST`
- **Access**: Public

#### Request Body
```json
{
  "email": "analyst.smith@example.com",
  "password": "SecurePassword123!"
}
```

#### Responses
- **200 OK**:
  ```json
  {
    "message": "Login successful",
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyMWYz...",
    "tokenType": "Bearer",
    "userId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "analyst.smith@example.com",
    "fullName": "Agent Smith",
    "status": "ACTIVE",
    "roles": ["USER"],
    "createdAt": "2026-09-19T14:30:00Z"
  }
  ```
- **400 Bad Request**: Email or password missing/empty.
- **401 Unauthorized**: Invalid email or password (generic message prevents user enumeration).
- **403 Forbidden**: Account is in `SUSPENDED` status.

---

### 2.3 User Logout

Revokes the caller's current JWT access token by registering its unique identifier (`jti`) in the revocation blacklist.

- **URL**: `/api/auth/logout`
- **Method**: `POST`
- **Access**: Authenticated (`Bearer <token>`)
- **Request Body**: None

#### Responses
- **200 OK**:
  ```json
  {
    "message": "Logout successful"
  }
  ```
- **401 Unauthorized**: Missing, malformed, or already-revoked Bearer token.

---

## 3. User Profile Endpoints (`/api/users`)

All user endpoints operate strictly on the authenticated identity extracted from the JWT token.

### 3.1 Get Current Profile

- **URL**: `/api/users/me`
- **Method**: `GET`
- **Access**: Authenticated (`Bearer <token>`)

#### Responses
- **200 OK**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "analyst.smith@example.com",
    "fullName": "Agent Smith",
    "status": "ACTIVE",
    "roles": ["USER"],
    "createdAt": "2026-09-19T14:30:00Z",
    "updatedAt": "2026-09-19T14:30:00Z"
  }
  ```
- **401 Unauthorized**: Unauthenticated or revoked token.
- **404 Not Found**: User not found in database.

---

### 3.2 Update Current Profile

Updates editable profile fields (`fullName`). Protected attributes such as `id`, `email`, `roles`, `status`, and `passwordHash` are immutable through this endpoint.

- **URL**: `/api/users/me`
- **Method**: `PUT`
- **Access**: Authenticated (`Bearer <token>`)

#### Request Body
```json
{
  "fullName": "Agent Smith Updated"
}
```

#### Field Constraints
| Field | Type | Required | Constraints |
| :--- | :--- | :--- | :--- |
| `fullName` | String | No | Max 100 characters |

#### Responses
- **200 OK**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "analyst.smith@example.com",
    "fullName": "Agent Smith Updated",
    "status": "ACTIVE",
    "roles": ["USER"],
    "createdAt": "2026-09-19T14:30:00Z",
    "updatedAt": "2026-09-19T14:35:12Z"
  }
  ```
- **400 Bad Request**: Full name exceeds 100 characters.
- **401 Unauthorized**: Unauthenticated.

---

## 4. RBAC Verification Endpoints (`/api/rbac`)

Internal verification endpoints enforcing method-level security (`@PreAuthorize`):

| Endpoint | Method | Required Authority | Success Response |
| :--- | :--- | :--- | :--- |
| `/api/rbac/user` | `GET` | `hasRole('USER')` | `{"message": "Authorized: USER"}` |
| `/api/rbac/analyst` | `GET` | `hasRole('ANALYST')` | `{"message": "Authorized: ANALYST"}` |
| `/api/rbac/moderator` | `GET` | `hasRole('MODERATOR')` | `{"message": "Authorized: MODERATOR"}` |
| `/api/rbac/admin` | `GET` | `hasRole('ADMIN')` | `{"message": "Authorized: ADMIN"}` |
| `/api/rbac/researcher`| `GET` | `hasRole('RESEARCHER')` | `{"message": "Authorized: RESEARCHER"}` |

#### Responses
- **200 OK**: Caller holds required role.
- **401 Unauthorized**: No token provided.
- **403 Forbidden**: Caller's token does not include the required role.

---

## 5. Standard Error Format (`ApiErrorResponse`)

When an error occurs, the server responds with a uniform JSON structure:

```json
{
  "status": 400,
  "error": "VALIDATION_ERROR",
  "message": "Email must be a valid email address; Password must be at least 8 characters",
  "path": "/api/auth/register",
  "timestamp": "2026-09-19T14:30:15.123456Z"
}
```

### Error Code Reference
| Error Code | HTTP Status | Meaning |
| :--- | :--- | :--- |
| `VALIDATION_ERROR` | 400 | One or more input fields failed validation constraints. |
| `INVALID_CREDENTIALS` | 401 | Invalid email/password, or missing/malformed Bearer header. |
| `ACCOUNT_SUSPENDED` | 403 | The user account is suspended. |
| `FORBIDDEN` | 403 | Access denied by RBAC authorization rules. |
| `USER_NOT_FOUND` | 404 | Authenticated user record does not exist. |
| `EMAIL_ALREADY_EXISTS`| 409 | Attempted registration with an already-registered email. |
| `CONFIGURATION_ERROR` | 500 | Database seeding issue (e.g. USER role not found). |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error. |
