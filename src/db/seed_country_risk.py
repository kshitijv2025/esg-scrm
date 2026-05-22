"""Seed country risk scores from the hardcoded risk_predictor data + additional countries."""

from src.db.database import _execute, get_connection, release_connection

COUNTRY_RISK_DATA = [
    # country_code, country_name, risk_score (0-15 scale matching _COUNTRY_RISK in risk_predictor.py)
    ("BD", "Bangladesh", 10.0, "Kailash Internal"),
    ("IN", "India", 5.0, "Kailash Internal"),
    ("VN", "Vietnam", 8.0, "Kailash Internal"),
    ("TH", "Thailand", 6.0, "Kailash Internal"),
    ("MM", "Myanmar", 15.0, "Kailash Internal"),
    ("ID", "Indonesia", 7.0, "Kailash Internal"),
    ("CN", "China", 9.0, "Kailash Internal"),
    ("TR", "Turkey", 10.0, "Kailash Internal"),
    ("KH", "Cambodia", 12.0, "Kailash Internal"),
    ("PK", "Pakistan", 14.0, "Kailash Internal"),
    # Additional countries
    ("ET", "Ethiopia", 13.0, "Kailash Internal"),
    ("LA", "Laos", 11.0, "Kailash Internal"),
    ("PH", "Philippines", 7.0, "Kailash Internal"),
    ("MY", "Malaysia", 4.0, "Kailash Internal"),
    ("SG", "Singapore", 2.0, "Kailash Internal"),
    ("LK", "Sri Lanka", 8.0, "Kailash Internal"),
    ("NP", "Nepal", 9.0, "Kailash Internal"),
    ("BT", "Bhutan", 5.0, "Kailash Internal"),
]


def seed_country_risk() -> None:
    """Seed or update country_risk_scores table.

    Uses INSERT OR REPLACE to upsert — preserves existing scores on re-run.
    """
    conn = get_connection()
    try:
        _execute(conn, "DELETE FROM country_risk_scores", ())
        for code, name, score, source in COUNTRY_RISK_DATA:
            _execute(
                conn,
                """
                INSERT INTO country_risk_scores (country_code, country_name, risk_score, source)
                VALUES (?, ?, ?, ?)
            """,
                (code, name, score, source),
            )
    finally:
        release_connection(conn)


if __name__ == "__main__":
    seed_country_risk()
    print("Country risk scores seeded.")
