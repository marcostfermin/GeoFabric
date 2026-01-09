"""Tests to fill coverage gaps in various modules."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from geofabric.errors import EngineError, InvalidURIError


def _write_test_parquet(path: str) -> None:
    """Write a test parquet file."""
    point_wkb = bytes.fromhex("010100000000000000000000000000000000000000")
    table = pa.table(
        {
            "id": pa.array([1, 2], pa.int64()),
            "geometry": pa.array([point_wkb, point_wkb], pa.binary()),
        }
    )
    pq.write_table(table, path)


class TestMainModule:
    """Tests for __main__.py module."""

    def test_main_import(self) -> None:
        """Test that __main__.py can be imported."""
        from geofabric import __main__

        assert hasattr(__main__, "main")

    def test_main_module_runnable(self) -> None:
        """Test running python -m geofabric --help."""
        result = subprocess.run(
            [sys.executable, "-m", "geofabric", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "gf" in result.stdout.lower() or "geofabric" in result.stdout.lower()


class TestDatasetOpenFunction:
    """Tests for dataset.open() function coverage."""

    def test_open_empty_file_uri(self) -> None:
        """Test open with empty file URI path."""
        import geofabric as gf

        with pytest.raises(InvalidURIError, match="Invalid file URI"):
            gf.open("file://")

    def test_open_nonexistent_path(self) -> None:
        """Test open with non-existent path."""
        import geofabric as gf

        with pytest.raises(InvalidURIError, match="does not exist"):
            gf.open("file:///nonexistent/path/file.parquet")

    def test_open_postgis_without_table(self) -> None:
        """Test open PostGIS without table parameter."""
        import geofabric as gf

        with pytest.raises(InvalidURIError, match="requires.*table"):
            gf.open("postgresql://user:pass@localhost/db")

    def test_open_unsupported_scheme(self) -> None:
        """Test open with unsupported URI scheme."""
        import geofabric as gf

        with pytest.raises(InvalidURIError, match="Unsupported URI"):
            gf.open("ftp://example.com/file.parquet")

    def test_open_s3_uri(self) -> None:
        """Test open with S3 URI creates S3Source."""
        import geofabric as gf
        from geofabric.sources.cloud import S3Source

        # Just test that it creates the right source type
        ds = gf.open("s3://my-bucket/data.parquet?region=us-east-1&anonymous=true")
        assert isinstance(ds.source, S3Source)
        assert ds.source.bucket == "my-bucket"
        assert ds.source.key == "data.parquet"

    def test_open_gcs_uri(self) -> None:
        """Test open with GCS URI creates GCSSource."""
        import geofabric as gf
        from geofabric.sources.cloud import GCSSource

        ds = gf.open("gs://my-bucket/data.parquet")
        assert isinstance(ds.source, GCSSource)
        assert ds.source.bucket == "my-bucket"

    def test_open_postgis_uri(self) -> None:
        """Test open with PostGIS URI creates PostGISSource."""
        import geofabric as gf
        from geofabric.sources.postgis import PostGISSource

        ds = gf.open("postgis://user:pass@localhost:5432/db?table=mytable&schema=myschema")
        assert isinstance(ds.source, PostGISSource)
        assert ds.source.table == "mytable"
        assert ds.source.schema == "myschema"


class TestDuckDBEngineErrors:
    """Tests for DuckDB engine error paths."""

    def test_unsupported_source_type(self) -> None:
        """Test engine with unsupported source type."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()

        class UnsupportedSource:
            pass

        with pytest.raises(EngineError, match="Unsupported source"):
            engine.source_to_relation_sql(UnsupportedSource())

    def test_overture_source_error(self) -> None:
        """Test engine with OvertureSource raises error."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.overture import OvertureSource

        engine = DuckDBEngine()
        source = OvertureSource(release="2025-01-01", theme="base", type_="test")

        with pytest.raises(EngineError, match="Download the data first"):
            engine.source_to_relation_sql(source)

    def test_unsupported_file_type(self) -> None:
        """Test engine with unsupported file type."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            from geofabric.sources.files import FilesSource

            source = FilesSource(temp_path)
            with pytest.raises(EngineError, match="Unsupported file type"):
                engine.source_to_relation_sql(source)
        finally:
            os.unlink(temp_path)

    def test_path_not_found(self) -> None:
        """Test engine with non-existent path."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.files import FilesSource

        engine = DuckDBEngine()
        source = FilesSource("/nonexistent/path/file.parquet")

        with pytest.raises(EngineError, match="Path not found"):
            engine.source_to_relation_sql(source)

    def test_query_to_df_error(self) -> None:
        """Test query_to_df with invalid SQL."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        with pytest.raises(EngineError, match="DuckDB query failed"):
            engine.query_to_df("SELECT * FROM nonexistent_table")

    def test_query_to_arrow_error(self) -> None:
        """Test query_to_arrow with invalid SQL."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        with pytest.raises(EngineError, match="DuckDB query failed"):
            engine.query_to_arrow("SELECT * FROM nonexistent_table")

    def test_copy_to_parquet_error(self) -> None:
        """Test copy_to_parquet with invalid SQL."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        with pytest.raises(EngineError, match="Failed to write parquet"):
            engine.copy_to_parquet("SELECT * FROM nonexistent", "/tmp/test.parquet")


