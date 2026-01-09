"""Tests for new features: spatial ops, validation, cache, new sources."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestSpatialOperations:
    """Tests for spatial operations."""

    def test_buffer_op_sql_meters(self) -> None:
        """Test BufferOp generates correct SQL for meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(geometry_col="geometry", distance=100, unit="meters")
        sql = op.to_sql("geometry")
        assert "ST_Buffer(geometry, 100)" in sql

    def test_buffer_op_sql_kilometers(self) -> None:
        """Test BufferOp converts kilometers to meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(geometry_col="geometry", distance=1, unit="kilometers")
        sql = op.to_sql("geometry")
        assert "ST_Buffer(geometry, 1000)" in sql

    def test_buffer_op_sql_miles(self) -> None:
        """Test BufferOp converts miles to meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(geometry_col="geometry", distance=1, unit="miles")
        sql = op.to_sql("geometry")
        assert "1609.34" in sql

    def test_simplify_op_preserve_topology(self) -> None:
        """Test SimplifyOp with preserve_topology=True."""
        from geofabric.spatial import SimplifyOp

        op = SimplifyOp(geometry_col="geometry", tolerance=0.001, preserve_topology=True)
        sql = op.to_sql("geometry")
        assert "ST_SimplifyPreserveTopology" in sql
        assert "0.001" in sql

    def test_simplify_op_no_topology(self) -> None:
        """Test SimplifyOp with preserve_topology=False."""
        from geofabric.spatial import SimplifyOp

        op = SimplifyOp(geometry_col="geometry", tolerance=0.001, preserve_topology=False)
        sql = op.to_sql("geometry")
        assert "ST_Simplify(geometry, 0.001)" in sql
        assert "PreserveTopology" not in sql

    def test_centroid_op(self) -> None:
        """Test CentroidOp generates correct SQL."""
        from geofabric.spatial import CentroidOp

        op = CentroidOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert sql == "ST_Centroid(geometry)"

    def test_convex_hull_op(self) -> None:
        """Test ConvexHullOp generates correct SQL."""
        from geofabric.spatial import ConvexHullOp

        op = ConvexHullOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert sql == "ST_ConvexHull(geometry)"

    def test_envelope_op(self) -> None:
        """Test EnvelopeOp generates correct SQL."""
        from geofabric.spatial import EnvelopeOp

        op = EnvelopeOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert sql == "ST_Envelope(geometry)"

    def test_union_op(self) -> None:
        """Test UnionOp generates correct SQL."""
        from geofabric.spatial import UnionOp

        op = UnionOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert sql == "ST_Union_Agg(geometry)"


class TestValidation:
    """Tests for validation utilities."""

    def test_validation_issue_dataclass(self) -> None:
        """Test ValidationIssue dataclass."""
        from geofabric.validation import ValidationIssue

        issue = ValidationIssue(row_id=1, issue_type="invalid_geometry", message="Self-intersection")
        assert issue.row_id == 1
        assert issue.issue_type == "invalid_geometry"
        assert issue.message == "Self-intersection"

    def test_validation_result_is_valid_true(self) -> None:
        """Test ValidationResult.is_valid when no invalid geometries."""
        from geofabric.validation import ValidationResult

        result = ValidationResult(
            total_rows=100,
            valid_count=95,
            invalid_count=0,
            null_count=5,
            issues=[],
        )
        assert result.is_valid is True

    def test_validation_result_is_valid_false(self) -> None:
        """Test ValidationResult.is_valid when invalid geometries exist."""
        from geofabric.validation import ValidationIssue, ValidationResult

        result = ValidationResult(
            total_rows=100,
            valid_count=90,
            invalid_count=5,
            null_count=5,
            issues=[ValidationIssue(row_id=i, issue_type="invalid", message="err") for i in range(5)],
        )
        assert result.is_valid is False

    def test_validation_result_summary(self) -> None:
        """Test ValidationResult.summary() output."""
        from geofabric.validation import ValidationResult

        result = ValidationResult(
            total_rows=100,
            valid_count=95,
            invalid_count=0,
            null_count=5,
            issues=[],
        )
        summary = result.summary()
        assert "100" in summary
        assert "95" in summary
        assert "All valid" in summary

    def test_dataset_stats_dataclass(self) -> None:
        """Test DatasetStats dataclass."""
        from geofabric.validation import DatasetStats

        stats = DatasetStats(
            row_count=1000,
            column_count=5,
            columns=["id", "name", "value", "date", "geometry"],
            dtypes={"id": "int64", "name": "object", "value": "float64", "date": "datetime64", "geometry": "object"},
            bounds=(-180.0, -90.0, 180.0, 90.0),
            geometry_type="POLYGON",
            crs="EPSG:4326",
            null_counts={"id": 0, "name": 10, "value": 5, "date": 0, "geometry": 0},
        )
        assert stats.row_count == 1000
        assert stats.geometry_type == "POLYGON"
        assert stats.bounds == (-180.0, -90.0, 180.0, 90.0)

    def test_dataset_stats_summary(self) -> None:
        """Test DatasetStats.summary() output."""
        from geofabric.validation import DatasetStats

        stats = DatasetStats(
            row_count=1000,
            column_count=5,
            columns=["id", "geometry"],
            dtypes={"id": "int64", "geometry": "object"},
            bounds=(-122.5, 37.5, -122.0, 38.0),
            geometry_type="POINT",
            crs="EPSG:4326",
            null_counts={"id": 0, "geometry": 0},
        )
        summary = stats.summary()
        assert "1,000" in summary
        assert "POINT" in summary
        assert "EPSG:4326" in summary


