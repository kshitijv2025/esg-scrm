# Authentication Specification

## Overview

JWT-based authentication with multi-tenant org isolation. All routes require auth except `/api/auth/register`, `/api/auth/login`, `/api/health`, and Twilio webhook endpoints.

## Registration Flow

### `POST /api/auth/register`

**Request**:

```json
{
  "name": "Rahim Ahmed",
  "email": "rahim@factory.com",
  "password": "SecurePass1",
  "org_name": "Bangladesh Export Textiles Ltd.",
  "industry": "Garment/Textile",
  "country": "Bangladesh"
}
```

**Password requirements**: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit. Validated via Pydantic `@field_validator`.

**Response** (201):

```json
{
  "token": "eyJ...",
  "user": {
    "id": "usr_abc",
    "name": "Rahim Ahmed",
    "email": "rahim@factory.com",
    "role": "admin"
  },
  "org": {
    "id": "org_xyz",
    "name": "Bangladesh Export Textiles Ltd.",
    "industry": "Garment/Textile"
  }
}
```

**Error** (400): "Registration failed. Please try again." (generic — no email enumeration)

**Rate limit**: 5 requests per 60 seconds per client IP. Bounded at 10,000 tracked IPs.

## Login Flow

### `POST /api/auth/login`

**Request**:

```json
{ "email": "rahim@factory.com", "password": "SecurePass1" }
```

**Response** (200):

```json
{
  "token": "eyJ...",
  "user": {
    "id": "usr_abc",
    "name": "Rahim Ahmed",
    "email": "rahim@factory.com",
    "role": "admin"
  },
  "org": { "id": "org_xyz", "name": "Bangladesh Export Textiles Ltd." }
}
```

**Error** (401): "Invalid email or password" (same message for wrong password and nonexistent user)

**Rate limit**: 5 requests per 60 seconds per client IP.

## JWT Token Structure

HS256 signed. Payload:

```json
{
  "sub": "usr_abc",
  "org_id": "org_xyz",
  "email": "rahim@factory.com",
  "role": "admin",
  "exp": 1716300000
}
```

Secret from `JWT_SECRET` env var (min 32 bytes). Expiry from `JWT_EXPIRY_HOURS` (default 24).

## Role-Based Access Control

| Role   | Can do                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------- |
| admin  | All operations: manage users, configure thresholds, send questionnaires, export reports, delete data |
| editor | Submit data, send questionnaires, acknowledge alerts, generate reports                               |
| viewer | View dashboards, read reports, view evidence chains                                                  |

Enforced via `require_role(user, allowed_roles)` in `src/api/middleware/rbac.py`. Returns 403 "Insufficient permissions for this action" (no role name leaked in error).

## Organization Isolation

All data-scoping routes extract `org_id` from JWT via `require_auth` dependency. Client-supplied org_id is ignored. Every database query filters by the JWT's org_id. Cross-tenant data access is blocked at the query level.

## Auth Middleware

`require_auth` in `src/api/middleware/auth.py`:

1. Extracts `Authorization: Bearer <token>` header
2. Decodes JWT, validates signature and expiry
3. Returns user dict with `sub`, `org_id`, `email`, `role`
4. Raises 401 on missing/invalid/expired token

## Password Storage

bcrypt via `bcrypt.hashpw()` with `bcrypt.gensalt()`. Legacy SHA-256 hashes (`{salt}${hash}`) are transparently verified and migrated to bcrypt on login via `needs_rehash()` in `src/auth/password.py`.

## Security Measures

- Rate limiting on login/register (5 req/60s per IP)
- Generic error messages (no user enumeration, no role leakage)
- JWT minimum token length enforced (rejects tokens < 20 chars)
- CORS configured for frontend origin only
- No secrets in logs or error messages
- Parameterized queries throughout (no SQL injection)
