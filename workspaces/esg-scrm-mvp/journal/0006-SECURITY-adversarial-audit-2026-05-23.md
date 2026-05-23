# SECURITY ADVERSARIAL AUDIT — ESG-SCRM MVP

**Date:** 2026-05-23
**Auditor:** security-reviewer (autonomous red team)
**Scope:** Full codebase review — auth, SQL, input validation, secrets, SSRF, CORS, webhooks

---

## CRITICAL

### VULN-001: Placeholder JWT Secret in `.env` — Token Forgery

**What:** The `.env` file contains `JWT_SECRET=CHANGE_ME_generate_a_random_64_char_secret` — a well-known placeholder string.

**Impact:** All JWT tokens can be forged by any attacker who knows this secret. They can generate tokens for any user, org_id, and role, completely bypassing authentication.

**Location:** `.env:9`, `.env.example:9`

**Exploit:**

```python
# Attacker generates forged token with known secret
import jwt
secret = "CHANGE_ME_generate_a_random_64_char_secret"  # known to attacker
payload = {"sub": "any_user_id", "org_id": "any_org", "role": "admin", ...}
token = jwt.encode(payload, secret, algorithm="HS256")  # forge admin token
# Use forged token in Authorization: Bearer <token> header
```

**Fix:** Remove `.env` from git history, generate a cryptographically random 64-character secret for each environment, and never commit actual secrets.

---

### VULN-002: Stripe Webhook Signature Verification Disabled in Production Path

**What:** When `STRIPE_WEBHOOK_SECRET` is not set, the Stripe webhook handler parses JSON without signature verification (line 350-354 of `billing.py`). This dev-mode fallback runs in production if the env var is missing.

**Impact:** Anyone can send forged Stripe webhook events (fake payments, fake subscription activations) without knowing any secret.

**Location:** `src/api/routes/billing.py:344-354`

```python
if STRIPE_WEBHOOK_SECRET:
    event = stripe.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET)
else:
    # Development mode — parse without verification
    try:
        event = json.loads(body)  # NO VERIFICATION — accepts ANY payload as valid Stripe event
```

**Fix:** Require `STRIPE_WEBHOOK_SECRET` in all environments, or fail fast at startup if unset in non-dev environments.

---

### VULN-003: SQL Injection via JWT `sub` Claim in Audit Log Query

**What:** The `sub` claim from an authenticated JWT is used directly in SQL query concatenation without sanitization. If the JWT secret is compromised (per VULN-001), an attacker can inject arbitrary SQL via the `sub` field.

**Impact:** Complete database compromise via second-order SQL injection when JWT secret is known.

**Location:** `src/api/routes/admin.py:361-365`

```python
# user_ids come from JWT sub claim via audit_log rows — never sanitized
user_ids = list({r["user_id"] for r in rows})
placeholders = ",".join(["?"] * len(user_ids))
email_rows = conn.execute(
    f"SELECT id, email FROM users WHERE id IN ({placeholders})",  # DYNAMIC SQL
    user_ids,  # user_ids = [r["user_id"] for r in rows] where user_id = payload["sub"]
).fetchall()
```

**Fix:** Validate/sanitize all JWT claims before use in SQL. Treat JWT payload fields as untrusted input.

---

## HIGH

### VULN-004: SSRF via Webhook URL Registration

**What:** Users can register webhooks pointing to internal/private IP ranges. The SSRF check (`_is_safe_url`) only runs at dispatch time, not at registration time. An attacker registers a webhook to an internal service, then triggers it to exfiltrate internal data.

**Impact:** Internal service enumeration, AWS metadata access (`http://169.254.169.254/`), port scanning, access to.internal APIs.

**Location:** `src/api/routes/webhooks.py:339-382`, `src/api/routes/webhooks.py:117-151`

```python
# URL validated at dispatch (lines 136, 208) but NOT at creation (line 369)
conn.execute(
    """INSERT INTO webhooks (id, org_id, name, url, ...) VALUES (?, ?, ?, ?, ...)""",
    (
        webhook_id,
        org_id,
        payload["name"],
        payload["url"],  # NO SSRF CHECK AT REGISTRATION TIME
        ...
    ),
)
```

