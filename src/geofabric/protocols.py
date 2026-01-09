"""Protocol definitions for GeoFabric components.

This module defines the structural typing protocols that enable type-safe
duck typing throughout GeoFabric. Using protocols allows new source, engine,
and sink implementations without modifying core code (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

__all__ = [
    "Engine",
    "EngineBase",
    "OpenOptions",
    "Sink",
    "SinkBase",
    "Source",
    "SourceBase",
    "SourceWithDuckDBRelation",
    "SourceWithFromURI",
    "SourceWithSearchItems",
    "SourceWithURI",
    "supports_duckdb_relation",
    "supports_from_uri",
    "supports_uri",
]


@runtime_checkable
class Source(Protocol):
    """Protocol for all data sources.

    Every source must implement source_kind() to identify its type.
    Sources are typically frozen dataclasses for immutability.

    A Source represents a dataset input.
    Engines translate a Source into a FROM-able relation (SQL or equivalent).
    """

    def source_kind(self) -> str:
        """Return the source type identifier (e.g., 'files', 's3', 'postgis')."""
        ...


@runtime_checkable
class SourceWithDuckDBRelation(Protocol):
    """Protocol for sources that can generate DuckDB SQL relations.

    Sources implementing this protocol can convert themselves to SQL
    that DuckDB can execute, enabling self-describing data sources.
    This follows the Open/Closed Principle - new sources can be added
    without modifying the DuckDBEngine class.
    """

    def source_kind(self) -> str:
        """Return the source type identifier."""
        ...

    def to_duckdb_relation_sql(self, engine: Any) -> str:
        """Generate SQL expression that DuckDB can use as a relation.

        Args:
            engine: The DuckDB engine instance (for loading extensions, etc.)

        Returns:
            SQL string usable in FROM clause (e.g., "read_parquet('...')")
        """
        ...


@runtime_checkable
class SourceWithSearchItems(Protocol):
    """Protocol for sources that can search for items (e.g., STAC catalogs)."""

    def source_kind(self) -> str:
        """Return the source type identifier."""
        ...

    def search_items(self, max_items: int = 100) -> list[str]:
        """Search for items and return asset URLs."""
        ...


@runtime_checkable
class SourceWithURI(Protocol):
    """Protocol for sources that can generate URIs.

    Sources implementing this protocol can provide a canonical URI
    representation of themselves. This enables:
    - Caching based on source identity
    - Logging and debugging with meaningful identifiers
    - Source comparison and deduplication
    """

    def source_kind(self) -> str:
        """Return the source type identifier."""
        ...

    def uri(self) -> str:
        """Return the canonical URI for this source.

        Returns:
            A URI string (e.g., 's3://bucket/key', 'file:///path/to/file')
        """
        ...


@runtime_checkable
class SourceWithFromURI(Protocol):
    """Protocol for source classes that can parse URIs.

    This is a class-level protocol (not instance-level) for sources
    that can be constructed from URI strings. Implemented as a classmethod
    or staticmethod.

    Note: Due to Protocol limitations, we check for this at runtime
    using hasattr() rather than isinstance().
    """

    @staticmethod
    def from_uri(uri: str) -> "Source":
        """Parse a URI and return a Source instance.

        Args:
            uri: The URI string to parse

        Returns:
            A Source instance

        Raises:
            InvalidURIError: If the URI cannot be parsed
        """
        ...


class SourceBase(ABC):
    """Abstract base class for sources requiring mandatory implementation.

    Use this when you want to enforce implementation at class definition
    time rather than runtime (stronger guarantees than Protocol).

    Provides common validation methods that subclasses can use.

    Design Principles:
    - Template Method Pattern: Defines algorithm skeleton, subclasses fill in steps
    - Open/Closed Principle: Closed for modification, open for extension
    - Dependency Inversion: High-level modules depend on abstractions
    """

    @abstractmethod
    def source_kind(self) -> str:
        """Return the source type identifier."""
        pass

    @classmethod
    def _validate_non_empty(cls, value: str, field_name: str) -> str:
        """Validate that a string value is not empty.

        Args:
            value: The value to validate
            field_name: Name of the field (for error messages)

        Returns:
            The validated value

        Raises:
            ValueError: If value is empty
        """
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty")
        return value

    @classmethod
    def _validate_port(cls, port: int) -> int:
        """Validate that a port number is in valid range.

        Args:
            port: The port number to validate

        Returns:
            The validated port

        Raises:
            ValueError: If port is out of range
        """
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
        return port

    @classmethod
    def _validate_url_scheme(cls, url: str, allowed_schemes: set[str]) -> str:
        """Validate that a URL has an allowed scheme.

        Args:
            url: The URL to validate
            allowed_schemes: Set of allowed scheme names (e.g., {'http', 'https'})

        Returns:
            The validated URL

        Raises:
            ValueError: If scheme is not allowed
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            raise ValueError(
                f"URL scheme must be one of {sorted(allowed_schemes)}, "
                f"got '{parsed.scheme}'"
            )
        return url


