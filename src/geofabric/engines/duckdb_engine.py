from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType

import duckdb
import pandas as pd
import pyarrow as pa

from geofabric.errors import EngineError, ExtensionError, QueryError
from geofabric.protocols import supports_duckdb_relation
from geofabric.sql_utils import escape_path

__all__ = ["DuckDBEngine", "DuckDBEngineFactory", "QueryScope"]


@dataclass
class DuckDBEngine:
    """DuckDB query execution engine with resource management.

    Supports both manual and context manager usage patterns:

        # Context manager (recommended for resource cleanup):
        with DuckDBEngine() as engine:
            result = engine.query_to_df("SELECT 1")

        # Manual usage (remember to close!):
        engine = DuckDBEngine()
        try:
            result = engine.query_to_df("SELECT 1")
        finally:
            engine.close()

    Design Principles:
        - Resource Safety: Context manager ensures connection cleanup
        - Lazy Initialization: Connection created on first use
        - Single Responsibility: Query execution only
    """

    database: str = ":memory:"
    _con: duckdb.DuckDBPyConnection | None = field(default=None, repr=False)
    _spatial_loaded: bool = field(default=False, repr=False)

    def engine_kind(self) -> str:
        return "duckdb"

    def con(self) -> duckdb.DuckDBPyConnection:
        """Get or create the database connection (lazy initialization)."""
        if self._con is None:
            self._con = duckdb.connect(self.database)
        return self._con

    def close(self) -> None:
        """Close the database connection and release resources.

        Safe to call multiple times. After closing, the engine can
        still be used - a new connection will be created on next use.
        """
        if self._con is not None:
            try:
                self._con.close()
            except Exception:  # nosec B110 - intentional: ignore cleanup errors
                pass
            self._con = None
            self._spatial_loaded = False

    def __enter__(self) -> "DuckDBEngine":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, closing connection."""
        self.close()

    def __del__(self) -> None:
        """Destructor to clean up connection if not explicitly closed."""
        self.close()

    def _ensure_spatial(self) -> None:
        """Load the DuckDB spatial extension (lazy loading).

        Raises:
            ExtensionError: If the extension cannot be loaded
        """
        if self._spatial_loaded:
            return

        con = self.con()

        # First try to load if already installed
        try:
            con.execute("LOAD spatial;")
            self._spatial_loaded = True
            return
        except duckdb.Error:
            pass  # Extension not installed yet, try to install

        # Try to install the extension
        try:
            con.execute("INSTALL spatial;")
            con.execute("LOAD spatial;")
            self._spatial_loaded = True
        except duckdb.Error as e:
            error_msg = str(e)
            if "Failed to download" in error_msg or "Could not establish connection" in error_msg:
                raise ExtensionError(
                    "spatial",
                    "Could not download the DuckDB spatial extension. "
                    "This may be due to network issues. Please ensure you have "
                    "internet connectivity or pre-install the extension with:\n"
                    "  duckdb -c 'INSTALL spatial;'\n\n"
                    f"Original error: {e}",
                ) from e
            raise ExtensionError("spatial", f"Failed to load spatial extension: {e}") from e

    def source_to_relation_sql(self, source: object) -> str:
        """Convert a source to SQL that can be used in FROM clause.

        Uses protocol dispatch - sources implementing SourceWithDuckDBRelation
        can describe themselves as SQL. This follows the Open/Closed Principle:
        new sources can be added without modifying this method.

        Args:
            source: A source implementing SourceWithDuckDBRelation protocol

        Returns:
            SQL string usable in FROM clause

        Raises:
            EngineError: If source type is not supported
        """
        # Protocol dispatch: let sources describe themselves as SQL
        if supports_duckdb_relation(source):
            return source.to_duckdb_relation_sql(self)

        raise EngineError(f"Unsupported source type: {type(source)}")

    def query_to_df(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return results as pandas DataFrame.

        Args:
            sql: SQL query to execute

        Returns:
            Query results as DataFrame

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Ensure spatial extension is loaded for queries using spatial functions
            self._ensure_spatial()
            return self.con().execute(sql).df()
        except Exception as e:
            raise QueryError(f"DuckDB query failed: {e}", sql=sql) from e

    def query_to_arrow(self, sql: str) -> pa.Table:
        """Execute SQL and return results as PyArrow Table.

        Args:
            sql: SQL query to execute

        Returns:
            Query results as Arrow Table

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Ensure spatial extension is loaded for queries using spatial functions
            self._ensure_spatial()
            return self.con().execute(sql).fetch_arrow_table()
        except Exception as e:
            raise QueryError(f"DuckDB query failed: {e}", sql=sql) from e

    def copy_to_parquet(self, sql: str, out_path: str) -> None:
        """Copy query results to a Parquet file.

        Args:
            sql: SQL query to execute
            out_path: Output file path

        Raises:
            QueryError: If query or write fails
        """
        out = str(Path(out_path).expanduser().resolve())
        escaped_out = escape_path(out)  # Escape single quotes to prevent SQL injection
        copy_sql = f"COPY ({sql}) TO '{escaped_out}' (FORMAT PARQUET);"
        try:
            self.con().execute(copy_sql)  # nosemgrep
        except Exception as e:
            raise QueryError(f"Failed to write parquet to {out_path}: {e}", sql=sql) from e

    def copy_to_geojson(self, sql: str, out_path: str) -> None:
        """Write query results to GeoJSON (requires spatial extension).

        Args:
            sql: SQL query to execute
            out_path: Output file path

        Raises:
            ExtensionError: If spatial extension cannot be loaded
            QueryError: If query or write fails
        """
        self._ensure_spatial()
        out = str(Path(out_path).expanduser().resolve())
        escaped_out = escape_path(out)  # Escape single quotes to prevent SQL injection
        copy_sql = f"COPY ({sql}) TO '{escaped_out}' WITH (FORMAT GDAL, DRIVER 'GeoJSON');"
        try:
            self.con().execute(copy_sql)  # nosemgrep
        except Exception as e:
            raise QueryError(f"Failed to write geojson to {out_path}: {e}", sql=sql) from e