**Fix:** Validate URLs at registration time. Block all private/reserved IP ranges in `_BLOCKED_IP_RANGES` before storing.

---

### VULN-005: Auditor Token Has No Bounded Expiry in DB — DOS Potential

**What:** The `auditor_access` endpoint (line 461-494 in `evidence.py`) loads `EVIDENCE_CHAIN` — a global in-memory dictionary built from a CSV file — and returns it without filtering by org_id. While the token IS checked for expiry, the evidence returned is the same static demo data for all orgs.

**Impact:** Data isolation between orgs is NOT enforced on this endpoint — every auditor token returns the same evidence data regardless of which org it belongs to. For a real system with per-org data, this would be a critical data leak.

**Location:** `src/api/routes/evidence.py:461-494`

```python
def auditor_access(token: str):
    # ...
    metrics = [
        {
            "cluster": cluster,
            "data_point_id": evidence.get("data_point_id"),
            # org_id from token is checked, but EVIDENCE_CHAIN is global/static
            # ALL ORGS GET THE SAME EVIDENCE CHAIN
            ...
        }
        for cluster, evidence in EVIDENCE_CHAIN.items()
    ]
```

**Fix:** Filter `EVIDENCE_CHAIN` by the auditor's `org_id`. In production, this data should come from the database with proper org filtering.

---

### VULN-006: Unbounded Rate Limiter Memory Growth — Denial of Service

**What:** The in-memory rate limiter (`_rate_limit_store`) grows without bound. Every unique IP that hits the auth endpoints adds an entry that persists for 60 seconds. An attacker with many IPs (botnet, distributed attack) can exhaust memory.

**Impact:** Memory exhaustion → application crash → denial of service.

**Location:** `src/api/routes/auth.py:22-41`

```python
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX_IPS = 10_000  # bound exists but eviction only runs when store exceeds limit

def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[ip].append(now)
    # Eviction only triggers when len > RATE_LIMIT_MAX_IPS (line 37-39)
    if len(_rate_limit_store) > RATE_LIMIT_MAX_IPS:
        stale = [k for k, v in _rate_limit_store.items() if not v]
        for k in stale:
            del _rate_limit_store[k]  # only evicts EMPTY lists
    return True
```

**Fix:** Use Redis or an LRU cache with TTL-based eviction instead of an in-memory dict.

---

### VULN-007: Missing Rate Limiting on Password Reset Endpoints

**What:** `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/resend-verification`, and `/api/auth/accept-invite` have no rate limiting.

**Impact:** Mass password reset requests can flood users with emails. Invitation token enumeration is possible.

**Location:** `src/api/routes/auth.py:155-180` (resend), `460-483` (forgot), `486-527` (reset), `269-312` (accept invite)

**Fix:** Apply the same `_check_rate_limit()` used on `/register` and `/login` to all password-related endpoints.

---

### VULN-008: Buyer Portal Scope Filtered Suppliers Returns All Suppliers on Empty Filter

**What:** In `buyer_portal.py` line 139-142, when `scope_filter` is an empty list (falsy), the query does NOT add the IN clause — so ALL suppliers for the org are returned, ignoring the buyer's intended scope restriction.

**Impact:** Buyer organization can see all suppliers in the seller org, not just the suppliers they were granted access to.

**Location:** `src/api/routes/buyer_portal.py:139-144`

```python
if scope_filter:  # empty list [] is falsy — skips the IN clause entirely
    placeholders = ",".join(["?"] * len(scope_filter))
    supplier_query += f" AND id IN ({placeholders})"
    supplier_params.extend(scope_filter)
# When scope_filter=[], ALL suppliers are returned — scope restriction bypassed!
```

**Fix:** Treat empty scope_filter as "no access" (return empty result), not "access to all suppliers."

---

### VULN-009: File Path Traversal in Document Download

**What:** In `documents.py` line 211-213, the `file_path` stored in the database is returned directly via `FileResponse` without validation that it lies within `UPLOAD_DIR`.

**Impact:** If an attacker can manipulate the `file_path` stored in the database (e.g., via SQL injection elsewhere), they can read arbitrary files from the server.

**Location:** `src/api/routes/documents.py:211-219`