@runtime_checkable
class Engine(Protocol):
    """Protocol for query execution engines.

    An Engine executes queries. Engines are SQL-based and translate
    Sources into executable queries.
    """

    def engine_kind(self) -> str:
        """Return the engine type identifier."""
        ...

    def source_to_relation_sql(self, source: Source) -> str:
        """Convert a source to SQL that can be used in FROM clause."""
        ...

    def query_to_df(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return results as pandas DataFrame."""
        ...

    def query_to_arrow(self, sql: str) -> pa.Table:
        """Execute SQL and return results as PyArrow Table."""
        ...

    def copy_to_parquet(self, sql: str, out_path: str) -> None:
        """Copy query results to a Parquet file."""
        ...

    def copy_to_geojson(self, sql: str, out_path: str) -> None:
        """Copy query results to a GeoJSON file."""
        ...


@runtime_checkable
class Sink(Protocol):
    """Protocol for data output destinations.

    A Sink consumes an executed query output to produce an artifact
    (tiles, db load, etc).
    """

    def sink_kind(self) -> str:
        """Return the sink type identifier."""
        ...

    def write(
        self,
        *,
        engine: Engine,
        sql: str,
        out_path: str,
        options: dict[str, Any],
    ) -> str:
        """Write query results to the sink.

        Args:
            engine: The execution engine
            sql: SQL query to execute
            out_path: Output path/location
            options: Sink-specific options

        Returns:
            Path or identifier of written output
        """
        ...


class EngineBase(ABC):
    """Abstract base class for query execution engines.

    Use this when you want to enforce implementation at class definition
    time rather than runtime. Provides common validation and utility methods.

    Design Principles:
    - Template Method Pattern: Defines algorithm skeleton for query execution
    - Open/Closed Principle: New engines can extend without modifying base
    - Single Responsibility: Each method has one clear purpose
    """

    @abstractmethod
    def engine_kind(self) -> str:
        """Return the engine type identifier."""
        pass

    @abstractmethod
    def source_to_relation_sql(self, source: Source) -> str:
        """Convert a source to SQL that can be used in FROM clause."""
        pass

    @abstractmethod
    def query_to_df(self, sql: str) -> "pd.DataFrame":
        """Execute SQL and return results as pandas DataFrame."""
        pass

    @abstractmethod
    def query_to_arrow(self, sql: str) -> "pa.Table":
        """Execute SQL and return results as PyArrow Table."""
        pass

    def _validate_sql(self, sql: str) -> str:
        """Validate SQL string is not empty.

        Args:
            sql: The SQL to validate

        Returns:
            The validated SQL

        Raises:
            ValueError: If SQL is empty
        """
        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")
        return sql

    def _validate_output_path(self, path: str) -> str:
        """Validate output path is not empty.

        Args:
            path: The path to validate

        Returns:
            The validated path

        Raises:
            ValueError: If path is empty
        """
        if not path or not path.strip():
            raise ValueError("Output path cannot be empty")
        return path


class SinkBase(ABC):
    """Abstract base class for data output sinks.

    Use this when you want to enforce implementation at class definition
    time rather than runtime. Provides common validation methods.

    Design Principles:
    - Template Method Pattern: Standardizes write operation structure
    - Dependency Inversion: Depends on Engine abstraction, not concrete impl
    - Interface Segregation: Minimal required interface
    """

    @abstractmethod
    def sink_kind(self) -> str:
        """Return the sink type identifier."""
        pass

    @abstractmethod
    def write(
        self,
        *,
        engine: Engine,
        sql: str,
        out_path: str,
        options: dict[str, Any],
    ) -> str:
        """Write query results to the sink.

        Args:
            engine: The execution engine
            sql: SQL query to execute
            out_path: Output path/location
            options: Sink-specific options

        Returns:
            Path or identifier of written output
        """
        pass

    def _validate_options(
        self,
        options: dict[str, Any],
        required: set[str],
        optional: set[str] | None = None,
    ) -> dict[str, Any]:
        """Validate sink options.

        Args:
            options: The options dict to validate
            required: Set of required option keys
            optional: Set of optional option keys (for documentation/validation)

        Returns:
            The validated options

        Raises:
            ValueError: If required options are missing
        """
        missing = required - set(options.keys())
        if missing:
            raise ValueError(f"Missing required options: {sorted(missing)}")
        return options


@dataclass(frozen=True)
class OpenOptions:
    """Options for opening a dataset."""

    engine: str | None = None


def supports_duckdb_relation(source: Any) -> bool:
    """Type guard to check if a source supports direct DuckDB relation generation.

    This enables safe protocol dispatch without isinstance chains.

    Args:
        source: Any source object

    Returns:
        True if source implements SourceWithDuckDBRelation protocol

    Example:
        if supports_duckdb_relation(source):
            sql = source.to_duckdb_relation_sql(engine)
    """
    return isinstance(source, SourceWithDuckDBRelation)


def supports_uri(source: Any) -> bool:
    """Type guard to check if a source can generate URIs.

    Args:
        source: Any source object

    Returns:
        True if source implements SourceWithURI protocol

    Example:
        if supports_uri(source):
            cache_key = source.uri()
    """
    return isinstance(source, SourceWithURI)


def supports_from_uri(source_class: type) -> bool:
    """Type guard to check if a source class can parse URIs.

    Note: This checks at the class level, not instance level.

    Args:
        source_class: A source class (not instance)

    Returns:
        True if source class has a from_uri staticmethod/classmethod

    Example:
        if supports_from_uri(S3Source):
            source = S3Source.from_uri("s3://bucket/key")
    """
    return hasattr(source_class, "from_uri") and callable(
        getattr(source_class, "from_uri", None)
    )
