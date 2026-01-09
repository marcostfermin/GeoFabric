from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from geofabric.errors import InvalidURIError
from geofabric.sql_utils import (
    DuckDBConfigBuilder,
    build_parquet_sql,
    build_stread_sql,
)

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine


def _validate_bucket_name(name: str, kind: str = "bucket") -> str:
    """Validate cloud storage bucket/container name.

    Cloud storage names typically must:
    - Not be empty
    - Not contain path traversal sequences
    - Not contain dangerous characters

    Args:
        name: The bucket/container name to validate
        kind: Description for error messages

    Returns:
        The validated name

    Raises:
        InvalidURIError: If the name is invalid
    """
    if not name:
        raise InvalidURIError(f"Empty {kind} name")

    # Check for path traversal attempts
    if ".." in name or name.startswith("/") or name.startswith("\\"):
        raise InvalidURIError(f"Invalid {kind} name: {name}")

    return name


def _validate_key_path(key: str, kind: str = "key") -> str:
    """Validate cloud storage key/blob path.

    Args:
        key: The object key/blob path to validate
        kind: Description for error messages

    Returns:
        The validated key

    Raises:
        InvalidURIError: If the key is invalid
    """
    # Keys can be empty (bucket root) but shouldn't have dangerous patterns
    if key.startswith("/"):
        key = key.lstrip("/")  # Normalize leading slashes

    # Check for path traversal attempts
    if ".." in key:
        raise InvalidURIError(f"Invalid {kind} path: path traversal not allowed")

    return key


@dataclass(frozen=True)
class S3Source:
    """Source for AWS S3 data."""

    bucket: str
    key: str
    region: str | None = None
    anonymous: bool = True

    def source_kind(self) -> str:
        return "s3"

    def __post_init__(self) -> None:
        """Validate bucket and key on initialization."""
        _validate_bucket_name(self.bucket, "bucket")
        _validate_key_path(self.key, "key")

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from S3.

        Implements SourceWithDuckDBRelation protocol.
        Uses DuckDBConfigBuilder for safe credential configuration.
        """
        from geofabric.config import get_config

        # Configure httpfs for S3 access using safe builder pattern
        config_builder = DuckDBConfigBuilder(engine)
        config_builder.load_extension("httpfs")

        # Apply programmatic credentials if configured (safely escaped)
        config = get_config()
        config_builder.set("s3_access_key_id", config.s3.access_key_id)
        config_builder.set("s3_secret_access_key", config.s3.secret_access_key)
        config_builder.set("s3_session_token", config.s3.session_token)
        config_builder.set("s3_endpoint", config.s3.endpoint)

        # Apply SSL setting
        if not config.s3.use_ssl:
            config_builder.set_bool("s3_use_ssl", False)

        # Apply source-specific settings
        if self.anonymous:
            config_builder.set("s3_url_style", "path")

        # Region: source-specific > config > default
        region = self.region or config.s3.region
        config_builder.set("s3_region", region)

        s3_url = f"s3://{self.bucket}/{self.key}"
        if self.key.endswith(".parquet") or self.key.endswith(".pq"):
            return build_parquet_sql(s3_url)
        return build_stread_sql(engine, s3_url)

    @staticmethod
    def from_uri(uri: str) -> S3Source:
        """Parse an S3 URI.

        Format: s3://bucket/path/to/file.parquet
        """
        parsed = urlparse(uri)
        if parsed.scheme != "s3":
            raise InvalidURIError(f"Not an S3 URI: {uri}")

        if not parsed.netloc:
            raise InvalidURIError(f"Missing bucket in S3 URI: {uri}")

        return S3Source(
            bucket=parsed.netloc,
            key=parsed.path.lstrip("/"),
        )

    def to_duckdb_path(self) -> str:
        """Return DuckDB-compatible S3 path."""
        return f"s3://{self.bucket}/{self.key}"

    def uri(self) -> str:
        """Return the S3 URI."""
        return f"s3://{self.bucket}/{self.key}"


@dataclass(frozen=True)
class GCSSource:
    """Source for Google Cloud Storage data."""

    bucket: str
    key: str

    def source_kind(self) -> str:
        return "gcs"

    def __post_init__(self) -> None:
        """Validate bucket and key on initialization."""
        _validate_bucket_name(self.bucket, "bucket")
        _validate_key_path(self.key, "key")

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from GCS.

        Implements SourceWithDuckDBRelation protocol.
        Uses DuckDBConfigBuilder for safe credential configuration.
        """
        from geofabric.config import get_config

        # Configure httpfs using safe builder pattern
        config_builder = DuckDBConfigBuilder(engine)
        config_builder.load_extension("httpfs")

        # Apply programmatic credentials if configured (safely escaped)
        config = get_config()
        config_builder.set("s3_access_key_id", config.gcs.access_key_id)
        config_builder.set("s3_secret_access_key", config.gcs.secret_access_key)

        # Set GCS endpoint for DuckDB httpfs
        config_builder.set("s3_endpoint", "storage.googleapis.com")
        config_builder.set("s3_url_style", "path")

        gcs_url = f"gs://{self.bucket}/{self.key}"
        if self.key.endswith(".parquet") or self.key.endswith(".pq"):
            return build_parquet_sql(gcs_url)
        return build_stread_sql(engine, gcs_url)

    @staticmethod
    def from_uri(uri: str) -> GCSSource:
        """Parse a GCS URI.

        Format: gs://bucket/path/to/file.parquet
        """
        parsed = urlparse(uri)
        if parsed.scheme not in ("gs", "gcs"):
            raise InvalidURIError(f"Not a GCS URI: {uri}")

        if not parsed.netloc:
            raise InvalidURIError(f"Missing bucket in GCS URI: {uri}")

        return GCSSource(
            bucket=parsed.netloc,
            key=parsed.path.lstrip("/"),
        )

    def to_duckdb_path(self) -> str:
        """Return DuckDB-compatible GCS path."""
        return f"gcs://{self.bucket}/{self.key}"

    def uri(self) -> str:
        """Return the GCS URI."""
        return f"gs://{self.bucket}/{self.key}"