class TestQueryBranches:
    """Tests for query.py branch coverage."""

    def test_to_geopandas_missing_geometry_column(self) -> None:
        """Test to_geopandas with missing geometry column."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            # Create parquet without geometry column
            table = pa.table({"id": pa.array([1, 2])})
            pq.write_table(table, path)

            ds = gf.open(f"file://{path}")
            q = ds.query()

            # Create a mock geopandas module
            mock_gpd = MagicMock()
            mock_gpd.GeoDataFrame = MagicMock()

            # Temporarily add mock geopandas to sys.modules
            original_gpd = sys.modules.get("geopandas")
            sys.modules["geopandas"] = mock_gpd

            try:
                with pytest.raises(ValueError, match="Expected geometry column"):
                    q.to_geopandas()
            finally:
                # Restore original state
                if original_gpd is not None:
                    sys.modules["geopandas"] = original_gpd
                elif "geopandas" in sys.modules:
                    del sys.modules["geopandas"]

    def test_to_parquet_without_geopandas(self) -> None:
        """Test to_parquet fallback when geopandas not available."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            input_path = os.path.join(td, "input.parquet")
            output_path = os.path.join(td, "output.parquet")
            _write_test_parquet(input_path)

            ds = gf.open(f"file://{input_path}")
            q = ds.query()

            # Mock to_geopandas to raise MissingDependencyError
            from geofabric.errors import MissingDependencyError

            with patch.object(q, "to_geopandas", side_effect=MissingDependencyError("test")):
                result = q.to_parquet(output_path)
                assert result == output_path
                assert os.path.exists(output_path)

    def test_to_pmtiles_invalid_minzoom(self) -> None:
        """Test to_pmtiles with negative minzoom."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query()

            with pytest.raises(ValueError, match="minzoom must be non-negative"):
                q.to_pmtiles("/tmp/out.pmtiles", minzoom=-1)

    def test_to_pmtiles_invalid_maxzoom(self) -> None:
        """Test to_pmtiles with negative maxzoom."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query()

            with pytest.raises(ValueError, match="maxzoom must be non-negative"):
                q.to_pmtiles("/tmp/out.pmtiles", maxzoom=-1)

    def test_to_pmtiles_minzoom_greater_than_maxzoom(self) -> None:
        """Test to_pmtiles with minzoom > maxzoom."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query()

            with pytest.raises(ValueError, match="minzoom.*must be <= maxzoom"):
                q.to_pmtiles("/tmp/out.pmtiles", minzoom=10, maxzoom=5)

    def test_show_without_lonboard(self) -> None:
        """Test show method when lonboard is not available."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query()

            with patch.dict("sys.modules", {"lonboard": None}):
                with patch("builtins.__import__", side_effect=ImportError):
                    result = q.show()
                    assert result is None

    def test_aggregate_with_by(self) -> None:
        """Test aggregate with by parameter."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            # Create parquet with category column
            point_wkb = bytes.fromhex("010100000000000000000000000000000000000000")
            table = pa.table(
                {
                    "id": pa.array([1, 2, 3], pa.int64()),
                    "geometry": pa.array([point_wkb, point_wkb, point_wkb], pa.binary()),
                    "category": pa.array(["a", "a", "b"], pa.string()),
                }
            )
            pq.write_table(table, path)

            ds = gf.open(f"file://{path}")
            q = ds.query()
            result = q.aggregate({"by": "category"})
            assert "group_key" in result.columns


class TestQueryWithMethods:
    """Tests for query.py with_* methods branches."""

    def test_with_area_without_star(self) -> None:
        """Test with_area when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_area()
            assert "ST_Area" in q.sql()

    def test_with_length_without_star(self) -> None:
        """Test with_length when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_length()
            assert "ST_Length" in q.sql()

    def test_with_bounds_without_star(self) -> None:
        """Test with_bounds when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_bounds()
            assert "ST_XMin" in q.sql()

    def test_with_geometry_type_without_star(self) -> None:
        """Test with_geometry_type when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_geometry_type()
            assert "ST_GeometryType" in q.sql()

    def test_with_num_points_without_star(self) -> None:
        """Test with_num_points when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_num_points()
            assert "ST_NPoints" in q.sql()

    def test_with_is_valid_without_star(self) -> None:
        """Test with_is_valid when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_is_valid()
            assert "ST_IsValid" in q.sql()

    def test_with_distance_to_without_star(self) -> None:
        """Test with_distance_to when _select doesn't have *."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{path}")
            q = ds.query().select(["id", "geometry"]).with_distance_to("POINT(0 0)")
            assert "ST_Distance" in q.sql()


