from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, quote_plus, urlparse

from geofabric.errors import InvalidURIError
from geofabric.sql_utils import escape_sql_string, validate_sql_identifier

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine


# Valid PostgreSQL sslmode values
_VALID_SSLMODES = frozenset({"disable", "allow", "prefer", "require", "verify-ca", "verify-full"})


@dataclass(frozen=True)
class PostGISSource:
    """Source for PostGIS database tables."""

    host: str
    port: int
    database: str
    user: str
    password: str
    table: str | None = None
    schema: str = "public"
    geometry_column: str = "geom"
    sslmode: str | None = None

    def __post_init__(self) -> None:
        """Validate PostGIS source parameters on initialization.

        Validates:
        - Port is in valid range (1-65535)
        - Schema name is a valid SQL identifier
        - Geometry column is a valid SQL identifier
        - Table name is a valid SQL identifier (if provided)
        - sslmode is one of the valid PostgreSQL sslmode values
        """
        # Validate port range
        if not (1 <= self.port <= 65535):
            raise InvalidURIError(f"Port must be between 1 and 65535, got {self.port}")

        # Validate SQL identifiers to prevent injection
        validate_sql_identifier(self.schema, "schema", "InvalidURIError")
        validate_sql_identifier(self.geometry_column, "geometry_column", "InvalidURIError")

        if self.table:
            validate_sql_identifier(self.table, "table", "InvalidURIError")

        # Validate sslmode if provided
        if self.sslmode is not None and self.sslmode not in _VALID_SSLMODES:
            raise InvalidURIError(
                f"Invalid sslmode '{self.sslmode}'. Must be one of: {sorted(_VALID_SSLMODES)}"
            )

    def source_kind(self) -> str:
        return "postgis"

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from PostGIS.

        Implements SourceWithDuckDBRelation protocol.
        Uses safe escaping to prevent SQL injection in connection strings.
        """
        from geofabric.sql_utils import DuckDBConfigBuilder

        engine._ensure_spatial()

        # Use config builder for safe extension loading
        config_builder = DuckDBConfigBuilder(engine)
        config_builder.load_extension("postgres")

        # Build connection string with proper escaping
        # Note: libpq connection strings use different escaping than SQL
        # We escape single quotes in the outer SQL ATTACH statement
        conn_parts = [
            f"host={self._escape_connstr_value(self.host)}",
            f"port={self.port}",
            f"dbname={self._escape_connstr_value(self.database)}",
            f"user={self._escape_connstr_value(self.user)}",
            f"password={self._escape_connstr_value(self.password)}",
        ]
        if self.sslmode:
            conn_parts.append(f"sslmode={self.sslmode}")

        conn_str = " ".join(conn_parts)
        # Escape for SQL string embedding
        escaped_conn_str = escape_sql_string(conn_str)

        # Check if already attached (avoid duplicate attach error)
        try:
            attached = engine.con().execute("SELECT database_name FROM duckdb_databases()").fetchdf()
            if "pg" not in attached["database_name"].tolist():
                engine.con().execute(f"ATTACH '{escaped_conn_str}' AS pg (TYPE POSTGRES, READ_ONLY);")  # nosemgrep
        except Exception:
            # If check fails, try to attach (will fail if already attached)
            try:
                engine.con().execute(f"ATTACH '{escaped_conn_str}' AS pg (TYPE POSTGRES, READ_ONLY);")  # nosemgrep
            except Exception:
                pass  # Already attached, ignore

        # Schema and table are validated in __post_init__
        table_ref = f"pg.{self.schema}.{self.table}"
        # geometry_column is validated in __post_init__
        # PostGIS geometry comes through DuckDB's postgres extension as WKB_BLOB already
        # No conversion needed, just ensure consistent naming
        if self.geometry_column == "geometry":
            return f"{table_ref}"  # nosec B608
        # Rename geometry column to 'geometry' (exclude original to avoid duplicate)
        return (
            "(SELECT "  # nosec B608
            f"  COLUMNS(c -> c != '{self.geometry_column}'), "
            f"  {self.geometry_column} AS geometry "
            f"FROM {table_ref})"
        )

    @staticmethod
    def _escape_connstr_value(value: str) -> str:
        """Escape a value for PostgreSQL connection string.

        In libpq connection strings, values containing spaces or special
        characters should be enclosed in single quotes, and single quotes
        within the value should be escaped with backslash.
        """
        if not value:
            return "''"
        # If value contains spaces, quotes, or backslashes, quote it
        if any(c in value for c in " '\\"):
            # Escape backslashes first, then single quotes
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
        return value

    @staticmethod
    def from_uri(uri: str) -> PostGISSource:
        """Parse a PostGIS URI.

        Format: postgresql://user:pass@host:port/database?table=<name>&schema=<schema>
        """
        parsed = urlparse(uri)
        if parsed.scheme not in ("postgresql", "postgis", "postgres"):
            raise InvalidURIError(f"Not a PostGIS URI: {uri}")

        if not parsed.hostname:
            raise InvalidURIError(f"Missing host in PostGIS URI: {uri}")
        if not parsed.path or parsed.path == "/":
            raise InvalidURIError(f"Missing database in PostGIS URI: {uri}")

        qs = parse_qs(parsed.query)
        table = qs.get("table", [None])[0]
        schema = qs.get("schema", ["public"])[0]
        geometry_column = qs.get("geometry_column", ["geom"])[0]

        sslmode = qs.get("sslmode", [None])[0]

        # Validate sslmode if provided (also validated in __post_init__ for direct instantiation)
        if sslmode and sslmode not in _VALID_SSLMODES:
            raise InvalidURIError(
                f"Invalid sslmode '{sslmode}'. Must be one of: {sorted(_VALID_SSLMODES)}"
            )

        return PostGISSource(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            user=parsed.username or "",
            password=parsed.password or "",
            table=table,
            schema=schema,
            geometry_column=geometry_column,
            sslmode=sslmode,
        )

    def __repr__(self) -> str:
        """Return string representation with password redacted."""
        return (
            f"PostGISSource(host={self.host!r}, port={self.port}, "
            f"database={self.database!r}, user={self.user!r}, "
            f"password={'***' if self.password else None!r}, "
            f"table={self.table!r}, schema={self.schema!r}, "
            f"geometry_column={self.geometry_column!r}, sslmode={self.sslmode!r})"
        )

    def connection_string(self, *, redact_password: bool = False) -> str:
        """Return DuckDB-compatible PostgreSQL connection string.

        Args:
            redact_password: If True, replace password with '***' (for logging/display)

        Returns:
            PostgreSQL connection string URL

        Security Note:
            The default behavior returns the actual password for internal use.
            Use redact_password=True when displaying or logging connection strings.
        """
        # URL-encode password to handle special characters
        if redact_password:
            encoded_password = "***" if self.password else ""
        else:
            encoded_password = quote_plus(self.password) if self.password else ""
        encoded_user = quote_plus(self.user) if self.user else ""
        base = f"postgresql://{encoded_user}:{encoded_password}@{self.host}:{self.port}/{self.database}"
        if self.sslmode:
            base += f"?sslmode={self.sslmode}"
        return base

    def qualified_table_name(self) -> str:
        """Return schema-qualified table name.

        Raises:
            InvalidURIError: If no table specified or names are invalid
        """
        if not self.table:
            raise InvalidURIError("No table specified in PostGIS URI")

        # Validate both schema and table names using centralized validator
        validated_schema = validate_sql_identifier(self.schema, "schema", "InvalidURIError")
        validated_table = validate_sql_identifier(self.table, "table", "InvalidURIError")

        return f"{validated_schema}.{validated_table}"


from geofabric.registry import SourceClassFactory

# Use generic factory instead of boilerplate class
PostGISSourceFactory = SourceClassFactory(PostGISSource)