from geofabric.registry import SourceClassFactory

# Use generic factory instead of boilerplate classes
S3SourceFactory = SourceClassFactory(S3Source)
GCSSourceFactory = SourceClassFactory(GCSSource)


@dataclass(frozen=True)
class AzureSource:
    """Source for Azure Blob Storage data."""

    container: str
    blob: str
    account_name: str | None = None

    def source_kind(self) -> str:
        return "azure"

    def __post_init__(self) -> None:
        """Validate container and blob on initialization."""
        _validate_bucket_name(self.container, "container")
        _validate_key_path(self.blob, "blob")

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from Azure Blob Storage.

        Implements SourceWithDuckDBRelation protocol.
        Uses DuckDBConfigBuilder for safe credential configuration.
        """
        from geofabric.config import get_config

        # Configure azure extension using safe builder pattern
        config_builder = DuckDBConfigBuilder(engine)
        config_builder.load_extension("azure")

        # Apply programmatic credentials if configured (safely escaped)
        # DuckDB Azure extension uses these config names (not azure_storage_*)
        config = get_config()
        if config.azure.connection_string:
            config_builder.set(
                "azure_connection_string", config.azure.connection_string
            )
        else:
            config_builder.set("azure_account_name", config.azure.account_name)
            config_builder.set("azure_account_key", config.azure.account_key)

            if config.azure.sas_token:
                # SAS token requires building a connection string with account name
                account = config.azure.account_name or self.account_name
                if not account:
                    raise InvalidURIError(
                        "Azure SAS token authentication requires account_name. "
                        "Set it via AzureSource(account_name=...) or configure_azure(account_name=...)"
                    )
                sas_conn = (
                    f"BlobEndpoint=https://{account}.blob.core.windows.net;"
                    f"SharedAccessSignature={config.azure.sas_token}"
                )
                config_builder.set("azure_connection_string", sas_conn)

        azure_url = f"az://{self.container}/{self.blob}"
        if self.blob.endswith(".parquet") or self.blob.endswith(".pq"):
            return build_parquet_sql(azure_url)
        return build_stread_sql(engine, azure_url)

    @staticmethod
    def from_uri(uri: str) -> AzureSource:
        """Parse an Azure Blob Storage URI.

        Format: az://container/path/to/file.parquet
                azure://container/path/to/file.parquet
        """
        parsed = urlparse(uri)
        if parsed.scheme not in ("az", "azure"):
            raise InvalidURIError(f"Not an Azure URI: {uri}")

        if not parsed.netloc:
            raise InvalidURIError(f"Missing container in Azure URI: {uri}")

        return AzureSource(
            container=parsed.netloc,
            blob=parsed.path.lstrip("/"),
        )

    def to_duckdb_path(self) -> str:
        """Return DuckDB-compatible Azure path."""
        return f"az://{self.container}/{self.blob}"

    def uri(self) -> str:
        """Return the Azure URI."""
        return f"az://{self.container}/{self.blob}"


AzureSourceFactory = SourceClassFactory(AzureSource)
