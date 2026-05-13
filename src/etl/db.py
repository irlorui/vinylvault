"""DuckDB connection wrapper, singleton, and schema initialization."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class DuckDBClient:
    """Thin DuckDB connection wrapper for VinylVault."""

    def __init__(self, database_path: str = "./data/vinylvault.duckdb"):
        """Set up the DuckDB connection."""
        self.database_path = database_path
        self.connection: duckdb.DuckDBPyConnection = duckdb.connect(self.database_path)
        logger.info(f"DuckDB connection opened: {self.database_path}")

    def test_connection(self) -> bool:
        """Return True if the DuckDB connection is healthy."""
        try:
            result = self.connection.execute("SELECT 1").fetchone()
            if result is None:
                return False
            return result[0] == 1
        except Exception as e:
            logger.error("DuckDB connection test failed: %s", e)
            return False

    def create_dataset(self, dataset_name: str) -> None:
        """Create a schema (dataset) in DuckDB."""
        try:
            self.connection.execute(f"CREATE SCHEMA IF NOT EXISTS {dataset_name};")
            logger.info("Created / verified schema: %s", dataset_name)
        except Exception as e:
            logger.error("Error creating schema %s: %s", dataset_name, e)
            raise

    def truncate_table(self, table_name: str, dataset: str) -> None:
        """Drop and recreate a table (truncate via DROP IF EXISTS)."""
        try:
            self.connection.execute(f"DROP TABLE IF EXISTS {dataset}.{table_name};")
            logger.info("Dropped existing table %s.%s", dataset, table_name)
        except Exception as e:
            logger.warning("Could not drop table %s.%s: %s", dataset, table_name, e)
            raise

    def insert_records(
        self, table_name: str, records: List[Dict[str, Any]], dataset: str = "raw"
    ) -> Dict[str, int]:
        """Insert a list of dicts into the given table."""
        if not records:
            return {"inserted": 0, "updated": 0}
        try:
            df = pd.DataFrame(records)  # noqa: F841 — DuckDB references `df` by name in SQL
            full_table_name = f"{dataset}.{table_name}"
            self.connection.execute(
                f"CREATE TABLE IF NOT EXISTS {full_table_name} AS SELECT * FROM df WHERE 1=0;"  # noqa: E501
            )
            self.connection.execute(f"INSERT INTO {full_table_name} SELECT * FROM df;")
            inserted_count = len(records)
            logger.info("Inserted %d records into %s", inserted_count, full_table_name)
            return {"inserted": inserted_count, "updated": 0}
        except Exception as e:
            logger.error("Error inserting records into %s: %s", table_name, e)
            raise

    def upsert_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        primary_key: str,
        dataset: str = "raw",
    ) -> Dict[str, int]:
        """Insert or replace records, keyed by primary_key."""
        if not records:
            return {"inserted": 0, "updated": 0}
        try:
            df = pd.DataFrame(records)
            full_table_name = f"{dataset}.{table_name}"

            existing_keys: set = set()
            if primary_key in df.columns:
                try:
                    pk_values = df[primary_key].tolist()
                    pk_list = ",".join(f"'{val}'" for val in pk_values)
                    existing_result = self.connection.execute(
                        f"SELECT {primary_key} FROM {full_table_name} WHERE {primary_key} IN ({pk_list})"  # noqa: E501
                    ).fetch_df()
                    existing_keys = (
                        set(existing_result[primary_key].tolist())
                        if not existing_result.empty
                        else set()
                    )
                except Exception:
                    pass

                df_keys = set(df[primary_key].tolist()) if not df.empty else set()
                updated_count = len(df_keys.intersection(existing_keys))
                inserted_count = len(df_keys) - updated_count

                self.connection.execute(
                    f"CREATE TABLE IF NOT EXISTS {full_table_name} AS SELECT * FROM df WHERE 1=0;"  # noqa: E501
                )

                columns = list(df.columns)
                column_names = ", ".join(columns)
                placeholders = ", ".join(["?" for _ in columns])
                non_pk_cols = [c for c in columns if c != primary_key]
                if non_pk_cols:
                    updates = ", ".join(f"{c} = excluded.{c}" for c in non_pk_cols)
                    upsert_query = (
                        f"INSERT INTO {full_table_name} ({column_names}) "
                        f"VALUES ({placeholders}) "
                        f"ON CONFLICT ({primary_key}) DO UPDATE SET {updates}"
                    )
                else:
                    upsert_query = (
                        f"INSERT INTO {full_table_name} ({column_names}) "
                        f"VALUES ({placeholders}) "
                        f"ON CONFLICT ({primary_key}) DO NOTHING"
                    )
                for _, row in df.iterrows():
                    values = [row[col] for col in columns]
                    self.connection.execute(upsert_query, values)

                logger.info(
                    "Upserted %d records into %s: %d new, %d updated",
                    len(records),
                    full_table_name,
                    inserted_count,
                    updated_count,
                )
                return {"inserted": inserted_count, "updated": updated_count}
        except Exception as e:
            logger.error("Error upserting records into %s: %s", table_name, e)
            raise
        return {"inserted": 0, "updated": 0}

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts."""
        try:
            result = self.connection.execute(query, params or {}).fetchdf()
            return result.to_dict("records")  # type: ignore[return-value]
        except Exception as e:
            logger.error("Error executing query: %s", e)
            raise

    def get_available_tables(self, dataset: str = "raw") -> List[str]:
        """Return all table names in the given schema."""
        try:
            query = (
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{dataset}'"
            )
            result = self.connection.execute(query).fetchdf()
            return result["table_name"].tolist() if not result.empty else []
        except Exception as e:
            logger.error("Error getting tables from %s: %s", dataset, e)
            return []

    def run_migrations(
        self,
        migrations_dir: Path = Path(__file__).parent / "migrations",
    ) -> None:
        """Execute all SQL scripts under migrations_dir to initialise the DB schema.

        Each immediate subdirectory is treated as a schema name; its .sql files are
        executed in alphabetical order after the schema is created.
        """
        if not migrations_dir.is_dir():
            raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

        for schema_dir in sorted(migrations_dir.iterdir()):
            if not schema_dir.is_dir():
                continue
            schema_name = schema_dir.name
            self.create_dataset(schema_name)
            for sql_file in sorted(schema_dir.glob("*.sql")):
                logger.info("Executing migration: %s/%s", schema_name, sql_file.name)
                self.connection.execute(sql_file.read_text())
        logger.info("Migrations complete")

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self.connection:
            self.connection.close()
            logger.info("DuckDB connection closed")


# ─── Singleton ─────────────────────────────────────────────────────────────

_DB_CLIENT: DuckDBClient | None = None


def close_db_client() -> None:
    """Close and release the shared DuckDBClient."""
    global _DB_CLIENT
    if _DB_CLIENT is not None:
        _DB_CLIENT.close()
        _DB_CLIENT = None
