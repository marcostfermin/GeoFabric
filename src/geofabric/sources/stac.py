from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from geofabric.errors import EngineError, InvalidURIError, MissingDependencyError
from geofabric.sql_utils import build_parquet_sql, build_stread_sql, escape_path

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine


@dataclass(frozen=True)
class STACSource:
    """Source for STAC (SpatioTemporal Asset Catalog) data."""

    catalog_url: str
    collection: str | None = None
    asset_key: str = "data"
    bbox: tuple[float, float, float, float] | None = None
    datetime: str | None = None

    def __post_init__(self) -> None:
        """Validate STAC source configuration on creation.

        Note: catalog_url can be empty, as get_catalog_url() falls back
        to config.stac.default_catalog.
        """
        # If catalog_url is provided, validate it's a proper URL
        if self.catalog_url and self.catalog_url.strip():
            if not (
                self.catalog_url.startswith("http://")
                or self.catalog_url.startswith("https://")
            ):
                raise InvalidURIError(
                    f"catalog_url must start with http:// or https://, got: {self.catalog_url}"
                )

        # Validate asset_key is not empty
        if not self.asset_key or not self.asset_key.strip():
            raise InvalidURIError("asset_key cannot be empty")

        # Validate collection if provided (should not be empty string)
        if self.collection is not None and not self.collection.strip():
            raise InvalidURIError("collection cannot be empty string")

    def source_kind(self) -> str:
        return "stac"

    def to_duckdb_relation_sql(self, engine: DuckDBEngine) -> str:
        """Generate SQL for reading from STAC catalog.

        Implements SourceWithDuckDBRelation protocol.
        Uses centralized SQL builders for security and consistency.
        """
        from geofabric.sql_utils import DuckDBConfigBuilder

        # Get asset URLs from STAC search
        urls = self.search_items()
        if not urls:
            raise EngineError("STAC search returned no items")

        # Configure httpfs for reading remote files using safe builder
        config_builder = DuckDBConfigBuilder(engine)
        config_builder.load_extension("httpfs")

        # If single URL, read directly
        if len(urls) == 1:
            url = urls[0]
            if url.endswith(".parquet") or url.endswith(".pq"):
                return build_parquet_sql(url)
            return build_stread_sql(engine, url)

        # Multiple URLs - union them together (assuming parquet)
        parquet_urls = [u for u in urls if u.endswith(".parquet") or u.endswith(".pq")]
        if parquet_urls:
            # Use read_parquet with list of files (escape each URL)
            url_list = ", ".join(f"'{escape_path(u)}'" for u in parquet_urls)
            return f"read_parquet([{url_list}])"

        # Fall back to first URL
        return build_stread_sql(engine, urls[0])

    @staticmethod
    def from_uri(uri: str) -> STACSource:
        """Parse a STAC URI.

        Format: stac://<catalog_url>?collection=<name>&bbox=<minx,miny,maxx,maxy>&datetime=<range>
        """
        parsed = urlparse(uri)
        if parsed.scheme != "stac":
            raise InvalidURIError(f"Not a STAC URI: {uri}")

        catalog_url = f"https://{parsed.netloc}{parsed.path}"
        qs = parse_qs(parsed.query)

        collection = qs.get("collection", [None])[0]
        asset_key = qs.get("asset", ["data"])[0]
        datetime_range = qs.get("datetime", [None])[0]

        bbox = None
        if "bbox" in qs:
            bbox_str = qs["bbox"][0]
            try:
                parts = [float(x) for x in bbox_str.split(",")]
                if len(parts) != 4:
                    raise InvalidURIError(
                        f"STAC bbox must have 4 values (minx,miny,maxx,maxy), got {len(parts)}"
                    )
                minx, miny, maxx, maxy = parts

                # Validate coordinates are finite
                for name, val in [("minx", minx), ("miny", miny), ("maxx", maxx), ("maxy", maxy)]:
                    if math.isnan(val) or math.isinf(val):
                        raise InvalidURIError(f"STAC bbox {name} must be finite, got {val}")

                # Validate bounds are not inverted
                if minx > maxx:
                    raise InvalidURIError(f"STAC bbox minx ({minx}) must be <= maxx ({maxx})")
                if miny > maxy:
                    raise InvalidURIError(f"STAC bbox miny ({miny}) must be <= maxy ({maxy})")

                bbox = (minx, miny, maxx, maxy)
            except ValueError as e:
                raise InvalidURIError(f"Invalid STAC bbox format: {bbox_str}") from e

        return STACSource(
            catalog_url=catalog_url,
            collection=collection,
            asset_key=asset_key,
            bbox=bbox,
            datetime=datetime_range,
        )

    def _get_client_kwargs(self) -> dict[str, Any]:
        """Get kwargs for pystac_client.Client.open() including auth headers."""
        from geofabric.config import get_config

        config = get_config()
        kwargs: dict[str, Any] = {}

        # Build headers from config
        headers: dict[str, str] = {}

        # Add API key if configured
        if config.stac.api_key:
            headers["X-API-Key"] = config.stac.api_key

        # Add custom STAC headers
        headers.update(config.stac.headers)

        # Add global HTTP headers
        headers.update(config.http.headers)

        if headers:
            kwargs["headers"] = headers

        # Apply HTTP config settings for timeout (pystac_client uses requests)
        # Note: pystac_client doesn't directly support all request options,
        # but timeout can be passed in some versions
        if config.http.timeout and config.http.timeout != 30:
            kwargs["timeout"] = config.http.timeout

        return kwargs

    def _get_request_session(self) -> Any:
        """Get a configured requests session with HTTP config settings."""
        import requests  # type: ignore[import-untyped]

        from geofabric.config import get_config

        config = get_config()
        session = requests.Session()

        # Apply proxy settings
        if config.http.proxy:
            session.proxies = {
                "http": config.http.proxy,
                "https": config.http.proxy,
            }

        # Apply SSL verification setting
        session.verify = config.http.verify_ssl

        return session

    def get_catalog_url(self) -> str:
        """Get the catalog URL, using default_catalog from config if not specified."""
        from geofabric.config import get_config

        if self.catalog_url:
            return self.catalog_url

        config = get_config()
        if config.stac.default_catalog:
            return config.stac.default_catalog

        raise InvalidURIError("No STAC catalog URL specified and no default_catalog configured")

    def search_items(self, max_items: int = 100) -> list[str]:
        """Search STAC catalog and return asset URLs."""
        try:
            from pystac_client import Client
        except ImportError as e:
            raise MissingDependencyError(
                "pystac-client is required for STAC sources. "
                "Install with: pip install geofabric[stac]"
            ) from e

        # Get client kwargs including authentication headers
        client_kwargs = self._get_client_kwargs()
        catalog_url = self.get_catalog_url()
        client = Client.open(catalog_url, **client_kwargs)

        search_kwargs: dict = {"max_items": max_items}
        if self.collection:
            search_kwargs["collections"] = [self.collection]
        if self.bbox:
            search_kwargs["bbox"] = self.bbox
        if self.datetime:
            search_kwargs["datetime"] = self.datetime

        search = client.search(**search_kwargs)
        urls = []
        for item in search.items():
            if self.asset_key in item.assets:
                urls.append(item.assets[self.asset_key].href)
        return urls


