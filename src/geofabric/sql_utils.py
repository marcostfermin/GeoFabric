"""SQL utilities for safe query construction.

This module provides centralized utilities for:
- Escaping values for safe SQL embedding
- Validating SQL identifiers to prevent injection
- Building common SQL expressions
- DuckDB-specific SQL generation

Security Note:
    All string interpolation into SQL should use these utilities to prevent
    SQL injection attacks. Never directly interpolate user input into SQL.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine

__all__ = [
    "build_stread_sql",
    "escape_path",
    "escape_sql_string",
    "escape_wkt",
    "validate_sql_identifier",
    "wrap_geometry",
]


def escape_sql_string(value: str) -> str:
    """Escape a string value for safe SQL embedding.

    This handles the standard SQL escaping of single quotes by doubling them.
    Use this for any string value that will be embedded in SQL.

    Args:
        value: The string value to escape

    Returns:
        Escaped string safe for SQL embedding (without surrounding quotes)

    Example:
        >>> escape_sql_string("normal")
        "normal"
        >>> escape_sql_string("it's")
        "it''s"
        >>> escape_sql_string("'; DROP TABLE users; --")
        "'''; DROP TABLE users; --"
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected string, got {type(value).__name__}")
    return value.replace("'", "''")


def escape_path(path: str) -> str:
    """Escape a file path for safe SQL embedding.

    This escapes special characters that could cause SQL injection
    when embedding file paths in SQL statements.

    Args:
        path: The file path to escape

    Returns:
        Escaped path safe for SQL embedding

    Example:
        >>> escape_path("/home/user/file.parquet")
        "/home/user/file.parquet"
        >>> escape_path("/home/user/file's.parquet")
        "/home/user/file''s.parquet"
    """
    return escape_sql_string(path)


def escape_wkt(wkt: str) -> str:
    """Escape single quotes in WKT strings for safe SQL embedding.

    Args:
        wkt: WKT geometry string

    Returns:
        Escaped WKT string safe for SQL embedding

    Example:
        >>> escape_wkt("POINT(0 0)")
        "POINT(0 0)"
        >>> escape_wkt("POINT('test')")  # Edge case
        "POINT(''test'')"
    """
    return escape_sql_string(wkt)


# Pattern for valid SQL identifiers (alphanumeric + underscore, not starting with digit)
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_sql_identifier(
    name: str,
    kind: str = "identifier",
    error_type: Literal["ValueError", "InvalidURIError"] = "ValueError",
) -> str:
    """Validate a SQL identifier to prevent injection attacks.

    SQL identifiers (table names, column names, schema names) must:
    - Not be empty
    - Start with a letter or underscore
    - Contain only letters, digits, and underscores

    Args:
        name: The identifier to validate
        kind: Description for error messages (e.g., 'column', 'table', 'schema')
        error_type: Type of error to raise ('ValueError' or 'InvalidURIError')

    Returns:
        The validated identifier (unchanged if valid)

    Raises:
        ValueError: If the identifier is invalid and error_type='ValueError'
        InvalidURIError: If the identifier is invalid and error_type='InvalidURIError'

    Example:
        >>> validate_sql_identifier("my_column")
        "my_column"
        >>> validate_sql_identifier("123bad")  # Raises ValueError
    """
    if not name:
        msg = f"Empty {kind} name"
        if error_type == "InvalidURIError":
            from geofabric.errors import InvalidURIError

            raise InvalidURIError(msg)
        raise ValueError(msg)

    if _IDENTIFIER_PATTERN.match(name):
        return name

    msg = (
        f"Invalid {kind} name '{name}'. Must contain only letters, digits, "
        "and underscores, and cannot start with a digit."
    )
    if error_type == "InvalidURIError":
        from geofabric.errors import InvalidURIError

        raise InvalidURIError(msg)
    raise ValueError(msg)


def wrap_geometry(geometry_col: str, func: str | None = None) -> str:
    """Wrap a geometry column with ST_GeomFromWKB and optional spatial function.

    This standardizes the common pattern of accessing geometry stored as WKB
    and optionally applying a spatial function.

    Args:
        geometry_col: Name of the geometry column (validated as SQL identifier)
        func: Optional spatial function to apply (e.g., 'ST_Area', 'ST_Centroid')

    Returns:
        SQL expression string

    Raises:
        ValueError: If geometry_col or func is not a valid SQL identifier

    Example:
        >>> wrap_geometry("geometry")
        "ST_GeomFromWKB(geometry)"
        >>> wrap_geometry("geometry", "ST_Area")
        "ST_Area(ST_GeomFromWKB(geometry))"
    """
    # Validate inputs to prevent SQL injection
    validate_sql_identifier(geometry_col, "geometry column")
    if func:
        validate_sql_identifier(func, "spatial function")

    base = f"ST_GeomFromWKB({geometry_col})"
    if func:
        return f"{func}({base})"
    return base


def build_stread_sql(engine: DuckDBEngine, path: str) -> str:
    """Build SQL for reading spatial file formats using DuckDB's ST_Read.

    This is a centralized function that eliminates code duplication across
    source classes. It handles:
    - Loading the spatial extension
    - Normalizing geometry column names
    - Converting to WKB format
    - Escaping the path safely

    Args:
        engine: The DuckDB engine instance
        path: Path or URL to the spatial file

    Returns:
        SQL expression usable in a FROM clause

    Example:
        >>> sql = build_stread_sql(engine, "/path/to/file.geojson")
        >>> # Returns SQL like:
        >>> # "(SELECT COLUMNS(c -> c NOT IN ('geom')), ST_AsWKB(geom) AS geometry FROM ST_Read('/path/to/file.geojson'))"
    """
    engine._ensure_spatial()
    escaped_path = escape_path(path)
    # ST_Read always creates a 'geom' column for the geometry
    # Use COLUMNS with lambda filter to exclude it, then convert to WKB as 'geometry'
    return (
        "(SELECT "  # nosec B608 - path is escaped via escape_path()
        "  COLUMNS(c -> c NOT IN ('geom')), "
        "  ST_AsWKB(geom) AS geometry "
        f"FROM ST_Read('{escaped_path}'))"
    )