class TestCache:
    """Tests for caching layer."""

    def test_cache_config_defaults(self) -> None:
        """Test CacheConfig default values."""
        from geofabric.cache import CacheConfig

        config = CacheConfig()
        assert config.enabled is True
        assert config.max_size_mb == 1000
        assert "geofabric" in str(config.cache_dir)

    def test_cache_config_custom_dir(self) -> None:
        """Test CacheConfig with custom directory."""
        from geofabric.cache import CacheConfig

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td)
            assert config.cache_dir == td
            assert config.cache_path.exists()

    def test_query_cache_key_generation(self) -> None:
        """Test QueryCache generates consistent keys."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            cache = QueryCache(CacheConfig(cache_dir=td))
            key1 = cache._cache_key("SELECT * FROM t", "file:///data.parquet")
            key2 = cache._cache_key("SELECT * FROM t", "file:///data.parquet")
            key3 = cache._cache_key("SELECT id FROM t", "file:///data.parquet")

            assert key1 == key2  # Same inputs = same key
            assert key1 != key3  # Different SQL = different key

    def test_query_cache_disabled(self) -> None:
        """Test QueryCache.get returns None when disabled."""
        from geofabric.cache import CacheConfig, QueryCache

        cache = QueryCache(CacheConfig(enabled=False))
        result = cache.get("SELECT * FROM t", "file:///data.parquet")
        assert result is None

    def test_query_cache_miss(self) -> None:
        """Test QueryCache.get returns None on cache miss."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            cache = QueryCache(CacheConfig(cache_dir=td))
            result = cache.get("SELECT * FROM t", "file:///nonexistent.parquet")
            assert result is None

    def test_query_cache_put_and_get(self) -> None:
        """Test QueryCache.put stores data and get retrieves it."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            cache = QueryCache(CacheConfig(cache_dir=td))

            # Create a test file to cache
            test_data = Path(td) / "test_data.parquet"
            test_data.write_bytes(b"test parquet data")

            # Put in cache
            sql = "SELECT * FROM t"
            source = "file:///data.parquet"
            cache_path = cache.put(sql, source, str(test_data))

            assert cache_path.exists()

            # Get from cache
            result = cache.get(sql, source)
            assert result is not None
            assert result.exists()

    def test_query_cache_clear(self) -> None:
        """Test QueryCache.clear removes all cached files."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            cache = QueryCache(CacheConfig(cache_dir=td))

            # Create some cached files
            test_data = Path(td) / "test_data.parquet"
            test_data.write_bytes(b"test data")
            cache.put("SELECT * FROM t1", "file:///a.parquet", str(test_data))
            cache.put("SELECT * FROM t2", "file:///b.parquet", str(test_data))

            # Clear cache
            count = cache.clear()
            assert count >= 2

            # Verify cache is empty
            assert cache.get("SELECT * FROM t1", "file:///a.parquet") is None

    def test_get_cache_singleton(self) -> None:
        """Test get_cache returns a singleton."""
        from geofabric.cache import get_cache

        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_configure_cache(self) -> None:
        """Test configure_cache updates global cache."""
        import os
        from geofabric.cache import configure_cache, get_cache

        with tempfile.TemporaryDirectory() as td:
            configure_cache(cache_dir=td, enabled=True, max_size_mb=500)
            cache = get_cache()
            # Use realpath to handle macOS symlinks (/tmp -> /private/tmp)
            assert os.path.realpath(str(cache.cache_dir)) == os.path.realpath(td)
            assert cache.max_size_mb == 500


