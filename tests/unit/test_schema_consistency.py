"""Validate column-name consistency between SQLite and PostgreSQL schemas."""
import re
from pathlib import Path

SCHEMA_SQL = Path("src/db/schema.sql")
SCHEMA_PG = Path("src/db/schema_pg.sql")


def _parse_tables(schema_text: str) -> dict[str, list[str]]:
    """Extract {table_name: [col_name, ...]} from SQL DDL."""
    tables = {}
    # Match CREATE TABLE blocks
    for match in re.finditer(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\);",
        schema_text,
        re.DOTALL,
    ):
        table_name = match.group(1)
        body = match.group(2)
        columns = []
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if not line:
                continue
            if line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")):
                continue
            if line.upper().startswith("CREATE"):
                continue
            col_match = re.match(r"^(\w+)\s+", line)
            if col_match:
                columns.append(col_match.group(1).lower())
        tables[table_name.lower()] = columns
    return tables


class TestSchemaConsistency:
    def test_both_schemas_exist(self):
        assert SCHEMA_SQL.exists(), "SQLite schema missing"
        assert SCHEMA_PG.exists(), "PostgreSQL schema missing"

    def test_shared_tables_have_matching_columns(self):
        sqlite_text = SCHEMA_SQL.read_text()
        pg_text = SCHEMA_PG.read_text()
        sqlite_tables = _parse_tables(sqlite_text)
        pg_tables = _parse_tables(pg_text)

        shared = set(sqlite_tables) & set(pg_tables)
        assert shared, "No shared tables found"

        drifts = []
        for table in sorted(shared):
            sq_cols = set(sqlite_tables[table])
            pg_cols = set(pg_tables[table])
            missing_in_pg = sq_cols - pg_cols
            extra_in_pg = pg_cols - sq_cols
            if missing_in_pg:
                drifts.append(f"{table}: missing in PG: {sorted(missing_in_pg)}")
            if extra_in_pg:
                drifts.append(f"{table}: extra in PG: {sorted(extra_in_pg)}")

        assert not drifts, (
            "Schema drift detected:\n" + "\n".join(drifts)
            + "\n\nEvery column in SQLite must have a matching column in PostgreSQL."
        )

    def test_sqlite_tables_exist_in_postgres(self):
        sqlite_tables = _parse_tables(SCHEMA_SQL.read_text())
        pg_tables = _parse_tables(SCHEMA_PG.read_text())
        missing = set(sqlite_tables) - set(pg_tables)
        assert not missing, f"Tables in SQLite but missing from PostgreSQL: {sorted(missing)}"

    def test_postgres_tables_exist_in_sqlite(self):
        sqlite_tables = _parse_tables(SCHEMA_SQL.read_text())
        pg_tables = _parse_tables(SCHEMA_PG.read_text())
        missing = set(pg_tables) - set(sqlite_tables)
        assert not missing, f"Tables in PostgreSQL but missing from SQLite: {sorted(missing)}"

    def test_shared_tables_have_matching_column_counts(self):
        """Verify every shared table has the same number of columns."""
        sqlite_tables = _parse_tables(SCHEMA_SQL.read_text())
        pg_tables = _parse_tables(SCHEMA_PG.read_text())

        shared = set(sqlite_tables) & set(pg_tables)
        mismatches = []
        for table in sorted(shared):
            sq_count = len(sqlite_tables[table])
            pg_count = len(pg_tables[table])
            if sq_count != pg_count:
                mismatches.append(
                    f"{table}: SQLite has {sq_count} columns, "
                    f"PostgreSQL has {pg_count} columns"
                )

        assert not mismatches, (
            "Column count mismatch:\n" + "\n".join(mismatches)
        )