class TestDuckDBEngineFactory:
    """Tests for DuckDBEngineFactory."""

    def test_factory_creates_engine(self) -> None:
        """Test that factory creates a DuckDBEngine."""
        from geofabric.engines.duckdb_engine import DuckDBEngine, DuckDBEngineFactory

        # Factory is now an instance of EngineClassFactory
        engine = DuckDBEngineFactory()
        assert isinstance(engine, DuckDBEngine)


class TestDuckDBSpatialExtension:
    """Tests for DuckDB spatial extension loading."""

    def test_spatial_extension_already_loaded(self) -> None:
        """Test _ensure_spatial when already loaded."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        engine._spatial_loaded = True
        # Should return immediately without error
        engine._ensure_spatial()

    @patch("duckdb.DuckDBPyConnection.execute")
    def test_spatial_extension_network_error(self, mock_execute: MagicMock) -> None:
        """Test _ensure_spatial with network error."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        # First call to LOAD fails, second call to INSTALL also fails with network error
        error_msg = "Failed to download extension"
        mock_execute.side_effect = duckdb.Error(error_msg)

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute = mock_execute

        with pytest.raises(EngineError, match="Could not download"):
            engine._ensure_spatial()


class TestFilesSource:
    """Tests for files source."""

    def test_files_source_directory(self) -> None:
        """Test FilesSource with directory."""
        import geofabric as gf

        with tempfile.TemporaryDirectory() as td:
            # Create a parquet file in the directory
            path = os.path.join(td, "test.parquet")
            _write_test_parquet(path)

            ds = gf.open(f"file://{td}")
            # Should be able to query directory of parquet files
            sql = ds.query().sql()
            assert "*.parquet" in sql


class TestCacheModule:
    """Tests for cache.py coverage."""

    def test_query_cache_basic(self) -> None:
        """Test QueryCache set and get operations."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td, enabled=True)
            cache = QueryCache(config)

            # Put a value
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                _write_test_parquet(f.name)
                cache.put("SELECT *", "file:///test", f.name)

            # Get the value
            result = cache.get("SELECT *", "file:///test")
            assert result is not None
            assert result.exists()

    def test_query_cache_miss(self) -> None:
        """Test QueryCache miss returns None."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td, enabled=True)
            cache = QueryCache(config)

            result = cache.get("SELECT *", "file:///nonexistent")
            assert result is None

    def test_query_cache_disabled(self) -> None:
        """Test QueryCache when disabled."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td, enabled=False)
            cache = QueryCache(config)

            result = cache.get("SELECT *", "file:///test")
            assert result is None

    def test_query_cache_clear(self) -> None:
        """Test QueryCache clear."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td, enabled=True)
            cache = QueryCache(config)

            # Put a value
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                _write_test_parquet(f.name)
                cache.put("SELECT *", "file:///test", f.name)

            # Clear
            count = cache.clear()
            assert count >= 1

    def test_query_cache_size_mb(self) -> None:
        """Test QueryCache size_mb."""
        from geofabric.cache import CacheConfig, QueryCache

        with tempfile.TemporaryDirectory() as td:
            config = CacheConfig(cache_dir=td, enabled=True)
            cache = QueryCache(config)

            size = cache.size_mb()
            assert size >= 0

    def test_get_cache_global(self) -> None:
        """Test get_cache returns global cache."""
        from geofabric.cache import get_cache

        cache = get_cache()
        assert cache is not None

    def test_configure_cache(self) -> None:
        """Test configure_cache."""
        from geofabric.cache import configure_cache, get_cache

        with tempfile.TemporaryDirectory() as td:
            configure_cache(cache_dir=td, enabled=True, max_size_mb=500)
            cache = get_cache()
            assert cache.max_size_mb == 500


class TestSourcesCloud:
    """Tests for cloud sources."""

    def test_s3_source_attrs(self) -> None:
        """Test S3Source attributes."""
        from geofabric.sources.cloud import S3Source

        source = S3Source(bucket="b", key="k", region="us-east-1", anonymous=False)
        assert source.bucket == "b"
        assert source.key == "k"
        assert source.region == "us-east-1"
        assert source.anonymous is False

    def test_gcs_source_attrs(self) -> None:
        """Test GCSSource attributes."""
        from geofabric.sources.cloud import GCSSource

        source = GCSSource(bucket="b", key="k")
        assert source.bucket == "b"
        assert source.key == "k"
