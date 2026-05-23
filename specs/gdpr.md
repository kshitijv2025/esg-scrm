# GDPR Specification

## Overview

GDPR data export and account deletion endpoints implementing Article 17 Right to Erasure and Article 20 Right to Data Portability. Export files expire after 7 days; deletion is soft (account deactivated, data retained 30 days before permanent removal).

## Endpoints

### `POST /api/gdpr/export`

**Auth**: Required (Bearer token).

**Response** (200):

```json
{
  "download_url": "/api/gdpr/export/{job_id}",
  "expires_at": "2026-05-28T10:00:00Z"
}
```

**Effect**: Creates `gdpr_export_jobs` row with `status=processing`, gathers user record, org record, last 90 days of `audit_log` entries, last 90 days of `notification_log` entries, writes JSON to `/tmp/gdpr_export_{job_id}.json`, updates job status to `ready`.

Export retention: 7 days (`EXPORT_RETENTION_DAYS = 7` at `src/api/routes/gdpr.py:15`).

Implemented at `src/api/routes/gdpr.py:28-123`.

---

### `GET /api/gdpr/export/{job_id}`

**Auth**: Required (Bearer token). Token's `sub` (user_id) must match the job's `user_id`.

**Response** (200): JSON export payload.

**Errors**:

- 401: `Valid token required`
- 403: `Access denied` — job belongs to a different user
- 404: `Export job not found` or `Export file not found`
- 410: `Export has expired`

Implemented at `src/api/routes/gdpr.py:126-168`.

---

### `DELETE /api/gdpr/account`

**Auth**: Required (Bearer token).

**Response** (200):

```json
{
  "message": "Account scheduled for deletion within 30 days",
  "deleted_at": "2026-05-21T10:00:00Z"
}
```

**Effect** (`src/api/routes/gdpr.py:171-220`):

1. Sets `users.is_active = 0`
2. Nulls `email` → `deleted_{user_id}@redacted.local`
3. Nulls `full_name` → `Deleted User`
4. Sets `password_hash` → `!DELETED`
5. Sets `email_verified = 0`, `last_login = NULL`

Deletion schedule: 30 days (`DELETION_SCHEDULE_DAYS = 30` at `src/api/routes/gdpr.py:16`).

**Errors**:

- 400: `Account already deleted`
- 401: `Valid token required`
- 404: `User not found`

## Data Gathered in Export

| Source             | Columns                                                                               | Retention    |
| ------------------ | ------------------------------------------------------------------------------------- | ------------ |
| `users`            | `id`, `org_id`, `email`, `full_name`, `role`, `is_active`, `last_login`, `created_at` | All time     |
| `organizations`    | `id`, `name`, `industry`, `country`, `plan`, `trial_end`                              | All time     |
| `audit_log`        | `id`, `action`, `resource_type`, `details`, `created_at`                              | Last 90 days |
| `notification_log` | `id`, `channel`, `recipient`, `subject`, `sent_at`, `status`                          | Last 90 days |

Audit log query at `src/api/routes/gdpr.py:71-76`: filters on `org_id`, `user_id`, and `created_at >= (now - 90 days)`, ordered descending, capped at 1000 rows.

Notification log query at `src/api/routes/gdpr.py:79-84`: same filters.

## Security Measures

- User can only download their own export (`job.user_id == token.sub`).
- Expired exports return 410 Gone.
- Deleted accounts use `deleted_{user_id}@redacted.local` to prevent email enumeration.
- PII fields nulled on soft-delete; data retained for 30-day legal window.

## Implementation Notes

- Export file written to `/tmp/gdpr_export_{job_id}.json` — actual ZIP creation is stubbed (returns JSON file directly).
- `gdpr_export_jobs` table tracks: `id`, `org_id`, `user_id`, `status`, `file_path`, `expires_at`, `created_at`.