class QueryScope:
    """Context manager for scoped query execution.

    Provides a scoped context for executing multiple queries while keeping
    the connection alive, with automatic cleanup on exit. Useful when you
    need to execute multiple related queries.

    Example:
        >>> engine = DuckDBEngine()
        >>> with engine.query_scope() as scope:
        ...     df1 = scope.execute("SELECT * FROM table1")
        ...     df2 = scope.execute("SELECT * FROM table2")
        >>> # Connection cleaned up automatically

    Design Principles:
        - Resource Safety: Connection remains open during scope
        - Convenience: Simple execute() method for running queries
        - Cleanup: Engine closed on scope exit (if owned by scope)
    """

    def __init__(self, engine: DuckDBEngine, *, close_on_exit: bool = True) -> None:
        """Initialize the query scope.

        Args:
            engine: DuckDB engine to use
            close_on_exit: If True, close the engine on scope exit
        """
        self._engine = engine
        self._close_on_exit = close_on_exit

    def __enter__(self) -> "QueryScope":
        """Enter the query scope."""
        # Ensure connection is established
        self._engine.con()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the query scope, optionally closing the engine."""
        if self._close_on_exit:
            self._engine.close()

    def execute(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return results as DataFrame.

        Args:
            sql: SQL query to execute

        Returns:
            Query results as DataFrame
        """
        return self._engine.query_to_df(sql)

    def execute_arrow(self, sql: str) -> pa.Table:
        """Execute SQL and return results as PyArrow Table.

        Args:
            sql: SQL query to execute

        Returns:
            Query results as Arrow Table
        """
        return self._engine.query_to_arrow(sql)

    @property
    def engine(self) -> DuckDBEngine:
        """Get the underlying engine."""
        return self._engine


# Add query_scope method to DuckDBEngine
def _query_scope(self: DuckDBEngine, *, close_on_exit: bool = True) -> QueryScope:
    """Create a scoped context for query execution.

    Args:
        close_on_exit: If True (default), close the engine when scope exits

    Returns:
        QueryScope context manager

    Example:
        >>> with engine.query_scope() as scope:
        ...     df = scope.execute("SELECT * FROM table")
    """
    return QueryScope(self, close_on_exit=close_on_exit)


# Attach method to class
DuckDBEngine.query_scope = _query_scope


from geofabric.registry import EngineClassFactory

# Use generic factory instead of boilerplate class
DuckDBEngineFactory = EngineClassFactory(DuckDBEngine)
