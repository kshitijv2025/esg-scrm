"""
Centralized SQLite database manager for the ESG SCRM platform.
Replaces duplicated _init_db() calls in etl.py and mqtt_client.py.
All API routes use this module to query the database.
"""
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent / "esg_scrm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_initialized = False


def get_connection(row_factory: bool = True) -> sqlite3.Connection:
    """Get a SQLite connection. Initializes the database on first call."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_db() -> None:
    """Initialize database from schema.sql if it doesn't exist."""
    global _initialized
    if _initialized and DB_PATH.exists():
        return
    if DB_PATH.exists():
        _initialized = True
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    _initialized = True


def reset_database() -> None:
    """Delete and recreate the database. Used by seed script and tests."""
    global _initialized
    if DB_PATH.exists():
        DB_PATH.unlink()
    _initialized = False
    _ensure_db()


# --- Query helpers for routes ---

def fetch_metrics(factory_id: str = "factory_bd_001") -> list[dict[str, Any]]:
    """Latest metric per cluster with evidence chain hashes."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT m.id, m.cluster, m.value, m.unit, m.confidence, m.source,
                      m.period, m.recorded_at, e.hash, e.prev_hash
               FROM metrics m
               LEFT JOIN evidence_chain e ON m.id = e.metric_id
               WHERE m.factory_id = ?
               AND m.recorded_at = (
                   SELECT MAX(m2.recorded_at) FROM metrics m2
                   WHERE m2.cluster = m.cluster AND m2.factory_id = m.factory_id
               )
               ORDER BY m.cluster""",
            (factory_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_trends(cluster: str, factory_id: str = "factory_bd_001") -> list[dict[str, Any]]:
    """Time series for a specific metric cluster."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT recorded_at, value FROM metrics
               WHERE factory_id = ? AND cluster = ?
               ORDER BY recorded_at""",
            (factory_id, cluster),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_all_trends(factory_id: str = "factory_bd_001") -> list[dict[str, Any]]:
    """Combined trends for energy, emissions, water."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT recorded_at, cluster, value FROM metrics
               WHERE factory_id = ? AND cluster IN ('energy_kwh', 'emissions_tco2', 'water_m3')
               ORDER BY recorded_at""",
            (factory_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_risk_flags(
    factory_id: str = "factory_bd_001",
    cluster: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
) -> list[dict[str, Any]]:
    """Risk flags with optional filters, sorted by priority descending."""
    conn = get_connection()
    try:
        query = "SELECT * FROM risk_flags WHERE factory_id = ?"
        params: list[Any] = [factory_id]

        if cluster is not None:
            query += " AND cluster = ?"
            params.append(cluster)
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(int(acknowledged))

        query += " ORDER BY priority_score DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def acknowledge_risk_flag(flag_id: str, acknowledged_by: str) -> Optional[dict[str, Any]]:
    """Acknowledge a risk flag. Returns the updated flag or None."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE risk_flags SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
            (now, acknowledged_by, flag_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM risk_flags WHERE id = ?", (flag_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_suppliers() -> list[dict[str, Any]]:
    """All suppliers."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_supplier(supplier_id: str) -> Optional[dict[str, Any]]:
    """Single supplier by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_supplier_scope3(supplier_id: str) -> Optional[dict[str, Any]]:
    """Scope 3 data for a supplier."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM supplier_scope3 WHERE supplier_id = ?",
            (supplier_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_all_scope3() -> list[dict[str, Any]]:
    """All scope 3 records."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ss.*, s.name as supplier_name FROM supplier_scope3 ss
               JOIN suppliers s ON ss.supplier_id = s.id
               ORDER BY ss.category"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_questionnaire_responses(supplier_id: str) -> list[dict[str, Any]]:
    """Questionnaire responses for a supplier."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM questionnaire_responses WHERE supplier_id = ? ORDER BY tier, question_id",
            (supplier_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_coverage_stats() -> dict[str, Any]:
    """Supplier questionnaire coverage stats."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM suppliers").fetchone()["cnt"]
        responded = conn.execute(
            "SELECT COUNT(*) as cnt FROM suppliers WHERE questionnaire_status = 'responded'"
        ).fetchone()["cnt"]
        total_spend = conn.execute("SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers").fetchone()["s"]
        covered_spend = conn.execute(
            "SELECT COALESCE(SUM(annual_spend_usd), 0) as s FROM suppliers WHERE questionnaire_status = 'responded'"
        ).fetchone()["s"]
        return {
            "total_suppliers": total,
            "responding_suppliers": responded,
            "coverage_pct": round(responded / total * 100) if total else 0,
            "total_spend": total_spend,
            "covered_spend": covered_spend,
            "spend_coverage_pct": round(covered_spend / total_spend * 100) if total_spend else 0,
        }
    finally:
        conn.close()
