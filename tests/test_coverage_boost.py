"""Additional tests to boost code coverage to 100%."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestDuckDBEngineExtended:
    """Extended tests for DuckDBEngine coverage."""

    def test_engine_kind(self) -> None:
        """Test engine_kind returns duckdb."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        assert engine.engine_kind() == "duckdb"

    def test_ensure_spatial_already_loaded(self) -> None:
        """Test _ensure_spatial returns early when already loaded."""
        from geofabric.engines.duckdb_engine import DuckDBEngine

        engine = DuckDBEngine()
        engine._spatial_loaded = True
        # Should return immediately without doing anything
        engine._ensure_spatial()
        assert engine._spatial_loaded is True

    def test_ensure_spatial_load_failure(self) -> None:
        """Test _ensure_spatial handles generic load failure."""
        import duckdb

        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute.side_effect = duckdb.Error("Generic error")

        with pytest.raises(EngineError, match="Failed to load spatial extension"):
            engine._ensure_spatial()

    def test_ensure_spatial_network_error(self) -> None:
        """Test _ensure_spatial handles network error."""
        import duckdb

        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute.side_effect = duckdb.Error("Failed to download extension")

        with pytest.raises(EngineError, match="Could not download"):
            engine._ensure_spatial()

    def test_files_source_directory(self) -> None:
        """Test FilesSource.to_duckdb_relation_sql with directory."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.files import FilesSource

        with tempfile.TemporaryDirectory() as td:
            engine = DuckDBEngine()
            source = FilesSource(path=td)
            sql = source.to_duckdb_relation_sql(engine)
            assert "read_parquet" in sql
            assert "*.parquet" in sql

    def test_files_source_unsupported_type(self) -> None:
        """Test FilesSource.to_duckdb_relation_sql with unsupported file type."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError
        from geofabric.sources.files import FilesSource

        with tempfile.NamedTemporaryFile(suffix=".xyz") as f:
            engine = DuckDBEngine()
            source = FilesSource(path=f.name)
            with pytest.raises(EngineError, match="Unsupported file type"):
                source.to_duckdb_relation_sql(engine)

    def test_files_source_path_not_found(self) -> None:
        """Test FilesSource.to_duckdb_relation_sql with non-existent path."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError
        from geofabric.sources.files import FilesSource

        engine = DuckDBEngine()
        source = FilesSource(path="/nonexistent/path")
        with pytest.raises(EngineError, match="Path not found"):
            source.to_duckdb_relation_sql(engine)

    def test_files_source_geojson(self) -> None:
        """Test FilesSource.to_duckdb_relation_sql with GeoJSON file."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.files import FilesSource

        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as f:
            f.write(b'{"type":"FeatureCollection","features":[]}')
            f.flush()
            engine = DuckDBEngine()
            engine._spatial_loaded = True  # Pretend spatial is loaded
            engine._con = MagicMock()
            source = FilesSource(path=f.name)
            sql = source.to_duckdb_relation_sql(engine)
            assert "ST_Read" in sql

    def test_source_to_relation_sql_source(self) -> None:
        """Test source_to_relation_sql with SQLSource."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.query import SQLSource

        engine = DuckDBEngine()
        source = SQLSource(sql="SELECT * FROM test")
        result = engine.source_to_relation_sql(source)
        assert result == "(SELECT * FROM test)"

    def test_source_to_relation_unsupported(self) -> None:
        """Test source_to_relation_sql with unsupported source type."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        with pytest.raises(EngineError, match="Unsupported source type"):
            engine.source_to_relation_sql("not a source")

    def test_query_to_df_error(self) -> None:
        """Test query_to_df handles errors."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute.side_effect = Exception("Query failed")

        with pytest.raises(EngineError, match="DuckDB query failed"):
            engine.query_to_df("SELECT * FROM nonexistent")

    def test_query_to_arrow_error(self) -> None:
        """Test query_to_arrow handles errors."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute.side_effect = Exception("Query failed")

        with pytest.raises(EngineError, match="DuckDB query failed"):
            engine.query_to_arrow("SELECT * FROM nonexistent")

    def test_copy_to_parquet_error(self) -> None:
        """Test copy_to_parquet handles errors."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._con.execute.side_effect = Exception("Write failed")

        with pytest.raises(EngineError, match="Failed to write parquet"):
            engine.copy_to_parquet("SELECT 1", "/tmp/test.parquet")

    def test_copy_to_geojson_error(self) -> None:
        """Test copy_to_geojson handles errors."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.errors import EngineError

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._spatial_loaded = True
        engine._con.execute.side_effect = Exception("Write failed")

        with pytest.raises(EngineError, match="Failed to write geojson"):
            engine.copy_to_geojson("SELECT 1", "/tmp/test.geojson")

    def test_s3_source_relation_sql(self) -> None:
        """Test S3Source.to_duckdb_relation_sql."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.cloud import S3Source

        engine = DuckDBEngine()
        engine._con = MagicMock()
        source = S3Source(bucket="test-bucket", key="data.parquet", region="us-east-1")
        result = source.to_duckdb_relation_sql(engine)
        assert "read_parquet" in result
        assert "s3://test-bucket/data.parquet" in result

    def test_s3_source_relation_sql_non_parquet(self) -> None:
        """Test S3Source.to_duckdb_relation_sql with non-parquet file."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.cloud import S3Source

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._spatial_loaded = True
        source = S3Source(bucket="test-bucket", key="data.geojson")
        result = source.to_duckdb_relation_sql(engine)
        assert "ST_Read" in result

    def test_gcs_source_relation_sql(self) -> None:
        """Test GCSSource.to_duckdb_relation_sql."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.cloud import GCSSource

        engine = DuckDBEngine()
        engine._con = MagicMock()
        source = GCSSource(bucket="test-bucket", key="data.parquet")
        result = source.to_duckdb_relation_sql(engine)
        assert "read_parquet" in result

    def test_postgis_source_relation_sql(self) -> None:
        """Test PostGISSource.to_duckdb_relation_sql."""
        from geofabric.engines.duckdb_engine import DuckDBEngine
        from geofabric.sources.postgis import PostGISSource

        engine = DuckDBEngine()
        engine._con = MagicMock()
        engine._spatial_loaded = True
        source = PostGISSource(
            host="localhost",
            port=5432,
            database="test",
            user="user",
            password="pass",
            table="mytable",
        )
        result = source.to_duckdb_relation_sql(engine)
        # PostGIS geometry comes through as WKB_BLOB, no ST_AsWKB needed
        assert "mytable" in result
        assert "geometry" in result

    def test_duckdb_engine_factory(self) -> None:
        """Test DuckDBEngineFactory."""
        from geofabric.engines.duckdb_engine import DuckDBEngine, DuckDBEngineFactory

        # Factory is now an instance of EngineClassFactory
        # Calling it directly returns an engine instance
        engine = DuckDBEngineFactory()
        assert isinstance(engine, DuckDBEngine)
        assert engine.database == ":memory:"


class TestCloudSourcesExtended:
    """Extended tests for cloud sources."""

    def test_s3_source_from_uri(self) -> None:
        """Test S3Source.from_uri."""
        from geofabric.sources.cloud import S3Source

        src = S3Source.from_uri("s3://my-bucket/path/to/file.parquet")
        assert src.bucket == "my-bucket"
        assert src.key == "path/to/file.parquet"

    def test_s3_source_from_uri_invalid(self) -> None:
        """Test S3Source.from_uri with invalid URI."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.cloud import S3Source

        with pytest.raises(InvalidURIError, match="Not an S3 URI"):
            S3Source.from_uri("http://example.com")

    def test_s3_source_from_uri_no_bucket(self) -> None:
        """Test S3Source.from_uri with missing bucket."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.cloud import S3Source

        with pytest.raises(InvalidURIError, match="Missing bucket"):
            S3Source.from_uri("s3:///path/to/file")

    def test_s3_source_to_duckdb_path(self) -> None:
        """Test S3Source.to_duckdb_path."""
        from geofabric.sources.cloud import S3Source

        src = S3Source(bucket="my-bucket", key="data.parquet")
        assert src.to_duckdb_path() == "s3://my-bucket/data.parquet"

    def test_gcs_source_from_uri(self) -> None:
        """Test GCSSource.from_uri."""
        from geofabric.sources.cloud import GCSSource

        src = GCSSource.from_uri("gs://my-bucket/path/to/file.parquet")
        assert src.bucket == "my-bucket"
        assert src.key == "path/to/file.parquet"

    def test_gcs_source_from_uri_gcs_scheme(self) -> None:
        """Test GCSSource.from_uri with gcs:// scheme."""
        from geofabric.sources.cloud import GCSSource

        src = GCSSource.from_uri("gcs://my-bucket/data.parquet")
        assert src.bucket == "my-bucket"

    def test_gcs_source_from_uri_invalid(self) -> None:
        """Test GCSSource.from_uri with invalid URI."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.cloud import GCSSource

        with pytest.raises(InvalidURIError, match="Not a GCS URI"):
            GCSSource.from_uri("http://example.com")

    def test_gcs_source_from_uri_no_bucket(self) -> None:
        """Test GCSSource.from_uri with missing bucket."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.cloud import GCSSource

        with pytest.raises(InvalidURIError, match="Missing bucket"):
            GCSSource.from_uri("gs:///path/to/file")

    def test_gcs_source_to_duckdb_path(self) -> None:
        """Test GCSSource.to_duckdb_path."""
        from geofabric.sources.cloud import GCSSource

        src = GCSSource(bucket="my-bucket", key="data.parquet")
        assert src.to_duckdb_path() == "gcs://my-bucket/data.parquet"

    def test_s3_source_factory(self) -> None:
        """Test S3SourceFactory."""
        from geofabric.sources.cloud import S3Source, S3SourceFactory

        # Factory is now an instance of SourceClassFactory
        # Calling it directly returns the source class
        assert S3SourceFactory() is S3Source

    def test_gcs_source_factory(self) -> None:
        """Test GCSSourceFactory."""
        from geofabric.sources.cloud import GCSSource, GCSSourceFactory

        # Factory is now an instance of SourceClassFactory
        assert GCSSourceFactory() is GCSSource


