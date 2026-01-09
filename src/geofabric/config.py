"""
Configuration module for GeoFabric credentials and settings.

Provides programmatic configuration as an alternative to environment variables.
Following industry best practices similar to boto3, Google Cloud SDK, and other
standard libraries.

Security:
    - All config values are validated on creation
    - Port numbers must be in valid range (1-65535)
    - Timeouts must be positive
    - SSL modes must be valid PostgreSQL values
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from geofabric.errors import ConfigurationError

__all__ = [
    "configure_azure",
    "configure_gcs",
    "configure_http",
    "configure_postgis",
    "configure_s3",
    "configure_stac",
    "get_config",
    "reset_config",
    "temporary_config",
]


# Valid PostgreSQL SSL modes
_VALID_SSLMODES = frozenset({"disable", "allow", "prefer", "require", "verify-ca", "verify-full"})


def _validate_port(port: int | None, field_name: str = "port") -> int | None:
    """Validate port number is in valid range.

    Args:
        port: Port number to validate (can be None)
        field_name: Name for error messages

    Returns:
        The validated port

    Raises:
        ConfigurationError: If port is out of range
    """
    if port is not None and not (1 <= port <= 65535):
        raise ConfigurationError(f"{field_name} must be between 1 and 65535, got {port}")
    return port


def _validate_timeout(timeout: int, field_name: str = "timeout") -> int:
    """Validate timeout is non-negative.

    Args:
        timeout: Timeout value to validate
        field_name: Name for error messages

    Returns:
        The validated timeout

    Raises:
        ConfigurationError: If timeout is negative
    """
    if timeout < 0:
        raise ConfigurationError(f"{field_name} must be non-negative, got {timeout}")
    return timeout


def _validate_sslmode(sslmode: str | None) -> str | None:
    """Validate PostgreSQL SSL mode.

    Args:
        sslmode: SSL mode to validate (can be None)

    Returns:
        The validated SSL mode

    Raises:
        ConfigurationError: If SSL mode is invalid
    """
    if sslmode is not None and sslmode not in _VALID_SSLMODES:
        raise ConfigurationError(
            f"Invalid sslmode '{sslmode}'. Must be one of: {sorted(_VALID_SSLMODES)}"
        )
    return sslmode


def _validate_url(url: str | None, field_name: str = "url", *, allow_hostport: bool = False) -> str | None:
    """Validate URL format.

    Args:
        url: URL to validate (can be None)
        field_name: Name for error messages
        allow_hostport: If True, allow host:port format without scheme (for endpoints)

    Returns:
        The validated URL

    Raises:
        ConfigurationError: If URL format is invalid
    """
    if url is not None:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            # Full URL with scheme - valid
            return url
        elif allow_hostport and url and not url.startswith("//"):
            # Allow host:port format for endpoints (e.g., "localhost:9000")
            # Basic validation: should have at least one character
            return url
        else:
            raise ConfigurationError(f"Invalid {field_name} format: {url}")
    return url


@dataclass
class S3Config:
    """S3 credential configuration."""

    access_key_id: str | None = None
    secret_access_key: str | None = None
    region: str | None = None
    session_token: str | None = None
    endpoint: str | None = None
    use_ssl: bool = True

    def __post_init__(self) -> None:
        """Validate S3 configuration on creation."""
        # Validate endpoint URL format if provided
        # Allow host:port format for S3-compatible services (MinIO, etc.)
        if self.endpoint:
            _validate_url(self.endpoint, "endpoint", allow_hostport=True)

    def __repr__(self) -> str:
        """Return string representation with sensitive fields redacted."""
        return (
            f"S3Config(access_key_id={'***' if self.access_key_id else None}, "
            f"secret_access_key={'***' if self.secret_access_key else None}, "
            f"region={self.region!r}, "
            f"session_token={'***' if self.session_token else None}, "
            f"endpoint={self.endpoint!r}, use_ssl={self.use_ssl})"
        )


@dataclass
class GCSConfig:
    """GCS credential configuration.

    Note: Both access_key_id and secret_access_key should be provided together
    for HMAC authentication. Partial configuration is allowed since credentials
    may also come from environment variables.
    """

    access_key_id: str | None = None
    secret_access_key: str | None = None
    project: str | None = None

    def __repr__(self) -> str:
        """Return string representation with sensitive fields redacted."""
        return (
            f"GCSConfig(access_key_id={'***' if self.access_key_id else None}, "
            f"secret_access_key={'***' if self.secret_access_key else None}, "
            f"project={self.project!r})"
        )


@dataclass
class AzureConfig:
    """Azure Blob Storage credential configuration."""

    account_name: str | None = None
    account_key: str | None = None
    connection_string: str | None = None
    sas_token: str | None = None

    def __post_init__(self) -> None:
        """Validate Azure configuration on creation.

        Validates that credentials are provided in valid combinations:
        - account_name + account_key together
        - connection_string alone
        - sas_token requires account_name
        """
        has_account_name = self.account_name is not None
        has_account_key = self.account_key is not None
        has_sas_token = self.sas_token is not None
        # Note: connection_string can be used alone without additional validation

        # Account name and key must be provided together
        if has_account_key and not has_account_name:
            raise ConfigurationError(
                "Azure account_key requires account_name to be provided"
            )

        # SAS token requires account_name
        if has_sas_token and not has_account_name:
            raise ConfigurationError(
                "Azure sas_token requires account_name to be provided"
            )

    def __repr__(self) -> str:
        """Return string representation with sensitive fields redacted."""
        return (
            f"AzureConfig(account_name={self.account_name!r}, "
            f"account_key={'***' if self.account_key else None}, "
            f"connection_string={'***' if self.connection_string else None}, "
            f"sas_token={'***' if self.sas_token else None})"
        )


@dataclass
class PostGISConfig:
    """PostGIS default connection configuration."""

    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    password: str | None = None
    sslmode: str | None = None

    def __post_init__(self) -> None:
        """Validate PostGIS configuration on creation."""
        _validate_port(self.port)
        _validate_sslmode(self.sslmode)

    def __repr__(self) -> str:
        """Return string representation with sensitive fields redacted."""
        return (
            f"PostGISConfig(host={self.host!r}, port={self.port!r}, "
            f"database={self.database!r}, user={self.user!r}, "
            f"password={'***' if self.password else None}, "
            f"sslmode={self.sslmode!r})"
        )


@dataclass
class STACConfig:
    """STAC catalog configuration."""

    api_key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    default_catalog: str | None = None

    def __post_init__(self) -> None:
        """Validate STAC configuration on creation."""
        if self.default_catalog:
            _validate_url(self.default_catalog, "default_catalog")

    def __repr__(self) -> str:
        """Return string representation with sensitive fields redacted."""
        # Redact sensitive headers (Authorization, API keys, etc.)
        redacted_headers = {
            k: "***" if any(
                s in k.lower() for s in ["auth", "key", "token", "secret", "credential"]
            ) else v
            for k, v in self.headers.items()
        }
        return (
            f"STACConfig(api_key={'***' if self.api_key else None}, "
            f"headers={redacted_headers!r}, "
            f"default_catalog={self.default_catalog!r})"
        )


@dataclass
class HTTPConfig:
    """HTTP configuration for web requests."""

    proxy: str | None = None
    timeout: int = 30
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        """Validate HTTP configuration on creation."""
        _validate_timeout(self.timeout)
        if self.proxy:
            _validate_url(self.proxy, "proxy")

    def __repr__(self) -> str:
        """Return string representation with sensitive headers redacted."""
        # Redact sensitive headers (Authorization, API keys, etc.)
        redacted_headers = {
            k: "***" if any(
                s in k.lower() for s in ["auth", "key", "token", "secret", "credential"]
            ) else v
            for k, v in self.headers.items()
        }
        return (
            f"HTTPConfig(proxy={self.proxy!r}, timeout={self.timeout}, "
            f"headers={redacted_headers!r}, verify_ssl={self.verify_ssl})"
        )


@dataclass
class GeoFabricConfig:
    """Global GeoFabric configuration."""

    s3: S3Config = field(default_factory=S3Config)
    gcs: GCSConfig = field(default_factory=GCSConfig)
    azure: AzureConfig = field(default_factory=AzureConfig)
    postgis: PostGISConfig = field(default_factory=PostGISConfig)
    stac: STACConfig = field(default_factory=STACConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)


# Global configuration instance
_config = GeoFabricConfig()


def configure_s3(
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
    region: str | None = None,
    session_token: str | None = None,
    endpoint: str | None = None,
    use_ssl: bool = True,
) -> None:
    """
    Configure S3 credentials programmatically.

    This is an alternative to setting environment variables. Credentials set here
    take precedence over environment variables.

    Args:
        access_key_id: AWS access key ID
        secret_access_key: AWS secret access key
        region: AWS region (e.g., 'us-east-1')
        session_token: AWS session token (for temporary credentials)
        endpoint: Custom S3 endpoint URL (for S3-compatible services)
        use_ssl: Use SSL for S3 connections (default: True)

    Example:
        >>> import geofabric as gf
        >>> gf.configure_s3(
        ...     access_key_id="AKIA...",
        ...     secret_access_key="...",
        ...     region="us-east-1"
        ... )
        >>> ds = gf.open("s3://my-bucket/data.parquet?anonymous=false")
    """
    _config.s3 = S3Config(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        region=region,
        session_token=session_token,
        endpoint=endpoint,
        use_ssl=use_ssl,
    )


def configure_gcs(
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
    project: str | None = None,
) -> None:
    """
    Configure GCS credentials programmatically.

    This is an alternative to setting environment variables or using
    application default credentials.

    Args:
        access_key_id: GCS HMAC access key ID
        secret_access_key: GCS HMAC secret access key
        project: GCP project ID

    Example:
        >>> import geofabric as gf
        >>> gf.configure_gcs(
        ...     access_key_id="GOOG...",
        ...     secret_access_key="...",
        ...     project="my-project"
        ... )
        >>> ds = gf.open("gs://my-bucket/data.parquet")
    """
    _config.gcs = GCSConfig(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        project=project,
    )


def configure_azure(
    account_name: str | None = None,
    account_key: str | None = None,
    connection_string: str | None = None,
    sas_token: str | None = None,
) -> None:
    """
    Configure Azure Blob Storage credentials programmatically.

    This is an alternative to setting environment variables (AZURE_STORAGE_ACCOUNT,
    AZURE_STORAGE_KEY, etc.).

    Args:
        account_name: Azure storage account name
        account_key: Azure storage account key
        connection_string: Full Azure connection string (alternative to account_name/key)
        sas_token: Shared Access Signature token

    Example:
        >>> import geofabric as gf
        >>> gf.configure_azure(
        ...     account_name="mystorageaccount",
        ...     account_key="..."
        ... )
        >>> ds = gf.open("az://container/data.parquet")
    """
    _config.azure = AzureConfig(
        account_name=account_name,
        account_key=account_key,
        connection_string=connection_string,
        sas_token=sas_token,
    )


def configure_postgis(
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    sslmode: str | None = None,
) -> None:
    """
    Configure default PostGIS connection parameters.

    These defaults are used when connection parameters are not specified
    in the connection string.

    Args:
        host: Database host
        port: Database port (default: 5432)
        database: Database name
        user: Database user
        password: Database password
        sslmode: SSL mode (disable, allow, prefer, require, verify-ca, verify-full)

    Example:
        >>> import geofabric as gf
        >>> gf.configure_postgis(
        ...     host="db.example.com",
        ...     user="myuser",
        ...     password="mypassword",
        ...     sslmode="require"
        ... )
        >>> ds = gf.open("postgresql:///mydb?table=public.parcels")
    """
    _config.postgis = PostGISConfig(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode=sslmode,
    )


def configure_stac(
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    default_catalog: str | None = None,
) -> None:
    """
    Configure STAC catalog authentication.

    Used for accessing private or authenticated STAC catalogs.

    Args:
        api_key: API key for authenticated catalogs
        headers: Custom HTTP headers (e.g., {"Authorization": "Bearer token"})
        default_catalog: Default STAC catalog URL

    Example:
        >>> import geofabric as gf
        >>> gf.configure_stac(
        ...     api_key="my-api-key",
        ...     headers={"X-Custom-Header": "value"}
        ... )
        >>> ds = gf.open("stac://catalog.example.com/collection")

        # Or with bearer token:
        >>> gf.configure_stac(
        ...     headers={"Authorization": "Bearer eyJ..."}
        ... )
    """
    _config.stac = STACConfig(
        api_key=api_key,
        headers=headers or {},
        default_catalog=default_catalog,
    )


def configure_http(
    proxy: str | None = None,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
) -> None:
    """
    Configure global HTTP settings for web requests.

    Applies to all HTTP-based operations including STAC, web fetching, etc.

    Args:
        proxy: HTTP proxy URL (e.g., "http://proxy.example.com:8080")
        timeout: Request timeout in seconds (default: 30)
        headers: Custom HTTP headers to include in all requests
        verify_ssl: Whether to verify SSL certificates (default: True)

    Example:
        >>> import geofabric as gf
        >>> gf.configure_http(
        ...     proxy="http://corporate-proxy:8080",
        ...     timeout=60,
        ...     verify_ssl=True
        ... )
    """
    _config.http = HTTPConfig(
        proxy=proxy,
        timeout=timeout,
        headers=headers or {},
        verify_ssl=verify_ssl,
    )


def get_config() -> GeoFabricConfig:
    """
    Get the current GeoFabric configuration.

    Returns:
        The global GeoFabricConfig instance.
    """
    return _config


def reset_config() -> None:
    """
    Reset all configuration to defaults.

    This clears any programmatically set credentials, reverting to
    environment variable-based authentication.

    Example:
        >>> import geofabric as gf
        >>> gf.configure_s3(access_key_id="...", secret_access_key="...")
        >>> gf.reset_config()  # Clear credentials
    """
    global _config
    _config = GeoFabricConfig()


class temporary_config:
    """Context manager for temporary configuration changes.

    Saves the current configuration on entry and restores it on exit,
    ensuring that configuration changes within the context don't affect
    code outside of it. This is especially useful for testing.

    Example:
        >>> import geofabric as gf
        >>> gf.configure_s3(region="us-east-1")
        >>> with gf.temporary_config():
        ...     gf.configure_s3(region="eu-west-1")
        ...     # region is eu-west-1 here
        >>> # region is back to us-east-1 here

    Thread Safety:
        This context manager is NOT thread-safe. Configuration changes
        in one thread will affect all threads.
    """

    def __init__(self) -> None:
        """Initialize the context manager."""
        self._saved_config: GeoFabricConfig | None = None

    def __enter__(self) -> "temporary_config":
        """Save the current configuration."""
        from copy import deepcopy

        self._saved_config = deepcopy(_config)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Restore the saved configuration."""
        global _config
        if self._saved_config is not None:
            _config = self._saved_config
