"""Caching layer for GeoFabric."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["CacheConfig", "QueryCache", "configure_cache", "get_cache"]


@dataclass
class CacheConfig:
    """Configuration for the cache layer."""

    cache_dir: str | None = None
    enabled: bool = True
    max_size_mb: int = 1000  # 1GB default

    def __post_init__(self) -> None:
        if self.cache_dir is None:
            self.cache_dir = str(Path("~/.geofabric/cache").expanduser())

        # Validate max_size_mb
        if self.max_size_mb <= 0:
            raise ValueError(f"max_size_mb must be positive, got {self.max_size_mb}")

    @property
    def cache_path(self) -> Path:
        # cache_dir is guaranteed to be set in __post_init__
        if self.cache_dir is None:  # pragma: no cover (defensive check)
            raise RuntimeError("cache_dir was not initialized - this should not happen")
        path = Path(self.cache_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


class QueryCache:
    """Cache for query results.

    Encapsulation:
        - Config is private (_config) to prevent external modification
        - Read-only properties expose safe access to config values
        - Internal methods are private (prefixed with _)

    Design Principles:
        - Information Hiding: Internal state protected from external modification
        - Fail-Safe Defaults: Cache enabled by default with sensible limits
    """

    __slots__ = ("_config",)

    def __init__(self, config: CacheConfig | None = None):
        self._config = config or CacheConfig()

    @property
    def is_enabled(self) -> bool:
        """Check if caching is enabled (read-only)."""
        return self._config.enabled

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path (read-only)."""
        return self._config.cache_path

    @property
    def max_size_mb(self) -> int:
        """Get the maximum cache size in MB (read-only)."""
        return self._config.max_size_mb

    def _cache_key(self, sql: str, source_uri: str) -> str:
        """Generate a cache key from SQL and source."""
        content = f"{source_uri}:{sql}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cache_file(self, key: str, ext: str = "parquet") -> Path:
        """Get the path to a cached data file.

        Args:
            key: Cache key (hash-based identifier)
            ext: File extension (default: parquet)

        Returns:
            Path to the cache data file
        """
        return self._config.cache_path / f"{key}.{ext}"

    def _meta_file(self, key: str) -> Path:
        """Get the path to a cache metadata file.

        Args:
            key: Cache key (hash-based identifier)

        Returns:
            Path to the JSON metadata file
        """
        return self._config.cache_path / f"{key}.meta.json"

    def get(self, sql: str, source_uri: str) -> Path | None:
        """Get cached result if available."""
        if not self._config.enabled:
            return None

        key = self._cache_key(sql, source_uri)
        cache_file = self._cache_file(key)
        meta_file = self._meta_file(key)

        if cache_file.exists() and meta_file.exists():
            return cache_file
        return None

    def put(
        self,
        sql: str,
        source_uri: str,
        data_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Store result in cache."""
        # Enforce size limit before adding new entry
        self._enforce_size_limit()

        key = self._cache_key(sql, source_uri)
        cache_file = self._cache_file(key)
        meta_file = self._meta_file(key)

        # Copy data to cache
        import shutil

        shutil.copy2(data_path, cache_file)

        # Write metadata
        meta = {
            "sql": sql,
            "source_uri": source_uri,
            "key": key,
            **(metadata or {}),
        }
        meta_file.write_text(json.dumps(meta, indent=2))

        return cache_file

    def _enforce_size_limit(self) -> None:
        """Evict oldest entries if cache exceeds max_size_mb.

        Uses LRU (Least Recently Used) eviction strategy.
        """
        import logging

        if not self._config.enabled:
            return

        max_bytes = self._config.max_size_mb * 1024 * 1024

        # Get all cache files with their modification times
        cache_files = []
        for f in self._config.cache_path.glob("*.parquet"):
            meta_file = self._config.cache_path / f"{f.stem}.meta.json"
            try:
                size = f.stat().st_size + (meta_file.stat().st_size if meta_file.exists() else 0)
                mtime = f.stat().st_mtime
                cache_files.append((f, meta_file, size, mtime))
            except OSError:
                continue

        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[3])

        # Calculate total size
        total_size = sum(item[2] for item in cache_files)

        # Evict oldest entries until under limit
        evicted_count = 0
        for cache_f, meta_f, size, _ in cache_files:
            if total_size <= max_bytes:
                break
            try:
                cache_f.unlink(missing_ok=True)
                meta_f.unlink(missing_ok=True)
                total_size -= size
                evicted_count += 1
            except OSError as e:
                # Log the error instead of silently continuing
                logging.debug(f"Failed to evict cache file {cache_f}: {e}")
                continue

        if evicted_count > 0:
            logging.debug(f"Evicted {evicted_count} cache entries to enforce size limit")

    def clear(self) -> int:
        """Clear all cached data. Returns number of files removed."""
        count = 0
        for f in self._config.cache_path.glob("*"):
            try:
                f.unlink()
                count += 1
            except OSError:
                # File may have been deleted by another process
                continue
        return count

    def size_mb(self) -> float:
        """Return total cache size in MB."""
        total = sum(f.stat().st_size for f in self._config.cache_path.glob("*"))
        return total / (1024 * 1024)


# Global cache instance
_cache: QueryCache | None = None


def get_cache() -> QueryCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache


def configure_cache(
    cache_dir: str | None = None,
    enabled: bool = True,
    max_size_mb: int = 1000,
) -> None:
    """Configure the global cache."""
    global _cache
    _cache = QueryCache(
        CacheConfig(
            cache_dir=cache_dir,
            enabled=enabled,
            max_size_mb=max_size_mb,
        )
    )
