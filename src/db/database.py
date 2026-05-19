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
    global _pg_pool
    if _pg_pool is None or _pg_pool.closed:
        import psycopg2
        from psycopg2.pool import ThreadedConnectionPool
        size = _get_pool_size()
        _pg_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=size,
            dsn=DATABASE_URL,
        )
    return _pg_pool


def _adapt_query(query: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL %s if needed."""
    if _is_postgres:
        return query.replace("?", "%s")
    return query


def get_connection(row_factory: bool = True):
    """Get a database connection. Returns sqlite3.Connection or psycopg2 connection.

    For PostgreSQL, the connection is acquired from the pool. The caller MUST
    call release_connection() when done to return it to the pool.
    For SQLite, a new connection is created each call and should be closed by the caller.
    """
    _ensure_db()
    if _is_postgres:
        pool = _get_pg_pool()
        conn = pool.getconn()
        conn.autocommit = True
        return conn
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def release_connection(conn) -> None:
    """Return a connection to the pool (PostgreSQL) or close it (SQLite).

    Safe to call with None — does nothing.
    """
    if conn is None:
        return
    if _is_postgres:
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


def _ensure_db() -> None:
    """Initialize database from schema if needed."""
    global _initialized
    if _initialized:
        return
    if _is_postgres:
        conn = get_connection()
        try:
            conn.autocommit = True
            schema = SCHEMA_PG_PATH.read_text()
            cur = conn.cursor()
            cur.execute(schema)
            cur.close()
        finally:
            release_connection(conn)
    else:
        if not DB_PATH.exists():
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA_PATH.read_text())
            conn.close()
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
                "whatsapp_messages", "audit_log", "questionnaire_questions",
                "questionnaire_templates", "alert_thresholds",
                "framework_mappings", "emission_factors", "questionnaire_responses",
                "supplier_scope3", "api_keys", "risk_flags", "evidence_chain",
                "metrics", "suppliers", "factories", "users", "organizations",
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
        return _fetchall(conn, f"""
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
        """, tuple(params))
    finally:
        release_connection(conn)


def fetch_trends(cluster: str, factory_id: str = "factory_bd_001", org_id: str = "") -> list[dict[str, Any]]:
    """Time series for a specific metric cluster."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(conn, """
                SELECT m.recorded_at, m.value FROM metrics m
                JOIN factories f ON m.factory_id = f.id
                WHERE f.org_id = ? AND m.cluster = ?
                ORDER BY m.recorded_at
            """, (org_id, cluster))
        return _fetchall(conn, """
            SELECT recorded_at, value FROM metrics
            WHERE factory_id = ? AND cluster = ?
            ORDER BY recorded_at
        """, (factory_id, cluster))
    finally:
        release_connection(conn)


def fetch_all_trends(factory_id: str = "factory_bd_001", org_id: str = "") -> list[dict[str, Any]]:
    """Combined trends for energy, emissions, water."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(conn, """
                SELECT m.recorded_at, m.cluster, m.value FROM metrics m
                JOIN factories f ON m.factory_id = f.id
                WHERE f.org_id = ? AND m.cluster IN ('energy_kwh', 'emissions_tco2', 'water_m3')
                ORDER BY m.recorded_at
            """, (org_id,))
        return _fetchall(conn, """
            SELECT recorded_at, cluster, value FROM metrics
            WHERE factory_id = ? AND cluster IN ('energy_kwh', 'emissions_tco2', 'water_m3')
            ORDER BY recorded_at
        """, (factory_id,))
    finally:
        release_connection(conn)


def fetch_risk_flags(
    factory_id: str = "factory_bd_001",
    cluster: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    org_id: str = "",
) -> list[dict[str, Any]]:
    """Risk flags with optional filters, sorted by priority descending."""
    conn = get_connection()
    try:
        query = "SELECT * FROM risk_flags WHERE factory_id = ?"
        params: list[Any] = [factory_id]

        if org_id:
            query += " AND org_id = ?"
            params.append(org_id)
        if cluster is not None:
            query += " AND cluster = ?"
            params.append(cluster)
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(int(acknowledged))

        query += " ORDER BY priority_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        return _fetchall(conn, query, tuple(params))
    finally:
        release_connection(conn)


def acknowledge_risk_flag(flag_id: str, acknowledged_by: str, org_id: str = "") -> Optional[dict[str, Any]]:
    """Acknowledge a risk flag. Returns the updated flag or None."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        if org_id:
            cur = _execute(conn, """
                UPDATE risk_flags SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
                WHERE id = ? AND org_id = ?
            """, (now, acknowledged_by, flag_id, org_id))
        else:
            cur = _execute(conn, """
                UPDATE risk_flags SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ? WHERE id = ?
            """, (now, acknowledged_by, flag_id))
        if _is_postgres:
            rowcount = cur.rowcount
        else:
            rowcount = cur.rowcount
        if rowcount == 0:
            return None
        return _fetchone(conn, "SELECT * FROM risk_flags WHERE id = ?", (flag_id,))
    finally:
        release_connection(conn)


def fetch_suppliers(skip: int = 0, limit: int = 100, org_id: str = "") -> list[dict[str, Any]]:
    """All suppliers with pagination."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(conn, """
                SELECT * FROM suppliers WHERE org_id = ? ORDER BY name LIMIT ? OFFSET ?
            """, (org_id, limit, skip))
        return _fetchall(conn, """
            SELECT * FROM suppliers ORDER BY name LIMIT ? OFFSET ?
        """, (limit, skip))
    finally:
        release_connection(conn)


def fetch_supplier_countries(org_id: str = "") -> list[str]:
    """Distinct countries from suppliers table."""
    conn = get_connection()
    try:
        if org_id:
            rows = _fetchall(conn, """
                SELECT DISTINCT country FROM suppliers WHERE org_id = ? ORDER BY country
            """, (org_id,))
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
        return _fetchone(conn, """
            SELECT * FROM supplier_scope3 WHERE supplier_id = ?
        """, (supplier_id,))
    finally:
        release_connection(conn)


def fetch_all_scope3(org_id: str = "") -> list[dict[str, Any]]:
    """All scope 3 records."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(conn, """
                SELECT ss.*, s.name as supplier_name FROM supplier_scope3 ss
                JOIN suppliers s ON ss.supplier_id = s.id
                WHERE ss.org_id = ?
                ORDER BY ss.category
            """, (org_id,))
        return _fetchall(conn, """
            SELECT ss.*, s.name as supplier_name FROM supplier_scope3 ss
            JOIN suppliers s ON ss.supplier_id = s.id
            ORDER BY ss.category
        """)
    finally:
        release_connection(conn)


def fetch_questionnaire_responses(supplier_id: str) -> list[dict[str, Any]]:
    """Questionnaire responses for a supplier."""
    conn = get_connection()
    try:
        return _fetchall(conn, """
            SELECT * FROM questionnaire_responses WHERE supplier_id = ? ORDER BY tier, question_id
        """, (supplier_id,))
    finally:
        release_connection(conn)


def fetch_coverage_stats(org_id: str = "") -> dict[str, Any]:
    """Supplier questionnaire coverage stats."""
    conn = get_connection()
    try:
        org = "WHERE org_id = ?" if org_id else ""
        params = (org_id,) if org_id else ()

        total = _fetchone(conn, f"SELECT COUNT(*) as cnt FROM suppliers {org}", params)["cnt"]
        responded = _fetchone(conn, f"""
            SELECT COUNT(*) as cnt FROM suppliers WHERE questionnaire_status = 'responded' {('AND org_id = ?' if org_id else '')}
        """, params)["cnt"]
        total_spend = _fetchone(conn, f"""
            SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers {org}
        """, params)["s"]
        covered_spend = _fetchone(conn, f"""
            SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers
            WHERE questionnaire_status = 'responded' {('AND org_id = ?' if org_id else '')}
        """, params)["s"]
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


def insert_audit_log(org_id: str, user_id: str, action: str,
                     resource_type: str, resource_id: str = "",
                     details: str = "", ip_address: str = "") -> None:
    """Insert an audit log entry."""
    conn = get_connection()
    try:
        _execute(conn, """
            INSERT INTO audit_log (org_id, user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (org_id, user_id, action, resource_type, resource_id, details, ip_address))
    finally:
        release_connection(conn)
