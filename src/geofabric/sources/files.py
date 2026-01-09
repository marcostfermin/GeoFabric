from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from geofabric.errors import EngineError, InvalidURIError
from geofabric.sql_utils import build_csv_sql, build_parquet_sql, build_stread_sql

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine


@dataclass(frozen=True)
class FilesSource:
    """Source for local file data.

    Implements SourceWithDuckDBRelation protocol for DuckDB integration.
    """

    path: str

    def __post_init__(self) -> None:
        """Validate file path on initialization.

        Ensures:
        - Path is not empty
        - Path doesn't contain path traversal patterns (..)
        """
        if not self.path:
            raise InvalidURIError("Path cannot be empty")

        # Check for path traversal attempts
        if ".." in self.path:
            raise InvalidURIError(
                f"Invalid path: path traversal not allowed (found '..' in '{self.path}')"
            )

    def source_kind(self) -> str:
        return "files"

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from local files.

        Implements SourceWithDuckDBRelation protocol.
        Uses centralized SQL builders for security and consistency.
        """
        p = Path(self.path).expanduser().resolve()

        if p.is_dir():
            glob = str(p / "*.parquet")
            return build_parquet_sql(glob, engine=engine)

        if p.is_file():
            suffix = p.suffix.lower()
            if suffix in (".parquet", ".pq"):
                return build_parquet_sql(str(p), engine=engine)
            if suffix == ".csv":
                # CSV files with WKT geometry need special handling
                return build_csv_sql(engine, str(p))
            if suffix in (".geojson", ".json", ".gpkg", ".shp", ".fgb"):
                return build_stread_sql(engine, str(p))
            raise EngineError(f"Unsupported file type: {suffix}")

        raise EngineError(f"Path not found: {p}")

    @staticmethod
    def from_uri(uri: str) -> FilesSource:
        """Parse a file URI or local path.

        Formats:
            file:///path/to/file.parquet
            /path/to/file.parquet
            ./relative/path.parquet
            ~/home/path.parquet
        """
        parsed = urlparse(uri)

        if parsed.scheme == "file":
            path = parsed.path
        elif parsed.scheme == "":
            # Plain path (no scheme)
            path = uri
        else:
            raise InvalidURIError(f"Not a file URI: {uri}")

        if not path:
            raise InvalidURIError(f"Invalid file URI: {uri}")

        # Expand and resolve the path
        resolved = Path(path).expanduser().resolve()
        return FilesSource(str(resolved))

    def uri(self) -> str:
        """Return the file URI following RFC 8089."""
        return Path(self.path).as_uri()


from geofabric.registry import SourceClassFactory

# Use generic factory instead of boilerplate class
FilesSourceFactory = SourceClassFactory(FilesSource)
