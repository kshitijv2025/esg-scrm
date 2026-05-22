"""
Minimal seed — creates only the login user, no demo data.
Run once to set up a login-capable database without polluting it with sample metrics.
"""

from src.db.database import get_connection, release_connection, _execute


def minimal_seed() -> None:
    """Seed org + admin user only. Safe to re-run (idempotent)."""
    conn = get_connection(row_factory=False)

    # Org
    _execute(
        conn,
        """
        INSERT OR IGNORE INTO organizations
          (id, name, industry, employee_count, primary_buyer, annual_revenue_usd, connected_since)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        ("org_bd_001", "TextileBD Manufacturing", "Manufacturing", 500, "", 0, "2026-01-01"),
    )

    # Admin user
    from src.auth.password import hash_password

    _execute(
        conn,
        """
        INSERT OR IGNORE INTO users
          (id, org_id, email, password_hash, full_name, role, email_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "usr_admin_001",
            "org_bd_001",
            "admin@textilebd.com",
            hash_password("admin123"),
            "Administrator",
            "admin",
            1,
        ),
    )

    release_connection(conn)
    print("Minimal seed done — login: admin@textilebd.com / admin123")


if __name__ == "__main__":
    minimal_seed()
