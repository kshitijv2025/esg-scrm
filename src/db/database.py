"""
Database manager supporting both SQLite (dev/test) and PostgreSQL (production).
Selected via DATABASE_URL env var:
  - Not set or sqlite:///... → SQLite (default)
  - postgresql://... → PostgreSQL

PostgreSQL mode uses a ThreadedConnectionPool for connection pooling.
Pool size is configurable via DB_POOL_SIZE env var (default 5, max 10).
"""

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

import dotenv

dotenv.load_dotenv()

DB_PATH = Path(__file__).parent / "esg_scrm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
SCHEMA_PG_PATH = Path(__file__).parent / "schema_pg.sql"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_is_postgres = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")
_initialized = False

_pg_pool = None

# Connection timestamps for recycling (connection object -> created-at timestamp)
_pg_conn_timestamps: dict = {}
_pg_conn_timestamps_lock = threading.Lock()

# Pool creation timestamp for periodic recycling
_pool_created_at: float = 0.0
_POOL_RECYCLE_SECONDS: int = 300  # 5 minutes


def _get_pool_size() -> int:
    """Read pool size from env, clamped to [1, 10]."""
    try:
        size = int(os.environ.get("DB_POOL_SIZE", "5"))
    except (ValueError, TypeError):
        size = 5
    return max(1, min(size, 10))


def is_postgres() -> bool:
    return _is_postgres


def _get_pg_pool():
    """Get or create the PostgreSQL connection pool."""
    global _pg_pool, _pool_created_at
    if _pg_pool is None or _pg_pool.closed:
        from psycopg2.pool import ThreadedConnectionPool

        size = _get_pool_size()
        _pg_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=size,
            dsn=DATABASE_URL,
        )
        _pool_created_at = time.monotonic()
    return _pg_pool