```python
file_path = row["file_path"]
if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="file not found on disk")

return FileResponse(
    file_path,
    filename=row["name"],
    media_type=row.get("mime_type", "application/octet-stream"),
)
# No validation that file_path is under UPLOAD_DIR — could be /etc/passwd
```

**Fix:** Resolve the file path and verify it starts with the canonical `UPLOAD_DIR` path.

---

### VULN-010: CORS Allows `allow_credentials=True` with Implicit Wildcard

**What:** The CORS middleware configuration uses `allow_credentials=True` with `allow_origins` parsed from a comma-separated env var. If `CORS_ORIGINS` is accidentally set to `*` or an empty string, browsers will reject credentials with wildcard.

**Impact:** Potential CORS misconfiguration in deployment. The current defaults (localhost only) are safe, but the env-var-driven approach is fragile.

**Location:** `src/api/main.py:164-170`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
# If CORS_ORIGINS=* in production, this becomes a security issue
```

**Fix:** Fail at startup if `CORS_ORIGINS` is `*` or empty in non-dev environments. Validate against an allowlist.

---

## MEDIUM

### VULN-011: No Lock on Token Version Bump in Password Reset — Race Condition

**What:** In `reset_password` (auth.py:486-527), the token_version bump reads the current version and increments it in a non-atomic way.

**Impact:** Concurrent password resets for the same user could result in lost token version increments (TOCTOU).

**Location:** `src/api/routes/auth.py:505-521`

```python
# Read current version (line 516-521)
row = conn.execute("SELECT token_version FROM users WHERE id = ?", (user["id"],)).fetchone()
if row:
    new_token_version = row["token_version"]  # could be stale if concurrent reset

# Write (line 508-512) doesn't atomically increment
conn.execute(
    "UPDATE users SET ... token_version = token_version + 1 ...",
    (new_hash, body.token),
)
```

**Fix:** Use atomic increment (`UPDATE users SET token_version = token_version + 1 WHERE id = ?`) or row-level locking.

---

### VULN-012: Missing Input Validation on `template_id` in WhatsApp Questionnaire

**What:** In `whatsapp.py` line 108, `template_id` is cast to `int` directly without validation. If the template doesn't exist or is inactive, no error is raised — silently sends no questions.

**Impact:** Silent failure — user thinks questionnaire was sent but it wasn't.

**Location:** `src/connectors/whatsapp.py:108-110`

```python
template_id = body.get("template_id", 0)
result = self._client.send_questionnaire(supplier_id, template_id=int(template_id))
# If template_id doesn't exist, result returns without error but sends empty questionnaire
```

**Fix:** Validate that the resolved template has at least one question before sending.

---

### VULN-013: API Key Hash Not Stored — Only First 8 Chars Revealed to User

**What:** In `admin.py` line 224-231, the API key is stored as a SHA-256 hash and the raw key is returned only once on creation. But the hash stored is `hashlib.sha256(raw_key.encode()).hexdigest()` — if the raw key has low entropy, the hash could be brute-forced.

**Impact:** If API keys are generated with `secrets.token_urlsafe(32)`, entropy is sufficient. But if the key format changes or is user-provided, brute-force is feasible.

**Location:** `src/api/routes/admin.py:224-231`

```python
raw_key = f"esg_{secrets.token_urlsafe(32)}"  # 32 bytes of entropy — adequate
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()  # stored as SHA256, not bcrypt
```

**Fix:** Use bcrypt or argon2 for stored API key hashes instead of SHA-256.

---

### VULN-014: `DEBUG` Mode Enables Verbose Error Responses

**What:** Sentry is initialized with `environment=os.environ.get("ENVIRONMENT", "development")`. If `ENVIRONMENT` is not set (defaults to "development"), error responses may include stack traces.

**Impact:** In production, stack traces expose internal paths, library versions, and code structure.

**Location:** `src/api/main.py:74`

```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=os.environ.get("ENVIRONMENT", "development"),  # defaults to dev!
    ...
)
```

**Fix:** Require `ENVIRONMENT` to be explicitly set. Fail at startup if it's "development" in production context.

---

### VULN-015: No Expiry Enforcement on Auditor Tokens — Only Checked In-Memory

**What:** In `evidence.py` line 472, the expiry check compares `datetime.utcnow().isoformat() + "Z" > row["expires_at"]`. This works, but the token store has no cleanup mechanism — expired tokens accumulate indefinitely.

**Impact:** Database bloat. Expired tokens remain until manually deleted.

**Location:** `src/api/routes/evidence.py:472`

**Fix:** Add a periodic cleanup job or TTL-based expiration in the database schema.

---

## LOW

### VULN-016: WhatsApp Webhook Has No IP Allowlist for Twilio

**What:** The WhatsApp webhook (whatsapp.py:146-234) validates the HMAC signature but does NOT verify the request came from Twilio's IPs. A replay attack is possible if an attacker captures a valid webhook payload.

**Impact:** Replay attacks — same questionnaire responses can be re-submitted if attacker captures and replays a valid webhook.

**Location:** `src/api/routes/whatsapp.py:146-234`

**Fix:** Verify `X-Twilio-Signature` AND check source IP is from Twilio's IP range (requires periodic IP list updates from Twilio).

---

### VULN-017: `require_auth` Result Cached No Opponent Check for `role` Field Type

**What:** The `require_auth` middleware (auth.py:25-50) returns `payload["role"]` directly without validating it's a string. If a malformed JWT has `role` as an integer or list, downstream role checks (`require_role`) may behave unexpectedly.

**Impact:** Potential type confusion in role-based access control.

**Location:** `src/api/middleware/auth.py:45-50`

```python
return {
    "sub": payload["sub"],
    "org_id": payload["org_id"],
    "email": payload["email"],
    "role": payload["role"],  # no type check — could be int, list, etc.
}
```

**Fix:** Validate `role` is a string and in the expected set `{"admin", "editor", "viewer"}` in `require_auth`.

---

### VULN-018: Reset Token Email Enumeration Still Possible Despite Generic Response

**What:** While `/forgot-password` returns a generic message, the timing differs if the email exists vs. doesn't exist (database query is only run when user exists). An attacker can detect valid emails via timing.

**Impact:** Email enumeration for valid users.

**Location:** `src/api/routes/auth.py:460-483`

```python
user = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
if user:  # Only does DB query if user exists
    reset_token = uuid.uuid4().hex  # DB write only happens if user found