def build_parquet_sql(
    path: str,
    engine: "DuckDBEngine | None" = None,
    geometry_col: str = "geometry",
) -> str:
    """Build SQL for reading parquet files.

    Args:
        path: Path or URL to the parquet file (can include globs)
        engine: Optional DuckDB engine for geometry normalization.
                If provided, will normalize GEOMETRY columns to WKB_BLOB
                for consistent handling (e.g., GeoParquet files from geopandas).
        geometry_col: Name of the geometry column to normalize (default: "geometry")

    Returns:
        SQL expression usable in a FROM clause

    Example:
        >>> build_parquet_sql("/data/*.parquet")
        "read_parquet('/data/*.parquet')"

    Note:
        Parquet files can have geometry in different formats:
        - BLOB: Raw WKB bytes (works directly with ST_GeomFromWKB)
        - GEOMETRY: DuckDB's native type (from GeoParquet/geopandas)

        When engine is provided, we detect the type and normalize:
        - GEOMETRY → ST_AsWKB(geometry) to convert to WKB_BLOB
        - BLOB → passed through unchanged (already compatible)
    """
    escaped_path = escape_path(path)
    base_sql = f"read_parquet('{escaped_path}')"

    if engine is None:
        return base_sql

    engine._ensure_spatial()
    validate_sql_identifier(geometry_col, "geometry column")

    # Check the actual column type in the parquet file
    # This is necessary because CASE WHEN is checked at compile-time
    try:
        schema_sql = f"""
            SELECT column_type
            FROM (DESCRIBE SELECT * FROM {base_sql} LIMIT 1)
            WHERE column_name = '{geometry_col}'
        """  # nosec B608 - geometry_col is validated above
        result = engine.con().execute(schema_sql).fetchone()

        if result and result[0] == "GEOMETRY":
            # GeoParquet file: convert GEOMETRY to WKB_BLOB
            return (
                "(SELECT "  # nosec B608 - path escaped, geometry_col validated
                f"  COLUMNS(c -> c != '{geometry_col}'), "
                f"  ST_AsWKB({geometry_col}) AS {geometry_col} "
                f"FROM {base_sql})"
            )
    except Exception:
        # If schema detection fails (e.g., glob patterns), fall through
        pass

    # BLOB type or detection failed: pass through unchanged
    # BLOB is compatible with ST_GeomFromWKB
    return base_sql


def build_csv_sql(engine: DuckDBEngine, path: str, geometry_col: str = "geometry") -> str:
    """Build SQL for reading CSV files with WKT geometry.

    CSV files are read using read_csv, and the geometry column (containing WKT)
    is converted to geometry using ST_GeomFromText.

    Args:
        engine: The DuckDB engine instance
        path: Path to the CSV file
        geometry_col: Name of the column containing WKT geometry (default: "geometry")

    Returns:
        SQL expression usable in a FROM clause

    Example:
        >>> sql = build_csv_sql(engine, "/path/to/file.csv")
        >>> # Returns SQL that reads CSV and converts WKT to geometry
    """
    engine._ensure_spatial()
    escaped_path = escape_path(path)
    validate_sql_identifier(geometry_col, "geometry column")
    # Read CSV and convert WKT geometry column to WKB
    return (
        "(SELECT "  # nosec B608 - path escaped, geometry_col validated
        f"  COLUMNS(c -> c NOT IN ('{geometry_col}')), "
        f"  ST_AsWKB(ST_GeomFromText({geometry_col})) AS geometry "
        f"FROM read_csv('{escaped_path}'))"
    )


class DuckDBConfigBuilder:
    """Builder for safely configuring DuckDB connection settings.

    This class encapsulates the pattern of setting DuckDB configuration
    values safely, with proper escaping to prevent SQL injection.

    Example:
        >>> builder = DuckDBConfigBuilder(engine)
        >>> builder.set("s3_access_key_id", access_key)
        >>> builder.set("s3_region", region)
        >>> builder.set_bool("s3_use_ssl", use_ssl)
    """

    def __init__(self, engine: DuckDBEngine) -> None:
        self._engine = engine

    def set(self, key: str, value: str | None) -> DuckDBConfigBuilder:
        """Set a string configuration value if not None.

        Args:
            key: The configuration key (validated as identifier)
            value: The value to set (will be escaped)

        Returns:
            self for chaining
        """
        if value is not None:
            # Validate key is a safe identifier
            validate_sql_identifier(key, "configuration key")
            escaped_value = escape_sql_string(value)
            self._engine.con().execute(f"SET {key}='{escaped_value}';")  # nosemgrep
        return self

    def set_bool(self, key: str, value: bool) -> DuckDBConfigBuilder:
        """Set a boolean configuration value.

        Args:
            key: The configuration key (validated as identifier)
            value: Boolean value

        Returns:
            self for chaining
        """
        validate_sql_identifier(key, "configuration key")
        self._engine.con().execute(f"SET {key}={str(value).lower()};")  # nosemgrep
        return self

    def load_extension(self, name: str) -> DuckDBConfigBuilder:
        """Install and load a DuckDB extension.

        Args:
            name: Extension name (validated as identifier)

        Returns:
            self for chaining
        """
        validate_sql_identifier(name, "extension name")
        self._engine.con().execute(f"INSTALL {name};")  # nosemgrep
        self._engine.con().execute(f"LOAD {name};")  # nosemgrep
        return self
