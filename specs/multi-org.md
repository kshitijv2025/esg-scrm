# Multi-Org Specification

## Overview

Multi-organization user access with per-org role scoping. A user can belong to multiple organizations with a different role in each. Org context is carried in the JWT `org_id` claim. Switching orgs issues a new token with the target `org_id`.

## Endpoints

### `GET /api/orgs`

**Auth**: Required.

**Response** (200):

```json
{
  "orgs": [
    {
      "org_id": "org_bd_001",
      "name": "Bangladesh Export Textiles Ltd.",
      "industry": "Garment manufacturing",
      "country": "Bangladesh",
      "plan": "professional",
      "role": "admin",
      "is_primary": true,
      "joined_at": null,
      "created_at": "2026-01-15T08:00:00Z"
    },
    {
      "org_id": "org_vn_001",
      "name": "Vietnam Garment Co.",
      "industry": "Textile manufacturing",
      "country": "Vietnam",
      "plan": "starter",
      "role": "editor",
      "is_primary": false,
      "joined_at": "2026-03-01T10:00:00Z",
      "created_at": "2026-02-20T08:00:00Z"
    }
  ]
}
```

Implemented at `src/api/routes/orgs.py:51-134`. Returns user's primary org from `users.org_id` plus all orgs from `user_orgs` table, each with the user's role in that org.

---

### `POST /api/orgs/{org_id}/switch`

**Auth**: Required.

**Response** (200):

```json
{
  "token": "eyJ...",
  "org_id": "org_vn_001",
  "role": "editor"
}
```

**Errors**:

- 401: `Valid token required`
- 403: `You are not a member of this organization`
- 404: `Organization not found`

Implemented at `src/api/routes/orgs.py:137-201`. Issues a new JWT with the switched `org_id` claim. Role in the new token is resolved from `user_orgs.role` (if membership exists) or `users.role` (if switching to primary org).

---

### `GET /api/orgs/{org_id}/members`

**Auth**: Required. User must be a member of the org.

**Response** (200):

```json
{
  "org_id": "org_bd_001",
  "org_name": "Bangladesh Export Textiles Ltd.",
  "members": [
    {
      "user_id": "usr_admin_001",
      "email": "admin@factory.com",
      "full_name": "Admin User",
      "role": "admin",
      "is_primary": true,
      "joined_at": null,
      "invited_by": null,
      "last_login": "2026-05-20T08:00:00Z"
    }
  ]
}
```

Implemented at `src/api/routes/orgs.py:204-301`. Returns members from `user_orgs` joined with `users` (for orgs with `user_orgs` entries) and primary org users from `users` directly.

**Errors**:

- 401: `Valid token required`
- 403: `You are not a member of this organization`
- 404: `Organization not found`

---

### `POST /api/orgs/{org_id}/invite`

**Auth**: Required. Current user must be `admin` of the org.

**Request**:

```json
{
  "email": "newuser@factory.com",
  "full_name": "New User",
  "role": "viewer"
}
```

`role` must be one of: `admin`, `editor`, `viewer`.

**Response** (200):

```json
{
  "message": "Invitation sent to newuser@factory.com",
  "invite_token": "...",
  "user": {
    "id": "usr_abc123",
    "email": "newuser@factory.com",
    "full_name": "New User",
    "role": "viewer"
  }
}
```

**Errors**:

- 400: Invalid role value
- 401: `Valid token required`
- 403: `You are not a member of this organization` or `Only admins can invite users`
- 404: `Organization not found`
- 409: `A user with this email is already a member of this organization`

Implemented at `src/api/routes/orgs.py:304-411`. Creates a pending user with `is_active=0`, `email_verified=0`, stores `invite_token`. Role validated server-side via Pydantic `EmailStr` and `role` validator at lines 39-43.

---

### `DELETE /api/orgs/{org_id}/members/{target_user_id}`

**Auth**: Required. Current user must be `admin` of the org.

**Response** (200):

```json
{ "message": "User removed from organization" }
```

**Errors**:

- 400: `Cannot remove yourself from the organization` or `Cannot remove the last admin of the organization`
- 401: `Valid token required`
- 403: `You are not a member of this organization` or `Only admins can remove members`
- 404: `User is not a member of this organization` or `Organization not found`

Implemented at `src/api/routes/orgs.py:414-518`. Removes from `user_orgs` if membership exists; deactivates user (`is_active=0`) if target's primary org is this org. Cannot remove the last admin of an org.

## Role Resolution Logic

Role is resolved from (in priority order):

1. `user_orgs.role` if the user has a membership record for the org.
2. `users.role` if the target org is the user's primary org (via `users.org_id`).

This applies to: `switch_org`, `list_org_members`, `invite_org_user`, `remove_org_member`.

## Security Measures

- Admin-only endpoints check DB role, not JWT role (JWT role can be spoofed; DB role is authoritative).
- Cannot invite a user already a member of the org (409).
- Cannot remove the last admin of an org.
- Cannot remove yourself.
- Invited users are `is_active=0` with unusable password hash until they accept the invite.

## Data Model

| Table           | Key Columns                                                                |
| --------------- | -------------------------------------------------------------------------- |
| `users`         | `id`, `org_id` (primary org), `email`, `role`, `is_active`, `invite_token` |
| `user_orgs`     | `user_id`, `org_id`, `role`, `is_primary`, `joined_at`, `invited_by`       |
| `organizations` | `id`, `name`, `industry`, `country`, `plan`                                |
