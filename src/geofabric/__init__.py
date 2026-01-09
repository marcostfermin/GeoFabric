from geofabric import roi
from geofabric._version import __version__
from geofabric.cache import configure_cache, get_cache
from geofabric.config import (
    configure_azure,
    configure_gcs,
    configure_http,
    configure_postgis,
    configure_s3,
    configure_stac,
    get_config,
    reset_config,
)
from geofabric.dataset import Dataset, open
from geofabric.engines.duckdb_engine import DuckDBEngine
from geofabric.query import Query
from geofabric.validation import (
    DatasetStats,
    ValidationIssue,
    ValidationResult,
    compute_stats,
    validate_geometries,
)

__all__ = [
    "Dataset",
    "DatasetStats",
    "DuckDBEngine",
    "Query",
    "ValidationIssue",
    "ValidationResult",
    "__version__",
    "compute_stats",
    "configure_azure",
    "configure_cache",
    "configure_gcs",
    "configure_http",
    "configure_postgis",
    "configure_s3",
    "configure_stac",
    "get_cache",
    "get_config",
    "open",
    "reset_config",
    "roi",
    "validate_geometries",
]