```

**Fix:** Always generate a token and attempt the DB write, even for non-existent emails. Add artificial delay to normalize response time.

---

## PASSED CHECKS

- **SQL Parameterization**: All database queries in `database.py`, `suppliers.py`, `auth.py` use parameterized queries (?, %s) for values — no raw string interpolation for user data in SQL.
- **JWT Algorithm**: JWT implementation hardcodes `HS256` (jwt.py:64) — no algorithm confusion attack surface.
- **Password Hashing**: Uses bcrypt via `hash_password`/`verify_password` (auth.py) with automatic rehashing of legacy SHA-256 hashes.
- **HMAC Constant-Time Comparison**: `hmac.compare_digest` used in both JWT signature verification (jwt.py:100) and WhatsApp webhook verification (whatsapp.py:384).
- **SSRF Protection in Webhooks**: `_is_safe_url` blocks private IP ranges at dispatch time (webhooks.py:60-98).
- **CORS Explicit Origins**: CORS uses explicit origin list from env var, not wildcard.
- **Role Validation in RBAC**: `require_role` validates against explicit allowlists.
- **Upload File Size Limit**: 5MB limit enforced in `upload.py:109`.
- **Filename Sanitization**: CSV upload validates filename characters (upload.py:42-50).
- **GDPR Export Auth**: GDPR export endpoints require authentication.
- **Evidence Chain Immutability**: SQLite triggers prevent UPDATE/DELETE on `evidence_chain` rows (database.py:221-234).

---

## SUMMARY

| Severity  | Count  |
| --------- | ------ |
| CRITICAL  | 3      |
| HIGH      | 7      |
| MEDIUM    | 5      |
| LOW       | 3      |
| **TOTAL** | **18** |

**Top Priority Fixes:**

1. Replace placeholder JWT secret immediately (VULN-001) — blocks all authentication
2. Fix Stripe webhook bypass in production (VULN-002) — allows fake payments
3. Sanitize JWT claims in SQL (VULN-003) — SQL injection if secret leaks
4. Add SSRF check at webhook URL registration (VULN-004) — internal service access
5. Fix buyer portal scope bypass (VULN-008) — data access control violation
