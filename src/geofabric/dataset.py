from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import pandas as pd

from geofabric.config import get_config
from geofabric.engines.duckdb_engine import DuckDBEngine
from geofabric.errors import InvalidURIError
from geofabric.query import Query
from geofabric.roi import ROI
from geofabric.sources.files import FilesSource
from geofabric.sources.overture import OvertureSource

if TYPE_CHECKING:
    from geofabric.validation import DatasetStats, ValidationResult

__all__ = ["Dataset", "open"]


@dataclass
class Dataset:
    source: object
    engine: DuckDBEngine

    def query(self) -> Query:
        return Query(dataset=self)

    def within(self, roi: ROI) -> Query:
        return self.query().within(roi)

    def where(self, sql_predicate: str) -> Query:
        if not sql_predicate or not sql_predicate.strip():
            raise ValueError("sql_predicate must not be empty")
        return self.query().where(sql_predicate)

    def select(self, columns: str | Sequence[str]) -> Query:
        return self.query().select(columns)

    def limit(self, n: int) -> Query:
        if n < 0:
            raise ValueError(f"limit must be >= 0, got {n}")
        return self.query().limit(n)

    @property
    def columns(self) -> list[str]:
        """Return list of column names."""
        return self.query().columns

    @property
    def dtypes(self) -> dict[str, str]:
        """Return mapping of column names to data types."""
        return self.query().dtypes

    def count(self) -> int:
        """Return the total number of rows."""
        return self.query().count()

    def head(self, n: int = 10) -> pd.DataFrame:
        """Return the first n rows."""
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        return self.query().head(n)

    def tail(self, n: int = 10) -> pd.DataFrame:
        """Return the last n rows."""
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        return self.query().tail(n)

    def sample(self, n: int = 10, seed: int | None = None) -> pd.DataFrame:
        """Return a random sample of n rows."""
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        return self.query().sample(n, seed)

    def validate(
        self,
        geometry_col: str = "geometry",
        id_col: str | None = None,
    ) -> ValidationResult:
        """Validate geometries in the dataset."""
        from geofabric.validation import validate_geometries

        return validate_geometries(
            self.engine,
            self.query().sql(),
            geometry_col=geometry_col,
            id_col=id_col,
        )

    def stats(self, geometry_col: str = "geometry") -> DatasetStats:
        """Compute statistics for the dataset."""
        from geofabric.validation import compute_stats

        return compute_stats(self.engine, self.query().sql(), geometry_col)


def open(uri: str, *, engine: DuckDBEngine | None = None) -> Dataset:
    engine = engine or DuckDBEngine()

    if uri.startswith("overture://"):
        src = OvertureSource.from_uri(uri)
        return Dataset(source=src, engine=engine)

    parsed = urlparse(uri)

    # Handle local files
    if parsed.scheme in ("file", ""):
        path = parsed.path if parsed.scheme == "file" else uri
        if not path:
            raise InvalidURIError(f"Invalid file URI: {uri}")
        p = Path(path).expanduser().resolve()
        if not p.exists():
            raise InvalidURIError(f"Path does not exist: {p}")
        return Dataset(source=FilesSource(str(p)), engine=engine)

    # Handle S3 URIs
    if parsed.scheme == "s3":
        from geofabric.sources.cloud import S3Source

        # Parse query params for S3-specific options
        query_params = parse_qs(parsed.query)
        region = query_params.get("region", [None])[0]
        anonymous = query_params.get("anonymous", ["true"])[0].lower() == "true"

        # Use from_uri for base parsing, then add options
        s3_src = S3Source(
            bucket=parsed.netloc,
            key=parsed.path.lstrip("/"),
            region=region,
            anonymous=anonymous,
        )
        return Dataset(source=s3_src, engine=engine)

    # Handle GCS URIs
    if parsed.scheme in ("gs", "gcs"):
        from geofabric.sources.cloud import GCSSource

        gcs_src = GCSSource.from_uri(uri)
        return Dataset(source=gcs_src, engine=engine)

    # Handle Azure Blob Storage URIs
    if parsed.scheme in ("az", "azure"):
        from geofabric.sources.cloud import AzureSource

        azure_src = AzureSource.from_uri(uri)
        # Apply account_name from config if not in source
        if not azure_src.account_name:
            config = get_config()
            if config.azure.account_name:
                azure_src = AzureSource(
                    container=azure_src.container,
                    blob=azure_src.blob,
                    account_name=config.azure.account_name,
                )
        return Dataset(source=azure_src, engine=engine)

    # Handle STAC URIs (stac://catalog-url/path?collection=name&bbox=...)
    if parsed.scheme == "stac":
        from geofabric.sources.stac import STACSource

        stac_src = STACSource.from_uri(uri)
        return Dataset(source=stac_src, engine=engine)

    # Handle PostGIS URIs (postgresql://user:pass@host:port/dbname?table=foo)
    if parsed.scheme in ("postgresql", "postgres", "postgis"):
        from geofabric.sources.postgis import PostGISSource

        query_params = parse_qs(parsed.query)
        table = query_params.get("table", [None])[0]
        schema = query_params.get("schema", ["public"])[0]
        geometry_column = query_params.get("geometry_column", ["geom"])[0]
        sslmode = query_params.get("sslmode", [None])[0]
        if not table:
            raise InvalidURIError("PostGIS URI requires ?table=tablename")

        # Use programmatic config as defaults when URI params not specified
        config = get_config()
        postgis_src = PostGISSource(
            host=parsed.hostname or config.postgis.host or "localhost",
            port=parsed.port or config.postgis.port or 5432,
            database=parsed.path.lstrip("/") or config.postgis.database or "",
            user=parsed.username or config.postgis.user or "",
            password=parsed.password or config.postgis.password or "",
            table=table,
            schema=schema,
            geometry_column=geometry_column,
            sslmode=sslmode or config.postgis.sslmode,
        )
        return Dataset(source=postgis_src, engine=engine)

    raise InvalidURIError(f"Unsupported URI scheme: {uri}")