class STACSession:
    """Context manager for STAC catalog sessions.

    Provides a managed HTTP session for STAC catalog operations with
    automatic resource cleanup. Applies configured proxy settings,
    SSL verification, and custom headers.

    Example:
        >>> source = STACSource(catalog_url="https://example.com/stac")
        >>> with source.session() as session:
        ...     items = session.search(collections=["collection1"])
        >>> # Session automatically closed

    Design Principles:
        - Resource Safety: HTTP session properly closed on exit
        - Configuration: Applies global HTTP config settings
        - Convenience: Direct access to pystac_client functionality
    """

    def __init__(self, source: STACSource) -> None:
        """Initialize the STAC session.

        Args:
            source: STACSource to create session for
        """
        self._source = source
        self._session: Any = None
        self._client: Any = None

    def __enter__(self) -> "STACSession":
        """Enter the session context, creating HTTP session and client."""
        try:
            from pystac_client import Client
        except ImportError as e:
            raise MissingDependencyError(
                "pystac-client is required for STAC sources. "
                "Install with: pip install geofabric[stac]"
            ) from e

        # Create and store the HTTP session
        self._session = self._source._get_request_session()

        # Get client kwargs including authentication headers
        client_kwargs = self._source._get_client_kwargs()
        catalog_url = self._source.get_catalog_url()

        # Open client with managed session
        self._client = Client.open(catalog_url, **client_kwargs)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the session context, closing HTTP session."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:  # nosec B110 - intentional: ignore cleanup errors
                pass
            self._session = None
        self._client = None

    def search(self, **kwargs: Any) -> Any:
        """Search the STAC catalog.

        Args:
            **kwargs: Search parameters (collections, bbox, datetime, etc.)

        Returns:
            Search results iterator
        """
        if self._client is None:
            raise EngineError("STACSession not entered - use 'with' statement")
        return self._client.search(**kwargs)

    def get_asset_urls(self, max_items: int = 100) -> list[str]:
        """Search and return asset URLs using source configuration.

        Args:
            max_items: Maximum number of items to return

        Returns:
            List of asset URLs
        """
        if self._client is None:
            raise EngineError("STACSession not entered - use 'with' statement")

        search_kwargs: dict = {"max_items": max_items}
        if self._source.collection:
            search_kwargs["collections"] = [self._source.collection]
        if self._source.bbox:
            search_kwargs["bbox"] = self._source.bbox
        if self._source.datetime:
            search_kwargs["datetime"] = self._source.datetime

        search = self._client.search(**search_kwargs)
        urls = []
        for item in search.items():
            if self._source.asset_key in item.assets:
                urls.append(item.assets[self._source.asset_key].href)
        return urls

    @property
    def client(self) -> Any:
        """Get the underlying pystac_client Client."""
        return self._client


# Add session method to STACSource
def _stac_session(self: STACSource) -> STACSession:
    """Create a managed STAC session.

    Returns:
        STACSession context manager

    Example:
        >>> with source.session() as session:
        ...     urls = session.get_asset_urls()
    """
    return STACSession(self)


# Attach method to class
STACSource.session = _stac_session


from geofabric.registry import SourceClassFactory

# Use generic factory instead of boilerplate class
STACSourceFactory = SourceClassFactory(STACSource)
