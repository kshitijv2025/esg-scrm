"""
Audit logging middleware for FastAPI.

Intercepts POST, PUT, DELETE requests and logs them to the audit_log table.

Usage:
    from src.api.middleware.audit import AuditMiddleware

    app.add_middleware(AuditMiddleware)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.db.database import get_connection, release_connection

logger = logging.getLogger(__name__)

# HTTP methods to audit
AUDITED_METHODS = {"POST", "PUT", "DELETE"}

# Fields to exclude from audit logs (secrets, sensitive data)
REDACTED_FIELDS = {
    "password",
    "password_hash",
    "token",
    "token_version",
    "reset_token",
    "reset_token_expires",
    "email_verify_token",
    "invite_token",
    "portal_token",
    "api_key",
    "api_key_hash",
    "key_hash",
    "secret",
    "authorization",
    "cookie",
}

# Compiled pattern for extracting resource type and ID from paths
# Matches: /api/suppliers/123 -> ("suppliers", "123")
PATH_RESOURCE_PATTERN = re.compile(r"^/api/([^/]+)(?:/([^/]+))?")


def _redact_body(body: dict) -> dict:
    """Return a copy of body with sensitive fields redacted."""
    if not isinstance(body, dict):
        return body
    redacted = {}
    for key, value in body.items():
        if key.lower() in REDACTED_FIELDS:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _redact_body(value)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            redacted[key] = [
                _redact_body(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            redacted[key] = value
    return redacted


def _extract_resource_from_path(path: str) -> tuple[str, str]:
    """Extract resource_type and resource_id from request path.

    Examples:
        /api/suppliers -> ("suppliers", "")
        /api/suppliers/123 -> ("suppliers", "123")
        /api/templates/1/questions -> ("templates", "1")
        /api/users/user-abc -> ("users", "user-abc")
    """
    match = PATH_RESOURCE_PATTERN.match(path)
    if match:
        resource_type = match.group(1)
        resource_id = match.group(2) or ""
        return resource_type, resource_id
    return "unknown", ""


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request, handling proxies."""
    # Check X-Forwarded-For header first (behind proxy/load balancer)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    # Check X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    return ""


def _read_request_body(request: Request) -> Optional[dict]:
    """Read and parse JSON request body, returning None if not JSON."""
    try:
        body = request.body()
        if body:
            return json.loads(body)
    except (json.JSONDecodeError, Exception):
        logging.getLogger("audit.middleware").debug("audit.body.parse.error", exc_info=True)
    return None


async def _log_audit(
    org_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    changes_json: str,
    ip_address: str,
) -> None:
    """Insert audit log entry into the database."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log
                (org_id, user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (org_id, user_id, action, resource_type, resource_id, changes_json, ip_address),
        )
        conn.commit()
    except Exception as e:
        logger.error("audit_log insert failed: %s", e)
    finally:
        if conn:
            release_connection(conn)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs POST, PUT, DELETE requests to audit_log table.

    Requires authentication — requests without valid JWT are not audited
    (they will fail authentication before reaching protected routes).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only audit POST, PUT, DELETE
        if request.method not in AUDITED_METHODS:
            return await call_next(request)

        # Extract path
        path = request.url.path

        # Skip auth routes (login, register, etc.) and health checks
        if path.startswith("/api/auth") or path in ("/api/health", "/ws/alerts"):
            return await call_next(request)

        # Get request body for POST/PUT
        body_dict = None
        if request.method in ("POST", "PUT"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_dict = json.loads(body_bytes)
                    # Re-create the request body for downstream handlers
                    # Starlette's request.body() can only be read once, so we need
                    # to reconstruct it. We use a shared approach via request.state.
                    request.state._audit_body = body_bytes
            except (json.JSONDecodeError, Exception):
                pass

        # Call the actual route handler
        response = await call_next(request)

        # Only log successful writes (2xx status codes)
        # Skip if response indicates authentication failure
        if response.status_code >= 400 and response.status_code < 500:
            # Don't log 4xx client errors (except 401/403 which indicate auth issues)
            if response.status_code in (401, 403):
                return response
            # Log other 4xx (bad request, validation errors) as they may indicate issues
            pass
        elif response.status_code >= 500:
            # Don't log server errors in audit
            return response

        # Try to get user info from request state (set by require_auth dependency)
        # The require_auth dependency stores user info in request.state if auth succeeds
        user = getattr(request.state, "user", None)
        if user is None:
            # Try to get from request extensions (set by auth middleware)
            auth_context = request.state.__dict__ if hasattr(request.state, "__dict__") else {}
            user = auth_context.get("user")

        if user is None:
            # Cannot audit without user context - this shouldn't happen for protected routes
            return response

        org_id = user.get("org_id", "unknown")
        user_id = user.get("sub", "unknown")
        action = request.method  # POST, PUT, DELETE

        resource_type, resource_id = _extract_resource_from_path(path)

        # Prepare changes JSON (redacted)
        changes = {"body": _redact_body(body_dict)} if body_dict else None
        changes_json = json.dumps(changes) if changes else ""

        ip_address = _get_client_ip(request)

        # Log asynchronously to not block the response
        try:
            # Use asyncio.create_task if available, otherwise log synchronously
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    _log_audit(
                        org_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        changes_json,
                        ip_address,
                    )
                )
            except RuntimeError:
                # No running loop, log synchronously
                _log_audit(
                    org_id, user_id, action, resource_type, resource_id, changes_json, ip_address
                )
        except Exception as e:
            logger.error("audit logging failed: %s", e)

        return response
