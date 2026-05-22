# A4 — Password Security Upgrade

**Date:** 2026-05-20
**Phase:** A / Data Foundation
**Status:** Complete

## What Was Built

### A4.1 bcrypt Password Hashing

- SHA-256 replaced with bcrypt in `src/auth/jwt.py`
- Migration for existing SHA-256 hashes (re-hash on next login)
- `needs_rehash()` function added per `src/auth/password.py:34`
- **Verification:** `grep "bcrypt\|hashpw\|needs_rehash" src/auth/password.py src/auth/jwt.py`

### A4.2 Auth Flows Updated

- Registration and login flows updated to use bcrypt
- All auth tests pass
- **Verification:** `grep "bcrypt\|hashpw" src/api/routes/auth.py`

### A4.3 Password Reset Flow

- `POST /api/auth/forgot-password` — generates time-limited token
- `POST /api/auth/reset-password` — validates token, updates password hash
- Requires SMTP env vars
- **Verification:** `grep "forgot.*password\|reset.*password" src/api/routes/auth.py`

### A4.4 JWT Token Invalidation

- `token_version` column added to users table
- Included in JWT payload
- Checked on decode
- Incremented on password change and user deactivation
- **Verification:** `grep "token_version" src/auth/jwt.py src/db/schema.sql`

### A4.5 Email Verification Flow

- `POST /api/auth/verify-email` endpoint
- Account stays in "pending" state until verified
- Unverified accounts cannot login
- **Verification:** `grep "verify.*email\|pending\|unverified" src/api/routes/auth.py`

### A4.6 User Invitation Backend

- `POST /api/auth/invite` — admin sends invite email, creates account with temporary password or magic link
- `POST /api/auth/accept-invite` — new user sets password
- Distinct from self-registration
- **Verification:** `grep "invite\|accept.*invite" src/api/routes/auth.py`

## Specs Implemented

- `specs/auth.md` § Password Storage
- `specs/auth.md` § Account Security
- `specs/auth.md` § RBAC