class TestPostGISSourceExtended:
    """Extended tests for PostGIS source."""

    def test_postgis_source_from_uri(self) -> None:
        """Test PostGISSource.from_uri."""
        from geofabric.sources.postgis import PostGISSource

        uri = "postgresql://user:pass@localhost:5432/mydb?table=mytable&schema=public"
        src = PostGISSource.from_uri(uri)
        assert src.host == "localhost"
        assert src.port == 5432
        assert src.database == "mydb"
        assert src.user == "user"
        assert src.password == "pass"
        assert src.table == "mytable"
        assert src.schema == "public"

    def test_postgis_source_from_uri_no_table(self) -> None:
        """Test PostGISSource.from_uri without table - allowed but qualified_table_name raises."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.postgis import PostGISSource

        # from_uri allows table=None
        src = PostGISSource.from_uri("postgresql://user:pass@localhost/mydb")
        assert src.table is None
        # But qualified_table_name raises when no table specified
        with pytest.raises(InvalidURIError, match="No table specified"):
            src.qualified_table_name()

    def test_postgis_source_from_uri_invalid(self) -> None:
        """Test PostGISSource.from_uri with invalid scheme."""
        from geofabric.errors import InvalidURIError
        from geofabric.sources.postgis import PostGISSource

        with pytest.raises(InvalidURIError, match="Not a PostGIS URI"):
            PostGISSource.from_uri("http://example.com")

    def test_postgis_source_connection_string(self) -> None:
        """Test PostGISSource.connection_string."""
        from geofabric.sources.postgis import PostGISSource

        src = PostGISSource(
            host="localhost",
            port=5432,
            database="test",
            user="user",
            password="pass",
            table="mytable",
        )
        conn_str = src.connection_string()
        # Returns postgresql:// URI format
        assert conn_str == "postgresql://user:pass@localhost:5432/test"

    def test_postgis_source_factory(self) -> None:
        """Test PostGISSourceFactory."""
        from geofabric.sources.postgis import PostGISSource, PostGISSourceFactory

        # Factory is now an instance of SourceClassFactory
        assert PostGISSourceFactory() is PostGISSource


class TestSTACSourceExtended:
    """Extended tests for STAC source."""

    def test_stac_source_creation(self) -> None:
        """Test STACSource creation."""
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
            asset_key="data",
        )
        assert src.catalog_url == "https://example.com/stac"
        assert src.collection == "test-collection"

    def test_stac_source_search_items(self) -> None:
        """Test STACSource.search_items with mocked client."""
        import sys

        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        # Create a mock pystac_client module
        mock_pystac_client = MagicMock()
        mock_client_class = MagicMock()
        mock_search = MagicMock()
        mock_item = MagicMock()
        mock_item.assets = {"data": MagicMock(href="https://example.com/data.tif")}
        mock_search.items.return_value = [mock_item]
        mock_client_class.open.return_value.search.return_value = mock_search
        mock_pystac_client.Client = mock_client_class

        # Inject mock module
        with patch.dict(sys.modules, {"pystac_client": mock_pystac_client}):
            items = src.search_items(max_items=10)
            assert len(items) == 1

    def test_stac_source_search_items_no_pystac(self) -> None:
        """Test STACSource.search_items when pystac_client not installed."""
        import sys

        from geofabric.errors import MissingDependencyError
        from geofabric.sources.stac import STACSource

        src = STACSource(
            catalog_url="https://example.com/stac",
            collection="test-collection",
        )

        # Temporarily remove pystac_client from sys.modules to simulate not installed
        original_modules = {}
        modules_to_remove = [k for k in sys.modules if k.startswith("pystac_client")]
        for mod in modules_to_remove:
            original_modules[mod] = sys.modules.pop(mod)

        # Also block future imports
        with patch.dict(sys.modules, {"pystac_client": None}):
            with pytest.raises((MissingDependencyError, ImportError)):
                src.search_items()

        # Restore modules
        sys.modules.update(original_modules)

    def test_stac_source_factory(self) -> None:
        """Test STACSourceFactory."""
        from geofabric.sources.stac import STACSource, STACSourceFactory

        # Factory is now an instance of SourceClassFactory
        assert STACSourceFactory() is STACSource


class TestValidationExtended:
    """Extended tests for validation module."""

    def test_validate_geometries(self) -> None:
        """Test validate_geometries function."""
        from geofabric.validation import validate_geometries

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({
            "_row_id": [1, 2, 3],
            "_validity": ["valid", "valid", "null"],
            "_reason": [None, None, None],
        })

        result = validate_geometries(mock_engine, "SELECT * FROM test")
        assert result.total_rows == 3
        assert result.valid_count == 2
        assert result.null_count == 1
        assert result.is_valid is True

    def test_validate_geometries_with_invalid(self) -> None:
        """Test validate_geometries with invalid geometries."""
        from geofabric.validation import validate_geometries

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({
            "_row_id": [1, 2],
            "_validity": ["valid", "invalid"],
            "_reason": [None, "Self-intersection"],
        })

        result = validate_geometries(mock_engine, "SELECT * FROM test")
        assert result.invalid_count == 1
        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].message == "Self-intersection"

    def test_compute_stats(self) -> None:
        """Test compute_stats function."""
        from geofabric.validation import compute_stats

        mock_engine = MagicMock()

        # Schema query
        mock_engine.query_to_df.side_effect = [
            pd.DataFrame({"id": pd.Series(dtype="int64"), "geometry": pd.Series(dtype="object")}),  # schema
            pd.DataFrame({"cnt": [100]}),  # count
            pd.DataFrame({"id_nulls": [0], "geometry_nulls": [5]}),  # null counts
            pd.DataFrame({"geom_type": ["GEOMETRY"]}),  # type detection query
            pd.DataFrame({  # bounds
                "minx": [-122.0],
                "miny": [37.0],
                "maxx": [-121.0],
                "maxy": [38.0],
                "geom_type": ["POLYGON"],
            }),
        ]

        result = compute_stats(mock_engine, "SELECT * FROM test")
        assert result.row_count == 100
        assert result.column_count == 2
        assert result.geometry_type == "POLYGON"

    def test_compute_stats_no_geometry(self) -> None:
        """Test compute_stats without geometry column."""
        from geofabric.validation import compute_stats

        mock_engine = MagicMock()
        mock_engine.query_to_df.side_effect = [
            pd.DataFrame({"id": pd.Series(dtype="int64")}),  # schema - no geometry
            pd.DataFrame({"cnt": [50]}),  # count
            pd.DataFrame({"id_nulls": [0]}),  # null counts
        ]

        result = compute_stats(mock_engine, "SELECT * FROM test")
        assert result.row_count == 50
        assert result.bounds is None
        assert result.geometry_type is None


class TestQueryExtended:
    """Extended tests for Query methods."""

    def _make_query(self):
        """Create a mock query for testing."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
        })
        return Query(dataset=mock_dataset)

    def test_query_sample(self) -> None:
        """Test Query.sample method."""
        q = self._make_query()
        result = q.sample(n=2, seed=42)
        assert isinstance(result, pd.DataFrame)

    def test_query_count(self) -> None:
        """Test Query.count method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({"cnt": [42]})
        q = Query(dataset=mock_dataset)
        assert q.count() == 42

    def test_query_explain(self) -> None:
        """Test Query.explain method."""
        q = self._make_query()
        result = q.explain()
        assert isinstance(result, str)

    def test_query_describe(self) -> None:
        """Test Query.describe method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.side_effect = [
            pd.DataFrame({"id": pd.Series(dtype="int64")}),  # schema
            pd.DataFrame({"cnt": [100]}),  # count
            pd.DataFrame({"id_nulls": [0]}),  # null counts
        ]
        q = Query(dataset=mock_dataset)
        result = q.describe()
        assert isinstance(result, pd.DataFrame)

    def test_query_to_csv(self) -> None:
        """Test Query.to_csv method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": [1, 2],
            "name": ["a", "b"],
        })
        q = Query(dataset=mock_dataset)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = q.to_csv(f.name, include_wkt=False)
            assert Path(result).exists()

    def test_query_dissolve(self) -> None:
        """Test Query.dissolve method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        q = Query(dataset=mock_dataset)
        result = q.dissolve(by="category")
        assert result is not None

    def test_query_dissolve_all(self) -> None:
        """Test Query.dissolve without grouping."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        q = Query(dataset=mock_dataset)
        result = q.dissolve()
        assert result is not None

    def test_sql_source(self) -> None:
        """Test SQLSource dataclass."""
        from geofabric.query import SQLSource

        src = SQLSource(sql="SELECT * FROM test")
        assert src.sql == "SELECT * FROM test"


class TestSpatialOpsExtended:
    """Extended tests for spatial operations."""

    def test_apply_spatial_op_star_select(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test apply_spatial_op with * select."""
        from geofabric.query import Query
        from geofabric.spatial import CentroidOp, apply_spatial_op

        q = Query(dataset=mock_dataset_for_spatial, _select=["*"])
        op = CentroidOp(geometry_col="geometry")
        result = apply_spatial_op(q, op)
        # After applying spatial op, the result wraps in a subquery with the transformation
        sql = result.sql()
        assert "EXCLUDE" in sql
        assert "ST_Centroid" in sql

    def test_apply_spatial_op_geometry_col(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test apply_spatial_op with geometry column in select."""
        from geofabric.query import Query
        from geofabric.spatial import CentroidOp, apply_spatial_op

        q = Query(dataset=mock_dataset_for_spatial, _select=["id", "geometry"])
        op = CentroidOp(geometry_col="geometry")
        result = apply_spatial_op(q, op)
        # After applying spatial op, the SQL contains the transformation
        sql = result.sql()
        assert "ST_Centroid" in sql

    def test_spatial_op_not_implemented(self) -> None:
        """Test SpatialOp.to_sql raises NotImplementedError."""
        from geofabric.spatial import SpatialOp

        op = SpatialOp(geometry_col="geometry")
        with pytest.raises(NotImplementedError):
            op.to_sql("geometry")

    def test_buffer_op_feet(self) -> None:
        """Test BufferOp with feet unit."""
        from geofabric.spatial import BufferOp

        op = BufferOp(distance=100, unit="feet")
        sql = op.to_sql("geometry")
        assert "30.48" in sql  # 100 * 0.3048


class TestDatasetExtended:
    """Extended tests for Dataset."""

    def test_dataset_within(self) -> None:
        """Test Dataset.within method."""
        from geofabric.dataset import Dataset
        from geofabric.roi import bbox

        mock_engine = MagicMock()
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        roi = bbox(-122, 37, -121, 38)
        q = ds.within(roi)
        assert q is not None

    def test_dataset_where(self) -> None:
        """Test Dataset.where method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        q = ds.where("id > 10")
        assert q is not None

    def test_dataset_select(self) -> None:
        """Test Dataset.select method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        q = ds.select(["id", "name"])
        assert q is not None

    def test_dataset_validate(self) -> None:
        """Test Dataset.validate method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.return_value = pd.DataFrame({
            "_row_id": [1],
            "_validity": ["valid"],
            "_reason": [None],
        })
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        result = ds.validate()
        assert result.is_valid

    def test_dataset_stats(self) -> None:
        """Test Dataset.stats method."""
        from geofabric.dataset import Dataset

        mock_engine = MagicMock()
        mock_engine.query_to_df.side_effect = [
            pd.DataFrame({"id": pd.Series(dtype="int64")}),
            pd.DataFrame({"cnt": [100]}),
            pd.DataFrame({"id_nulls": [0]}),
        ]
        ds = Dataset(source=MagicMock(), engine=mock_engine)
        result = ds.stats()
        assert result.row_count == 100


class TestROIExtended:
    """Extended tests for ROI module."""

    def test_bbox_roi(self) -> None:
        """Test bbox ROI creation."""
        from geofabric.roi import bbox

        roi = bbox(-122.5, 37.5, -122.0, 38.0)
        assert roi.minx == -122.5
        assert roi.miny == 37.5

    def test_wkt_roi(self) -> None:
        """Test WKT ROI creation."""
        from geofabric.roi import wkt

        roi = wkt("POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))")
        assert roi.wkt is not None
        assert "POLYGON" in roi.wkt


class TestRegistryExtended:
    """Extended tests for Registry."""

    def test_registry_sources_engines_sinks(self) -> None:
        """Test Registry with sources, engines, sinks."""
        from geofabric.registry import Registry

        reg = Registry(
            sources={"files": MagicMock()},
            engines={"duckdb": MagicMock()},
            sinks={"parquet": MagicMock()},
        )
        assert "files" in reg.sources
        assert "duckdb" in reg.engines
        assert "parquet" in reg.sinks


class TestFilesSource:
    """Tests for FilesSource."""

    def test_files_source_source_kind(self) -> None:
        """Test FilesSource.source_kind."""
        from geofabric.sources.files import FilesSource

        src = FilesSource(path="/tmp/test.parquet")
        assert src.source_kind() == "files"


class TestOvertureSource:
    """Tests for OvertureSource."""

    def test_overture_source_source_kind(self) -> None:
        """Test OvertureSource.source_kind."""
        from geofabric.sources.overture import OvertureSource

        src = OvertureSource(release="2025-01-01.0", theme="places", type_="place")
        assert src.source_kind() == "overture"


class TestPMTilesSink:
    """Tests for PMTilesSink."""

    def test_pmtiles_sink_kind(self) -> None:
        """Test PMTilesSink.sink_kind."""
        from geofabric.sinks.pmtiles import PMTilesSink

        sink = PMTilesSink()
        assert sink.sink_kind() == "pmtiles"

    def test_pmtiles_sink_factory(self) -> None:
        """Test PMTilesSinkFactory."""
        from geofabric.sinks.pmtiles import PMTilesSink, PMTilesSinkFactory

        # Factory is now an instance of SinkClassFactory
        sink = PMTilesSinkFactory()
        assert isinstance(sink, PMTilesSink)


class TestMainModule:
    """Tests for __main__ module."""

    def test_main_module_execution(self) -> None:
        """Test __main__ module can be imported."""
        import geofabric.__main__ as main_mod

        assert hasattr(main_mod, "main")