def _adapt_query(query: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL %s if needed."""
    if _is_postgres:
        return query.replace("?", "%s")
    return query


def _evict_stale_pg_connections() -> None:
    """Close and remove any pooled PG connections idle for more than _POOL_RECYCLE_SECONDS."""
    global _pg_pool, _pool_created_at
    if _pg_pool is None or _pg_pool.closed:
        return
    cutoff = time.monotonic() - _POOL_RECYCLE_SECONDS
    # Periodically refresh the entire pool as a safety net
    if _pool_created_at > 0 and time.monotonic() - _pool_created_at > _POOL_RECYCLE_SECONDS * 3:
        # Pool is too old — force full refresh
        _close_pool()
        _get_pg_pool()
        return
    with _pg_conn_timestamps_lock:
        stale = [conn for conn, ts in list(_pg_conn_timestamps.items()) if ts < cutoff]
    for conn in stale:
        try:
            with _pg_conn_timestamps_lock:
                _pg_conn_timestamps.pop(conn, None)
            _pg_pool.putconn(conn, close=True)
        except Exception as e:
            logging.getLogger("db").warning("db.connection.evict.error", error=str(e))


def get_connection(row_factory: bool = True):
    """Get a database connection. Returns sqlite3.Connection or psycopg2 connection.

    For PostgreSQL, the connection is acquired from the pool. The caller MUST
    call release_connection() when done to return it to the pool.
    Stale connections (idle >300s) are evicted before being returned.
    For SQLite, a new connection is created each call and should be closed by the caller.
    """
    _ensure_db()
    if _is_postgres:
        _evict_stale_pg_connections()
        pool = _get_pg_pool()
        conn = pool.getconn()
        conn.autocommit = True
        # Track creation timestamp for recycling
        with _pg_conn_timestamps_lock:
            _pg_conn_timestamps[conn] = time.monotonic()
        return conn
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def release_connection(conn) -> None:
    """Return a connection to the pool (PostgreSQL) or close it (SQLite).

    Safe to call with None — does nothing.
    """
    if conn is None:
        return
    if _is_postgres:
        # Update timestamp so next get_connection() can check age
        with _pg_conn_timestamps_lock:
            _pg_conn_timestamps[conn] = time.monotonic()
        pool = _get_pg_pool()
        pool.putconn(conn)
    else:
        try:
            conn.close()
        except Exception:
            pass


def _close_pool():
    """Close all pooled PostgreSQL connections and destroy the pool."""
    global _pg_pool
    if _pg_pool is not None and not _pg_pool.closed:
        _pg_pool.closeall()
        _pg_pool = None
    with _pg_conn_timestamps_lock:
        _pg_conn_timestamps.clear()


def _migrate_sqlite() -> None:
    """Apply schema migrations to an existing SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Add plan column to organizations table
        org_cols = {r[1] for r in conn.execute("PRAGMA table_info(organizations)").fetchall()}
        if "plan" not in org_cols:
            conn.execute(
                "ALTER TABLE organizations ADD COLUMN plan TEXT NOT NULL DEFAULT 'starter'"
            )
        if "trial_end" not in org_cols:
            conn.execute("ALTER TABLE organizations ADD COLUMN trial_end TEXT")

        # Check existing columns in users table
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "token_version" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1")
        if "reset_token" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        if "reset_token_expires" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token_expires TEXT")
        if "email_verified" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        if "email_verify_token" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verify_token TEXT")
        if "invited_by" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN invited_by TEXT")
        if "invite_token" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN invite_token TEXT")
        # Add production_volume column to metrics table
        metric_cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}
        if "production_volume" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN production_volume REAL")
        # Add renewable_kwh column to metrics table
        if "renewable_kwh" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN renewable_kwh REAL")
        # Add wastewater_discharge column to metrics table
        if "wastewater_discharge" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN wastewater_discharge REAL")
        # Add water_stress_level column to metrics table
        if "water_stress_level" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN water_stress_level TEXT")
        # Create rec_certificates table if it does not exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rec_certificates (
                id TEXT PRIMARY KEY,
                org_id TEXT,
                source TEXT NOT NULL,
                kwh_certified REAL NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                certificate_url TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Existing users created before email verification are considered verified
        if "email_verified" in cols:
            conn.execute(
                "UPDATE users SET email_verified = 1 WHERE email_verified = 0 AND email_verify_token IS NULL"
            )

        # C3.8: Immutability triggers on evidence_chain — prevent UPDATE/DELETE
        # Triggers are created IF NOT EXISTS so this is idempotent
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS evidence_chain_no_update
            BEFORE UPDATE ON evidence_chain
            BEGIN
                SELECT RAISE(ABORT, 'evidence_chain rows are immutable');
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS evidence_chain_no_delete
            BEFORE DELETE ON evidence_chain
            BEGIN
                SELECT RAISE(ABORT, 'evidence_chain rows are immutable');
            END
        """)

        # C3.9: Add retention_period_months to organizations (default 84 = 7 years)
        org_cols = {r[1] for r in conn.execute("PRAGMA table_info(organizations)").fetchall()}
        if "retention_period_months" not in org_cols:
            conn.execute(
                "ALTER TABLE organizations ADD COLUMN retention_period_months INTEGER NOT NULL DEFAULT 84"
            )

        # C3.9: Add archived_at to evidence_chain and audit_log for soft-delete
        ec_cols = {r[1] for r in conn.execute("PRAGMA table_info(evidence_chain)").fetchall()}
        if "archived_at" not in ec_cols:
            conn.execute("ALTER TABLE evidence_chain ADD COLUMN archived_at TEXT")
        al_cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
        if "archived_at" not in al_cols:
            conn.execute("ALTER TABLE audit_log ADD COLUMN archived_at TEXT")

        # C3.9: Create archive tables if they don't exist (idempotent)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_chain_archive (
                id INTEGER PRIMARY KEY,
                metric_id INTEGER NOT NULL,
                org_id TEXT NOT NULL DEFAULT '',
                cluster TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE,
                prev_hash TEXT,
                value REAL NOT NULL,
                raw_value REAL,
                calculated_value REAL,
                emission_factor_id INTEGER,
                methodology TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                computed_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                recorded_by TEXT NOT NULL DEFAULT '',
                source_system TEXT NOT NULL DEFAULT 'manual',
                parent_id INTEGER,
                archived_at TEXT NOT NULL,
                archive_reason TEXT NOT NULL DEFAULT 'retention'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log_archive (
                id INTEGER PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                ip_address TEXT NOT NULL DEFAULT '',
                archived_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                archive_reason TEXT NOT NULL DEFAULT 'retention'
            )
        """)

        # Notification log table for tracking outbound notifications
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT NOT NULL,
                user_id TEXT,
                channel TEXT NOT NULL,
                subject TEXT,
                body_preview TEXT,
                recipient TEXT,
                status TEXT NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Billing: subscriptions table for plan/subscription tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                stripe_customer_id TEXT NOT NULL DEFAULT '',
                stripe_subscription_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'inactive',
                plan_id TEXT NOT NULL DEFAULT 'starter',
                current_period_start TEXT,
                current_period_end TEXT,
                trial_end TEXT,
                cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Migrate existing subscriptions table with missing columns BEFORE creating indexes
        sub_cols = {r[1] for r in conn.execute("PRAGMA table_info(subscriptions)").fetchall()}
        if "stripe_customer_id" not in sub_cols:
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN stripe_customer_id TEXT NOT NULL DEFAULT ''"
            )
        if "stripe_subscription_id" not in sub_cols:
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN stripe_subscription_id TEXT NOT NULL DEFAULT ''"
            )
        if "current_period_start" not in sub_cols:
            conn.execute("ALTER TABLE subscriptions ADD COLUMN current_period_start TEXT")
        if "cancel_at_period_end" not in sub_cols:
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN cancel_at_period_end INTEGER NOT NULL DEFAULT 0"
            )
        if "updated_at" not in sub_cols:
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_org ON subscriptions(org_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id)"
        )

        # D1.5: Add resolved_at column to risk_flags for alert history tracking
        rf_cols = {r[1] for r in conn.execute("PRAGMA table_info(risk_flags)").fetchall()}
        if "resolved_at" not in rf_cols:
            conn.execute("ALTER TABLE risk_flags ADD COLUMN resolved_at TEXT")

        # Phase D: Add corrective_actions table if it doesn't exist
        existing_tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "corrective_actions" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS corrective_actions (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    supplier_id TEXT,
                    flag_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled')),
                    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                    assigned_to TEXT,
                    deadline TEXT,
                    completed_at TEXT,
                    completed_by TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_corrective_actions_org ON corrective_actions(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_corrective_actions_supplier ON corrective_actions(supplier_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_corrective_actions_status ON corrective_actions(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_corrective_actions_deadline ON corrective_actions(deadline)"
            )

        # Phase D: Add documents table if it doesn't exist
        if "documents" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    supplier_id TEXT,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    category TEXT NOT NULL DEFAULT 'certificate' CHECK (category IN ('certificate', 'audit_report', 'compliance', 'contract', 'other')),
                    expiry_date TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_by TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_org ON documents(org_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_supplier ON documents(supplier_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date)"
            )

        # Buyer portal access table
        if "buyer_portal_access" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS buyer_portal_access (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    buyer_org_id TEXT NOT NULL DEFAULT '',
                    buyer_org_name TEXT NOT NULL DEFAULT '',
                    scope_filter TEXT NOT NULL DEFAULT '{}',
                    token TEXT NOT NULL UNIQUE,
                    token_expires TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_buyer_portal_token ON buyer_portal_access(token)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_buyer_portal_org ON buyer_portal_access(org_id)"
            )

        # ML weight changes audit table
        if "weight_changes" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weight_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    old_weights_json TEXT NOT NULL,
                    new_weights_json TEXT NOT NULL,
                    feedback_count INTEGER NOT NULL,
                    changed_by TEXT NOT NULL,
                    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_weight_changes_org ON weight_changes(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_weight_changes_user ON weight_changes(user_id)"
            )

        # GDPR export jobs table
        if "gdpr_export_jobs" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gdpr_export_jobs (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processing',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    file_path TEXT,
                    expires_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gdpr_jobs_org ON gdpr_export_jobs(org_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_gdpr_jobs_user ON gdpr_export_jobs(user_id)"
            )

        # Notification log table
        if "notification_log" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'email',
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
                    status TEXT NOT NULL DEFAULT 'sent'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_org ON notification_log(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_user ON notification_log(user_id)"
            )

        # Phase D: Compliance calendar deadlines
        if "compliance_deadlines" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_deadlines (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    deadline TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'upcoming',
                    submission_date TEXT,
                    evidence_required INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_org ON compliance_deadlines(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_deadline ON compliance_deadlines(deadline)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_framework ON compliance_deadlines(framework)"
            )

        # Country risk scores
        if "country_risk_scores" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS country_risk_scores (
                    country_code TEXT PRIMARY KEY,
                    country_name TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    source TEXT NOT NULL DEFAULT 'Kailash Internal'
                )
            """)

        # User-organization join table for multi-org membership
        if "user_orgs" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_orgs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_orgs_user ON user_orgs(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_orgs_org ON user_orgs(org_id)")

        # Phase D: Scheduled report jobs
        if "scheduled_reports" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_reports (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    report_type TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    next_run TEXT,
                    last_run TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    recipients TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_by TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_reports_org ON scheduled_reports(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next_run ON scheduled_reports(next_run)"
            )

        # Phase D: Webhook registrations
        if "webhooks" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    events TEXT NOT NULL DEFAULT '[]',
                    secret TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_triggered TEXT,
                    last_status INTEGER,
                    last_response TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_by TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_org ON webhooks(org_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_events ON webhooks(events)")

        # Auditor token store for time-limited auditor access links
        if "auditor_tokens" not in existing_tables:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auditor_tokens (
                    token TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'read_only',
                    expires_at TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_auditor_tokens_org ON auditor_tokens(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_auditor_tokens_expires ON auditor_tokens(expires_at)"
            )

        conn.commit()
    finally:
        conn.close()


def _ensure_db() -> None:
    """Initialize database from schema if needed."""
    global _initialized
    if _initialized:
        return
    if _is_postgres:
        conn = _get_pg_pool().getconn()
        try:
            conn.autocommit = True
            schema = SCHEMA_PG_PATH.read_text()
            cur = conn.cursor()
            cur.execute(schema)
            cur.close()
        finally:
            _get_pg_pool().putconn(conn)
    else:
        if not DB_PATH.exists():
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA_PATH.read_text())
            conn.close()
        else:
            # Verify critical tables exist; if not, re-initialize from schema
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                existing_tables = {
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if "users" not in existing_tables or "factories" not in existing_tables:
                    conn.close()
                    conn = sqlite3.connect(DB_PATH)
                    conn.executescript(SCHEMA_PATH.read_text())
                    conn.close()
                else:
                    _migrate_sqlite()
            finally:
                conn.close()
    # C3.9: Enforce retention policy on startup — archive old records, no hard delete
    # Uses _run_retention_policy() to avoid re-entering _ensure_db() via get_connection()
    try:
        _run_retention_policy()
    except Exception:
        # Retention policy failure is non-fatal — log but don't block startup
        import logging

        logging.getLogger("database").warning(
            "Retention policy enforcement failed; will retry on next startup"
        )
    _initialized = True


def reset_database() -> None:
    """Reset database. Drops all data and recreates schema."""
    global _initialized
    if _is_postgres:
        conn = get_connection()
        try:
            conn.autocommit = True
            cur = conn.cursor()
            tables = [
                "whatsapp_messages",
                "audit_log",
                "questionnaire_questions",
                "questionnaire_templates",
                "alert_thresholds",
                "framework_mappings",
                "emission_factors",
                "questionnaire_responses",
                "supplier_scope3",
                "api_keys",
                "risk_flags",
                "evidence_chain",
                "rec_certificates",
                "metrics",
                "suppliers",
                "factories",
                "users",
                "organizations",
                "auditor_tokens",
            ]
            for t in tables:
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
            cur.close()
        finally:
            release_connection(conn)
        _initialized = False
        _ensure_db()
    else:
        for suffix in ("", "-wal", "-shm", "-journal"):
            p = DB_PATH.parent / f"{DB_PATH.name}{suffix}"
            if p.exists():
                p.unlink()
        _initialized = False
        _ensure_db()
        _initialized = False
        _ensure_db()


def _dict_from_row(row) -> dict:
    """Convert a row to dict regardless of DB type."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return dict(row)
    try:
        return dict(row)
    except (TypeError, ValueError):
        return row


def _fetchone(conn, query: str, params: tuple = ()) -> Optional[dict]:
    """Execute query and return one row as dict."""
    q = _adapt_query(query)
    cur = conn.cursor()
    cur.execute(q, params)
    row = cur.fetchone()
    if not _is_postgres:
        cur.close()
    if row is None:
        return None
    if _is_postgres:
        desc = cur.description
        cur.close()
        return dict(zip([d[0] for d in desc], row))
    return _dict_from_row(row)


def _fetchall(conn, query: str, params: tuple = ()) -> list[dict]:
    """Execute query and return all rows as dicts."""
    q = _adapt_query(query)
    cur = conn.cursor()
    cur.execute(q, params)
    rows = cur.fetchall()
    if _is_postgres:
        desc = cur.description
        cur.close()
        if desc:
            cols = [d[0] for d in desc]
            return [dict(zip(cols, r)) for r in rows]
        return []
    cur.close()
    return [_dict_from_row(r) for r in rows]


def _execute(conn, query: str, params: tuple = ()):
    """Execute a write query."""
    q = _adapt_query(query)
    cur = conn.cursor()
    cur.execute(q, params)
    if _is_postgres:
        conn.commit()
    else:
        conn.commit()
    return cur


# --- Query helpers for routes ---


def fetch_metrics(factory_id: str = "factory_bd_001", org_id: str = "") -> list[dict[str, Any]]:
    """Latest metric per cluster with evidence chain hashes."""
    conn = get_connection()
    try:
        org_filter = "AND m.org_id = ?" if org_id else ""
        params: list[Any] = [factory_id]
        if org_id:
            params.append(org_id)
        return _fetchall(
            conn,
            f"""
            SELECT m.id, m.cluster, m.value, m.unit, m.confidence, m.source,
                   m.period, m.recorded_at, e.hash, e.prev_hash
            FROM metrics m
            LEFT JOIN evidence_chain e ON m.id = e.metric_id
            WHERE m.factory_id = ? {org_filter}
            AND m.recorded_at = (
                SELECT MAX(m2.recorded_at) FROM metrics m2
                WHERE m2.cluster = m.cluster AND m2.factory_id = m.factory_id
            )
            ORDER BY m.cluster
        """,
            tuple(params),
        )
    finally:
        release_connection(conn)


def fetch_metric_metadata() -> dict[str, dict[str, Any]]:
    """Fetch all metric metadata rows, keyed by cluster."""
    conn = get_connection()
    try:
        rows = _fetchall(conn, "SELECT * FROM metric_metadata", ())
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            result[row["cluster"]] = row
        return result
    finally:
        release_connection(conn)


def fetch_intensity_data(org_id: str) -> dict[str, Any]:
    """Fetch latest energy, emissions, and production_volume for intensity calculation."""
    conn = get_connection()
    try:
        energy_row = _fetchone(
            conn,
            """
            SELECT value, production_volume, period FROM metrics
            WHERE org_id = ? AND cluster = 'energy_kwh'
            ORDER BY recorded_at DESC LIMIT 1
        """,
            (org_id,),
        )
        emissions_row = _fetchone(
            conn,
            """
            SELECT value, production_volume, period FROM metrics
            WHERE org_id = ? AND cluster = 'emissions_tco2'
            ORDER BY recorded_at DESC LIMIT 1
        """,
            (org_id,),
        )
        return {
            "energy_kwh": energy_row["value"] if energy_row else 0,
            "emissions_tco2": emissions_row["value"] if emissions_row else 0,
            "production_volume": (energy_row or {}).get("production_volume") or 0,
            "period": (energy_row or {}).get("period", ""),
        }
    finally:
        release_connection(conn)


def fetch_renewable_data(org_id: str) -> dict[str, Any]:
    """Fetch total energy, renewable energy, and REC certificates for renewable tracking."""
    conn = get_connection()
    try:
        energy_row = _fetchone(
            conn,
            """
            SELECT value, renewable_kwh, period FROM metrics
            WHERE org_id = ? AND cluster = 'energy_kwh'
            ORDER BY recorded_at DESC LIMIT 1
        """,
            (org_id,),
        )
        rec_certs = _fetchall(
            conn,
            """
            SELECT id, source, kwh_certified, period_start, period_end, certificate_url
            FROM rec_certificates
            WHERE org_id = ?
            ORDER BY period_start DESC
        """,
            (org_id,),
        )

        total_kwh = energy_row["value"] if energy_row else 0
        renewable_kwh = (energy_row or {}).get("renewable_kwh") or 0

        renewable_pct = round(renewable_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0

        return {
            "total_kwh": total_kwh,
            "renewable_kwh": renewable_kwh,
            "renewable_percentage": renewable_pct,
            "rec_certificates": [
                {
                    "id": c["id"],
                    "source": c["source"],
                    "kwh_certified": c["kwh_certified"],
                    "period_start": c["period_start"],
                    "period_end": c["period_end"],
                    "certificate_url": c["certificate_url"],
                }
                for c in rec_certs
            ],
            "period": (energy_row or {}).get("period", ""),
        }
    finally:
        release_connection(conn)


def fetch_trends(
    cluster: str, factory_id: str = "factory_bd_001", org_id: str = ""
) -> list[dict[str, Any]]:
    """Time series for a specific metric cluster."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(
                conn,
                """
                SELECT recorded_at, value FROM metrics
                WHERE org_id = ? AND cluster = ?
                ORDER BY recorded_at
            """,
                (org_id, cluster),
            )
        return _fetchall(
            conn,
            """
            SELECT recorded_at, value FROM metrics
            WHERE factory_id = ? AND cluster = ?
            ORDER BY recorded_at
        """,
            (factory_id, cluster),
        )
    finally:
        release_connection(conn)


def fetch_all_trends(factory_id: str = "factory_bd_001", org_id: str = "") -> list[dict[str, Any]]:
    """Combined trends for energy, emissions, water, waste, and incident_rate."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(
                conn,
                """
                SELECT recorded_at, cluster, value FROM metrics
                WHERE org_id = ? AND cluster IN ('energy_kwh', 'emissions_tco2', 'water_m3', 'waste_kg', 'incident_rate')
                ORDER BY recorded_at
            """,
                (org_id,),
            )
        return _fetchall(
            conn,
            """
            SELECT recorded_at, cluster, value FROM metrics
            WHERE factory_id = ? AND cluster IN ('energy_kwh', 'emissions_tco2', 'water_m3', 'waste_kg', 'incident_rate')
            ORDER BY recorded_at
        """,
            (factory_id,),
        )
    finally:
        release_connection(conn)


def fetch_risk_flags(
    cluster: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    org_id: str = "",
    factory_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Risk flags with optional filters, sorted by priority descending.

    Args:
        cluster: filter by metric cluster.
        severity: filter by severity level.
        acknowledged: if True, resolved alerts; if False, active alerts; if None, all.
        skip/limit: pagination cursor.
        org_id: org scope (recommended — use instead of factory_id when possible).
        factory_id: optional factory scope; if None, queries across all factories for the org.
    """
    conn = get_connection()
    try:
        conditions = []
        params: list[Any] = []

        if factory_id is not None:
            conditions.append("factory_id = ?")
            params.append(factory_id)
        if org_id:
            conditions.append("org_id = ?")
            params.append(org_id)
        if cluster is not None:
            conditions.append("cluster = ?")
            params.append(cluster)
        if severity is not None:
            conditions.append("severity = ?")
            params.append(severity)
        if acknowledged is not None:
            conditions.append("acknowledged = ?")
            params.append(int(acknowledged))

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM risk_flags WHERE {where_clause} ORDER BY priority_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        return _fetchall(conn, query, tuple(params))
    finally:
        release_connection(conn)


def acknowledge_risk_flag(
    flag_id: str, acknowledged_by: str, org_id: str = ""
) -> Optional[dict[str, Any]]:
    """Acknowledge a risk flag. Returns the updated flag or None."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        if org_id:
            cur = _execute(
                conn,
                """
                UPDATE risk_flags SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
                WHERE id = ? AND org_id = ?
            """,
                (now, acknowledged_by, flag_id, org_id),
            )
        else:
            cur = _execute(
                conn,
                """
                UPDATE risk_flags SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ? WHERE id = ?
            """,
                (now, acknowledged_by, flag_id),
            )
        if _is_postgres:
            rowcount = cur.rowcount
        else:
            rowcount = cur.rowcount
        if rowcount == 0:
            return None
        return _fetchone(conn, "SELECT * FROM risk_flags WHERE id = ?", (flag_id,))
    finally:
        release_connection(conn)


def fetch_recent_matching_flag(
    org_id: str,
    cluster: str,
    lookback_hours: int = 24,
) -> Optional[dict[str, Any]]:
    """Fetch the most recent unacknowledged risk flag matching org_id + cluster.

    Returns the flag dict, or None if no unacknowledged flag exists within
    the lookback window.
    """
    conn = get_connection()
    try:
        if _is_postgres:
            query = """
                SELECT * FROM risk_flags
                WHERE org_id = %s AND cluster = %s
                  AND created_at >= NOW() - INTERVAL '1 hour' * %s
                  AND acknowledged_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            """
        else:
            query = """
                SELECT * FROM risk_flags
                WHERE org_id = ? AND cluster = ?
                  AND created_at >= datetime('now', '-' || ? || ' hours')
                  AND acknowledged_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            """
        return _fetchone(conn, query, (org_id, cluster, lookback_hours))
    finally:
        release_connection(conn)


def should_suppress_flag(
    org_id: str,
    cluster: str,
    lookback_hours: int = 24,
) -> bool:
    """Return True if an unacknowledged flag for this org_id + cluster exists
    within the lookback window (duplicate suppression).
    """
    return fetch_recent_matching_flag(org_id, cluster, lookback_hours) is not None


def fetch_suppliers(skip: int = 0, limit: int = 100, org_id: str = "") -> list[dict[str, Any]]:
    """All suppliers with pagination."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(
                conn,
                """
                SELECT * FROM suppliers WHERE org_id = ? ORDER BY name LIMIT ? OFFSET ?
            """,
                (org_id, limit, skip),
            )
        return _fetchall(
            conn,
            """
            SELECT * FROM suppliers ORDER BY name LIMIT ? OFFSET ?
        """,
            (limit, skip),
        )
    finally:
        release_connection(conn)


def fetch_supplier_countries(org_id: str = "") -> list[str]:
    """Distinct countries from suppliers table."""
    conn = get_connection()
    try:
        if org_id:
            rows = _fetchall(
                conn,
                """
                SELECT DISTINCT country FROM suppliers WHERE org_id = ? ORDER BY country
            """,
                (org_id,),
            )
        else:
            rows = _fetchall(conn, "SELECT DISTINCT country FROM suppliers ORDER BY country")
        return [r["country"] for r in rows]
    finally:
        release_connection(conn)


def fetch_supplier(supplier_id: str) -> Optional[dict[str, Any]]:
    """Single supplier by ID."""
    conn = get_connection()
    try:
        return _fetchone(conn, "SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
    finally:
        release_connection(conn)


def fetch_supplier_scope3(supplier_id: str) -> Optional[dict[str, Any]]:
    """Scope 3 data for a supplier."""
    conn = get_connection()
    try:
        return _fetchone(
            conn,
            """
            SELECT * FROM supplier_scope3 WHERE supplier_id = ?
        """,
            (supplier_id,),
        )
    finally:
        release_connection(conn)


def fetch_all_scope3(org_id: str = "") -> list[dict[str, Any]]:
    """All scope 3 records."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(
                conn,
                """
                SELECT ss.*, s.name as supplier_name FROM supplier_scope3 ss
                JOIN suppliers s ON ss.supplier_id = s.id
                WHERE ss.org_id = ?
                ORDER BY ss.category
            """,
                (org_id,),
            )
        return _fetchall(
            conn,
            """
            SELECT ss.*, s.name as supplier_name FROM supplier_scope3 ss
            JOIN suppliers s ON ss.supplier_id = s.id
            ORDER BY ss.category
        """,
        )
    finally:
        release_connection(conn)


def fetch_questionnaire_responses(supplier_id: str) -> list[dict[str, Any]]:
    """Questionnaire responses for a supplier."""
    conn = get_connection()
    try:
        return _fetchall(
            conn,
            """
            SELECT * FROM questionnaire_responses WHERE supplier_id = ? ORDER BY tier, question_id
        """,
            (supplier_id,),
        )
    finally:
        release_connection(conn)


def fetch_coverage_stats(org_id: str = "") -> dict[str, Any]:
    """Supplier questionnaire coverage stats."""
    conn = get_connection()
    try:
        org = "WHERE org_id = ?" if org_id else ""
        params = (org_id,) if org_id else ()

        total = _fetchone(conn, f"SELECT COUNT(*) as cnt FROM suppliers {org}", params)["cnt"]
        responded = _fetchone(
            conn,
            f"""
            SELECT COUNT(*) as cnt FROM suppliers WHERE questionnaire_status = 'responded' {("AND org_id = ?" if org_id else "")}
        """,
            params,
        )["cnt"]
        total_spend = _fetchone(
            conn,
            f"""
            SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers {org}
        """,
            params,
        )["s"]
        covered_spend = _fetchone(
            conn,
            f"""
            SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers
            WHERE questionnaire_status = 'responded' {("AND org_id = ?" if org_id else "")}
        """,
            params,
        )["s"]
        return {
            "total_suppliers": total,
            "responding_suppliers": responded,
            "coverage_pct": round(responded / total * 100) if total else 0,
            "total_spend": total_spend,
            "covered_spend": covered_spend,
            "spend_coverage_pct": round(covered_spend / total_spend * 100) if total_spend else 0,
        }
    finally:
        release_connection(conn)


def fetch_response_based_coverage(org_id: str) -> dict[str, Any]:
    """Spend-weighted coverage based on actual questionnaire_responses rows.

    A "responded" supplier is one with at least one row in
    questionnaire_responses for this org_id.  This is more accurate than
    relying on the questionnaire_status column, which can drift from the
    actual response data.
    """
    conn = get_connection()
    try:
        total_row = _fetchone(
            conn,
            """
            SELECT COUNT(*) as cnt, COALESCE(SUM(annual_spend_usd), 0) as total_spend
            FROM suppliers WHERE org_id = ?
        """,
            (org_id,),
        )
        total_suppliers = total_row["cnt"]
        total_spend = total_row["total_spend"]

        responded_row = _fetchone(
            conn,
            """
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(spend), 0) as covered_spend
            FROM (
                SELECT DISTINCT qr.supplier_id
                FROM questionnaire_responses qr
                WHERE qr.org_id = ?
            ) responded
            INNER JOIN (
                SELECT id, annual_spend_usd as spend
                FROM suppliers WHERE org_id = ?
            ) s ON responded.supplier_id = s.id
        """,
            (org_id, org_id),
        )

        responded_suppliers = responded_row["cnt"]
        covered_spend = responded_row["covered_spend"]

        spend_weighted = round(covered_spend / total_spend * 100, 1) if total_spend else 0
        headcount = round(responded_suppliers / total_suppliers * 100, 1) if total_suppliers else 0

        return {
            "total_suppliers": total_suppliers,
            "responded_suppliers": responded_suppliers,
            "total_spend_usd": total_spend,
            "covered_spend_usd": covered_spend,
            "spend_weighted_coverage_pct": spend_weighted,
            "headcount_coverage_pct": headcount,
        }
    finally:
        release_connection(conn)


def fetch_emission_factors(factor_name: str = "", country_code: str = "") -> list[dict[str, Any]]:
    """Query emission factors."""
    conn = get_connection()
    try:
        query = "SELECT * FROM emission_factors WHERE 1=1"
        params: list[Any] = []
        if factor_name:
            query += " AND factor_name = ?"
            params.append(factor_name)
        if country_code:
            query += " AND country_code = ?"
            params.append(country_code)
        query += " ORDER BY factor_name"
        return _fetchall(conn, query, tuple(params))
    finally:
        release_connection(conn)


def fetch_framework_mappings(cluster: str = "", framework: str = "") -> list[dict[str, Any]]:
    """Query framework mappings."""
    conn = get_connection()
    try:
        query = "SELECT * FROM framework_mappings WHERE 1=1"
        params: list[Any] = []
        if cluster:
            query += " AND cluster = ?"
            params.append(cluster)
        if framework:
            query += " AND framework = ?"
            params.append(framework)
        query += " ORDER BY cluster, framework, disclosure_code"
        return _fetchall(conn, query, tuple(params))
    finally:
        release_connection(conn)


def fetch_alert_thresholds(org_id: str = "", cluster: str = "") -> list[dict[str, Any]]:
    """Query alert thresholds."""
    conn = get_connection()
    try:
        query = "SELECT * FROM alert_thresholds WHERE is_active = 1"
        params: list[Any] = []
        if org_id:
            query += " AND org_id = ?"
            params.append(org_id)
        if cluster:
            query += " AND cluster = ?"
            params.append(cluster)
        query += " ORDER BY cluster"
        return _fetchall(conn, query, tuple(params))
    finally:
        release_connection(conn)


def update_alert_threshold(
    threshold_id: int,
    org_id: str,
    *,
    operator: Optional[str] = None,
    threshold_value: Optional[float] = None,
    severity: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    """Update an alert threshold. Returns the updated row or None if not found/matched."""
    conn = get_connection()
    try:
        fields: list[str] = []
        params: list[Any] = []

        if operator is not None:
            fields.append("operator = ?")
            params.append(operator)
        if threshold_value is not None:
            fields.append("threshold_value = ?")
            params.append(threshold_value)
        if severity is not None:
            fields.append("severity = ?")
            params.append(severity)
        if is_active is not None:
            fields.append("is_active = ?")
            params.append(int(is_active))

        if not fields:
            return _fetchone(conn, "SELECT * FROM alert_thresholds WHERE id = ?", (threshold_id,))

        fields.append("updated_at = datetime('now')")
        params.extend([threshold_id, org_id])

        cur = _execute(
            conn,
            f"UPDATE alert_thresholds SET {', '.join(fields)} WHERE id = ? AND org_id = ?",
            tuple(params),
        )
        if cur.rowcount == 0:
            return None
        return _fetchone(conn, "SELECT * FROM alert_thresholds WHERE id = ?", (threshold_id,))
    finally:
        release_connection(conn)


def delete_alert_threshold(threshold_id: int, org_id: str) -> bool:
    """Delete an alert threshold. Returns True if deleted, False if not found/matched."""
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            "DELETE FROM alert_thresholds WHERE id = ? AND org_id = ?",
            (threshold_id, org_id),
        )
        return cur.rowcount > 0
    finally:
        release_connection(conn)


def insert_audit_log(
    org_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str = "",
    details: str = "",
    ip_address: str = "",
) -> None:
    """Insert an audit log entry."""
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            INSERT INTO audit_log (org_id, user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (org_id, user_id, action, resource_type, resource_id, details, ip_address),
        )
    finally:
        release_connection(conn)


def validate_response_value(
    supplier: dict[str, Any],
    question_id: str,
    response_value: Optional[float],
) -> tuple[str, str]:
    """Check a numeric response against spend-based sanity bounds.

    Returns (validation_status, validation_notes).
    Uses industry-avg energy intensity to compute an expected range:
      - q1 (electricity kWh):  0.5 kWh per USD of annual spend
      - q2 (diesel litres):    0.005 L per USD of annual spend

    Flagged if reported is >10× or <0.1× the expected value (i.e.,
    clearly inconsistent with the supplier's spend scale).
    """
    if response_value is None:
        return "verified", ""

    spend = supplier.get("annual_spend_usd", 0) or 0
    if spend <= 0:
        return "verified", ""

    # Map question_id to expected intensity (kWh or litres per USD)
    intensity_map: dict[str, float] = {
        "q1": 0.5,  # electricity kWh per USD
        "q2": 0.005,  # diesel litres per USD
    }
    expected = intensity_map.get(question_id)
    if expected is None:
        return "verified", ""

    expected_value = spend * expected
    if expected_value <= 0:
        return "verified", ""

    ratio = response_value / expected_value
    if ratio > 10:
        return (
            "flagged",
            f"Value ({response_value:,.0f}) is {ratio:.1f}× above "
            f"expected spend-based estimate ({expected_value:,.0f})",
        )
    if ratio < 0.1 and response_value > 0:
        return (
            "flagged",
            f"Value ({response_value:,.0f}) is {1 / ratio:.1f}× below "
            f"expected spend-based estimate ({expected_value:,.0f})",
        )
    return "verified", ""


def fetch_evidence_chain(org_id: str = "") -> dict[str, dict]:
    """Read evidence chain rows from DB, keyed by cluster.

    C3.3: Joins with emission_factors for citation fields. Falls back to
    in-memory EVIDENCE_CHAIN (CSV-built) only if DB table is completely empty.
    The DB path is protected by immutability triggers (C3.8).
    """
    conn = get_connection()
    try:
        query = (
            "SELECT * FROM evidence_chain WHERE org_id = ?"
            if org_id
            else "SELECT * FROM evidence_chain"
        )
        params = (org_id,) if org_id else ()
        rows = _fetchall(conn, query, params)
        if not rows:
            return {}
        chain: dict[str, dict] = {}
        for r in rows:
            # C3.3: Join emission_factor citation fields for CSRD/GRI reporting
            ef_id = r.get("emission_factor_id")
            if ef_id:
                ef_row = _fetchone(
                    conn,
                    "SELECT factor_name, category, factor_value, unit, source, year FROM emission_factors WHERE id = ?",
                    (ef_id,),
                )
                if ef_row:
                    r["emission_factor_source"] = ef_row.get("source", "")
                    r["emission_factor_year"] = ef_row.get("year")
                    r["emission_factor_value"] = ef_row.get("factor_value")
                    r["emission_factor_unit"] = ef_row.get("unit")
                    r["emission_factor_table"] = ef_row.get("factor_name", "")
            chain[r["cluster"]] = dict(r)
        return chain
    finally:
        release_connection(conn)


# C3.3: Cluster-level metadata for API response enrichment
_CLUSTER_META = {
    "energy_kwh": {
        "data_point_id_prefix": "dp_en",
        "unit": "kWh",
        "calculation_method": "direct_measurement",
        "reported_in_frameworks": ["CSRD", "GRI", "TCFD"],
    },
    "emissions_tco2": {
        "data_point_id_prefix": "dp_em",
        "unit": "tCO2e",
        "calculation_method": "activity_based",
        "reported_in_frameworks": ["CSRD", "ISSB", "GRI", "TCFD"],
        "upstream_records": ["dp_en_001"],
    },
    "water_m3": {
        "data_point_id_prefix": "dp_wt",
        "unit": "m³",
        "calculation_method": "direct_measurement",
        "reported_in_frameworks": ["CSRD", "GRI"],
    },
    "scope3_category1": {
        "data_point_id_prefix": "dp_s3",
        "unit": "tCO2e",
        "calculation_method": "activity_based",
        "reported_in_frameworks": ["CSRD", "ISSB", "GRI"],
    },
    "diesel_consumed": {
        "data_point_id_prefix": "dp_dl",
        "unit": "tCO2e",
        "calculation_method": "manual_calculation",
        "reported_in_frameworks": ["CSRD", "GRI"],
    },
    "scope3_category6": {
        "data_point_id_prefix": "dp_bt",
        "unit": "tCO2e",
        "calculation_method": "manual_calculation",
        "reported_in_frameworks": ["CSRD"],
    },
}


def create_evidence_chain_entry(
    org_id: str,
    metric_id: int,
    cluster: str,
    value: float,
    *,
    raw_value: Optional[float] = None,
    calculated_value: Optional[float] = None,
    emission_factor_id: Optional[int] = None,
    methodology: str = "",
    confidence: str = "MEDIUM",
    source_system: str = "mqtt",
    recorded_by: str = "",
    parent_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Create an evidence chain entry when a metric is uploaded.

    C3.3: Wired into metric upload flows (MQTT, CSV upload, API).
    Uses the DB connection pool and is org-scoped.

    Args:
        conn: If provided, uses this connection instead of acquiring a new one.
              Caller is responsible for commit/release. Enables atomic operations
              with the caller's transaction.
    """
    from src.evidence.hash_chain import compute_hash
    from datetime import datetime, timezone

    _conn_owned = False
    if conn is None:
        conn = get_connection()
        _conn_owned = True
    try:
        # Get previous hash for this cluster/org
        prev_row = _fetchone(
            conn,
            "SELECT hash FROM evidence_chain WHERE cluster=? AND org_id=? ORDER BY id DESC LIMIT 1",
            (cluster, org_id),
        )
        prev_hash = prev_row["hash"] if prev_row else None

        now = datetime.now(timezone.utc).isoformat()
        the_hash = compute_hash(cluster, value, now, prev_hash or "")

        cur = _execute(
            conn,
            """
            INSERT INTO evidence_chain
            (metric_id, org_id, cluster, hash, prev_hash, value, raw_value,
             calculated_value, emission_factor_id, methodology, confidence,
             computed_at, recorded_at, recorded_by, source_system, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metric_id,
                org_id,
                cluster,
                the_hash,
                prev_hash,
                value,
                raw_value,
                calculated_value,
                emission_factor_id,
                methodology,
                confidence,
                now,
                now,
                recorded_by,
                source_system,
                parent_id,
            ),
        )
        return {
            "id": cur.lastrowid,
            "metric_id": metric_id,
            "org_id": org_id,
            "cluster": cluster,
            "hash": the_hash,
            "prev_hash": prev_hash,
            "value": value,
            "raw_value": raw_value,
            "calculated_value": calculated_value,
            "emission_factor_id": emission_factor_id,
            "methodology": methodology,
            "confidence": confidence,
            "computed_at": now,
            "recorded_at": now,
            "recorded_by": recorded_by,
            "source_system": source_system,
            "parent_id": parent_id,
        }
    finally:
        if _conn_owned:
            release_connection(conn)


def fetch_prev_hash_by_cluster(org_id: str, cluster: str) -> Optional[str]:
    """Return the most recent hash for a cluster within an org, or None if no chain exists."""
    conn = get_connection()
    try:
        row = _fetchone(
            conn,
            "SELECT hash FROM evidence_chain WHERE cluster=? AND org_id=? ORDER BY id DESC LIMIT 1",
            (cluster, org_id),
        )
        return row["hash"] if row else None
    finally:
        release_connection(conn)


_retention_policy_active = False


def _run_retention_policy() -> None:
    """Called by _ensure_db() after migrations to enforce retention policy.

    Uses a raw SQLite connection to avoid re-entering _ensure_db() via get_connection().
    For PostgreSQL, uses get_connection() which does not recurse.
    """
    global _retention_policy_active
    if _retention_policy_active:
        return
    _retention_policy_active = True
    try:
        if not _is_postgres:
            # Raw connection avoids get_connection() → _ensure_db() recursion
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
        else:
            conn = get_connection()
        try:
            archive_retention_policy(conn=conn)
        finally:
            if not _is_postgres:
                conn.close()
            else:
                release_connection(conn)
    finally:
        _retention_policy_active = False


def archive_retention_policy(org_id: str = "", conn=None) -> dict[str, int]:
    """Archive records older than each org's retention_period_months.

    C3.9: Implements 7-year minimum retention (CSRD requirement).
    Records are moved to *_archive tables with archived_at timestamp.
    NO hard delete — archive tables retain all records indefinitely.

    When called with a pre-existing connection (conn=...), the caller owns the
    connection lifecycle. When called without, acquires and releases its own.
    Returns dict with counts of archived evidence_chain and audit_log rows.
    """
    from datetime import datetime, timezone, timedelta

    archived = {"evidence_chain": 0, "audit_log": 0}
    _conn_owned = conn is None
    if _conn_owned:
        if _is_postgres:
            conn = get_connection()
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
    try:
        # Get retention period per org
        if org_id:
            orgs = [
                _fetchone(
                    conn,
                    "SELECT id, retention_period_months FROM organizations WHERE id = ?",
                    (org_id,),
                )
            ]
        else:
            orgs = _fetchall(conn, "SELECT id, retention_period_months FROM organizations")

        for org in orgs:
            if not org or not org.get("retention_period_months"):
                continue
            oid = org["id"]
            retention_months = org["retention_period_months"]
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
            cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # C3.9: Archive evidence_chain rows older than cutoff
            # Move to archive table, then mark source row as archived (NOT deleted)
            ec_rows = _fetchall(
                conn,
                """
                SELECT id, metric_id, org_id, cluster, hash, prev_hash, value, raw_value,
                       calculated_value, emission_factor_id, methodology, confidence,
                       computed_at, recorded_at, recorded_by, source_system, parent_id
                FROM evidence_chain
                WHERE org_id = ? AND archived_at IS NULL AND recorded_at < ?
            """,
                (oid, cutoff_str),
            )
            for row in ec_rows:
                _execute(
                    conn,
                    """
                    INSERT INTO evidence_chain_archive
                    (id, metric_id, org_id, cluster, hash, prev_hash, value, raw_value,
                     calculated_value, emission_factor_id, methodology, confidence,
                     computed_at, recorded_at, recorded_by, source_system, parent_id,
                     archived_at, archive_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        row["id"],
                        row["metric_id"],
                        row["org_id"],
                        row["cluster"],
                        row["hash"],
                        row.get("prev_hash"),
                        row["value"],
                        row.get("raw_value"),
                        row.get("calculated_value"),
                        row.get("emission_factor_id"),
                        row["methodology"],
                        row["confidence"],
                        row["computed_at"],
                        row["recorded_at"],
                        row.get("recorded_by", ""),
                        row.get("source_system", "manual"),
                        row.get("parent_id"),
                        now_str,
                        "retention",
                    ),
                )
                _execute(
                    conn,
                    "UPDATE evidence_chain SET archived_at = ? WHERE id = ?",
                    (now_str, row["id"]),
                )
                archived["evidence_chain"] += 1

            # C3.9: Archive audit_log rows older than cutoff
            al_rows = _fetchall(
                conn,
                """
                SELECT id, org_id, user_id, action, resource_type, resource_id,
                       details, ip_address, created_at
                FROM audit_log
                WHERE org_id = ? AND archived_at IS NULL AND created_at < ?
            """,
                (oid, cutoff_str),
            )
            for row in al_rows:
                _execute(
                    conn,
                    """
                    INSERT INTO audit_log_archive
                    (id, org_id, user_id, action, resource_type, resource_id,
                     details, ip_address, archived_at, created_at, archive_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        row["id"],
                        row["org_id"],
                        row["user_id"],
                        row["action"],
                        row["resource_type"],
                        row.get("resource_id", ""),
                        row.get("details", ""),
                        row.get("ip_address", ""),
                        now_str,
                        row["created_at"],
                        "retention",
                    ),
                )
                _execute(
                    conn, "UPDATE audit_log SET archived_at = ? WHERE id = ?", (now_str, row["id"])
                )
                archived["audit_log"] += 1
    finally:
        if _conn_owned:
            if _is_postgres:
                release_connection(conn)
            else:
                conn.close()
    return archived


def fetch_wastewater_data(org_id: str) -> dict[str, Any]:
    """Fetch latest water metric with wastewater discharge and stress level."""
    conn = get_connection()
    try:
        row = _fetchone(
            conn,
            """
            SELECT value, wastewater_discharge, water_stress_level, period
            FROM metrics
            WHERE org_id = ? AND cluster = 'water_m3'
            ORDER BY recorded_at DESC LIMIT 1
        """,
            (org_id,),
        )
        if row is None:
            return {
                "wastewater_discharge": 0,
                "water_stress_level": "Unknown",
                "water_consumption_m3": 0,
                "period": "",
            }
        return {
            "wastewater_discharge": row["wastewater_discharge"] or 0,
            "water_stress_level": row["water_stress_level"] or "Unknown",
            "water_consumption_m3": row["value"],
            "period": row["period"] or "",
        }
    finally:
        release_connection(conn)


def fetch_trust_badges(org_id: str) -> dict[str, Any]:
    """Evaluate data-driven trust badge eligibility for an org."""
    conn = get_connection()
    try:
        # 1. CSRD Compliant: org has csrd_esrs framework mappings
        csrd_rows = _fetchall(
            conn,
            """
            SELECT COUNT(*) as cnt FROM framework_mappings
            WHERE org_id = ? AND framework = 'csrd_esrs'
        """,
            (org_id,),
        )
        csrd_compliant = csrd_rows[0]["cnt"] > 0 if csrd_rows else False

        # 2. GHG Protocol Source: org has emission factors with GHG Protocol source
        ghg_rows = _fetchall(
            conn,
            """
            SELECT COUNT(*) as cnt FROM emission_factors
            WHERE (org_id = ? OR org_id IS NULL OR org_id = '')
              AND (source LIKE '%GHG Protocol%' OR source LIKE '%ghg_protocol%')
        """,
            (org_id,),
        )
        ghg_protocol_source = ghg_rows[0]["cnt"] > 0 if ghg_rows else False

        # 3. Audit Ready: all evidence_chain rows for org have valid (non-tampered) hashes
        from src.evidence.hash_chain import verify_chain_record

        evidence_rows = _fetchall(
            conn,
            """
            SELECT cluster, value, recorded_at, hash, prev_hash
            FROM evidence_chain WHERE org_id = ?
        """,
            (org_id,),
        )
        audit_ready = False
        if evidence_rows:
            audit_ready = all(
                verify_chain_record(
                    cluster=r["cluster"],
                    value=float(r["value"]),
                    timestamp=r["recorded_at"],
                    stored_hash=r["hash"],
                    prev_hash=r.get("prev_hash"),
                )
                for r in evidence_rows
            )
        else:
            # No evidence chains yet — not audit ready
            audit_ready = False

        # 4. Scope 3 Verified: supplier questionnaire responses exist
        coverage = fetch_response_based_coverage(org_id)
        scope3_verified = (
            coverage["responded_suppliers"] > 0 and coverage["spend_weighted_coverage_pct"] > 0
        )

        return {
            "csrd_compliant": csrd_compliant,
            "ghg_protocol_source": ghg_protocol_source,
            "audit_ready": audit_ready,
            "scope3_verified": scope3_verified,
        }
    finally:
        release_connection(conn)