class TestNewSources:
    """Tests for new data sources."""

    def test_s3_source_creation(self) -> None:
        """Test S3Source can be instantiated."""
        from geofabric.sources.cloud import S3Source

        src = S3Source(bucket="my-bucket", key="path/to/data.parquet", region="us-east-1")
        assert src.bucket == "my-bucket"
        assert src.key == "path/to/data.parquet"
        assert src.region == "us-east-1"
        assert src.anonymous is True

    def test_s3_source_uri(self) -> None:
        """Test S3Source generates correct URI."""
        from geofabric.sources.cloud import S3Source

        src = S3Source(bucket="my-bucket", key="data.parquet")
        assert src.uri() == "s3://my-bucket/data.parquet"

    def test_gcs_source_creation(self) -> None:
        """Test GCSSource can be instantiated."""
        from geofabric.sources.cloud import GCSSource

        src = GCSSource(bucket="my-bucket", key="path/to/data.parquet")
        assert src.bucket == "my-bucket"
        assert src.key == "path/to/data.parquet"

    def test_gcs_source_uri(self) -> None:
        """Test GCSSource generates correct URI."""
        from geofabric.sources.cloud import GCSSource

        src = GCSSource(bucket="my-bucket", key="data.parquet")
        assert src.uri() == "gs://my-bucket/data.parquet"

    def test_postgis_source_creation(self) -> None:
        """Test PostGISSource can be instantiated."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="localhost",
            port=5432,
            database="mydb",
            user="user",
            password="pass",
            table="my_table",
            schema="public",
            geometry_column="geom",
        )
        assert src.host == "localhost"
        assert src.port == 5432
        assert src.database == "mydb"
        assert src.table == "my_table"
        assert src.geometry_column == "geom"

    def test_stac_source_creation(self) -> None:
        """Test STACSource can be instantiated."""
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://planetarycomputer.microsoft.com/api/stac/v1",
            collection="landsat-c2-l2",
            bbox=(-122.5, 37.5, -122.0, 38.0),
        )
        assert src.catalog_url == "https://planetarycomputer.microsoft.com/api/stac/v1"
        assert src.collection == "landsat-c2-l2"
        assert src.bbox == (-122.5, 37.5, -122.0, 38.0)


class TestDatasetEnhancements:
    """Tests for Dataset enhancements."""

    def test_dataset_open_s3_uri(self) -> None:
        """Test opening S3 URI creates S3Source."""
        from geofabric.dataset import open as gf_open
        from geofabric.sources.cloud import S3Source

        # Mock the engine to avoid actual S3 connection
        with patch("geofabric.dataset.DuckDBEngine"):
            ds = gf_open("s3://my-bucket/path/data.parquet")
            assert isinstance(ds.source, S3Source)
            assert ds.source.bucket == "my-bucket"
            assert ds.source.key == "path/data.parquet"

    def test_dataset_open_gs_uri(self) -> None:
        """Test opening GCS URI creates GCSSource."""
        from geofabric.dataset import open as gf_open
        from geofabric.sources.cloud import GCSSource

        with patch("geofabric.dataset.DuckDBEngine"):
            ds = gf_open("gs://my-bucket/path/data.parquet")
            assert isinstance(ds.source, GCSSource)
            assert ds.source.bucket == "my-bucket"
            assert ds.source.key == "path/data.parquet"

    def test_dataset_open_postgis_uri(self) -> None:
        """Test opening PostGIS URI creates PostGISSource."""
        from geofabric.dataset import open as gf_open
        from geofabric.sources.postgis import PostGISSource

        with patch("geofabric.dataset.DuckDBEngine"):
            ds = gf_open("postgresql://user:pass@localhost:5432/mydb?table=mytable")
            assert isinstance(ds.source, PostGISSource)
            assert ds.source.host == "localhost"
            assert ds.source.port == 5432
            assert ds.source.database == "mydb"
            assert ds.source.table == "mytable"


class TestQueryEnhancements:
    """Tests for Query method enhancements."""

    def _make_fake_query(self):
        """Create a fake Query for testing."""
        from geofabric.query import Query

        fake_dataset = MagicMock()
        fake_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
        })
        return Query(dataset=fake_dataset)

    def test_query_head(self) -> None:
        """Test Query.head returns limited rows."""
        q = self._make_fake_query()
        result = q.head(2)
        assert isinstance(result, pd.DataFrame)

    def test_query_count(self) -> None:
        """Test Query.count returns integer."""
        from geofabric.query import Query

        fake_dataset = MagicMock()
        fake_dataset.engine.query_to_df.return_value = pd.DataFrame({"cnt": [42]})
        q = Query(dataset=fake_dataset)
        result = q.count()
        assert result == 42

    def test_query_columns_property(self) -> None:
        """Test Query.columns property returns column names."""
        q = self._make_fake_query()
        cols = q.columns
        assert isinstance(cols, list)

    def test_query_dtypes_property(self) -> None:
        """Test Query.dtypes property returns type mapping."""
        q = self._make_fake_query()
        dtypes = q.dtypes
        assert isinstance(dtypes, dict)


class TestCLIEnhancements:
    """Tests for CLI enhancements."""

    def test_output_format_enum(self) -> None:
        """Test OutputFormat enum has all expected values."""
        from geofabric.cli.app import OutputFormat

        assert OutputFormat.parquet.value == "parquet"
        assert OutputFormat.geojson.value == "geojson"
        assert OutputFormat.csv.value == "csv"
        assert OutputFormat.flatgeobuf.value == "flatgeobuf"
        assert OutputFormat.geopackage.value == "geopackage"
