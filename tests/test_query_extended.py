"""Extended tests for Query module."""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestQuerySpatialOps:
    """Tests for Query spatial operations."""

    def _make_query(self):
        """Create a mock query for testing."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"
        return Query(dataset=mock_dataset)

    def test_query_buffer(self) -> None:
        """Test Query.buffer method."""
        q = self._make_query()
        result = q.buffer(distance=100, unit="meters")
        assert result is not None

    def test_query_simplify(self) -> None:
        """Test Query.simplify method."""
        q = self._make_query()
        result = q.simplify(tolerance=0.001)
        assert result is not None

    def test_query_simplify_no_topology(self) -> None:
        """Test Query.simplify with preserve_topology=False."""
        q = self._make_query()
        result = q.simplify(tolerance=0.001, preserve_topology=False)
        assert result is not None

    def test_query_centroid(self) -> None:
        """Test Query.centroid method."""
        q = self._make_query()
        result = q.centroid()
        assert result is not None

    def test_query_convex_hull(self) -> None:
        """Test Query.convex_hull method."""
        q = self._make_query()
        result = q.convex_hull()
        assert result is not None

    def test_query_envelope(self) -> None:
        """Test Query.envelope method."""
        q = self._make_query()
        result = q.envelope()
        assert result is not None


class TestQueryIterators:
    """Tests for Query iterator methods."""

    def test_query_iter_chunks(self) -> None:
        """Test Query.iter_chunks method."""
        import pyarrow as pa

        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_table = pa.table({"id": [1, 2, 3]})
        mock_dataset.engine.query_to_arrow.return_value = mock_table
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        chunks = list(q.iter_chunks(chunk_size=2))
        assert len(chunks) >= 1

    def test_query_iter_dataframes(self) -> None:
        """Test Query.iter_dataframes method."""
        import pyarrow as pa

        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_table = pa.table({"id": [1, 2, 3, 4, 5]})
        mock_dataset.engine.query_to_arrow.return_value = mock_table
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        dfs = list(q.iter_dataframes(chunk_size=2))
        assert all(isinstance(df, pd.DataFrame) for df in dfs)


class TestQueryExportFormats:
    """Tests for Query export format methods."""

    def test_query_to_flatgeobuf(self) -> None:
        """Test Query.to_flatgeobuf method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        # Mock the to_geopandas method to return a mock GeoDataFrame
        mock_gdf = MagicMock()
        with patch.object(q, "to_geopandas", return_value=mock_gdf):
            with tempfile.NamedTemporaryFile(suffix=".fgb", delete=False) as f:
                result = q.to_flatgeobuf(f.name)
                assert result == f.name
                mock_gdf.to_file.assert_called_once_with(f.name, driver="FlatGeobuf")

    def test_query_to_geopackage(self) -> None:
        """Test Query.to_geopackage method."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        # Mock the to_geopandas method to return a mock GeoDataFrame
        mock_gdf = MagicMock()
        with patch.object(q, "to_geopandas", return_value=mock_gdf):
            with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
                result = q.to_geopackage(f.name, layer="test_layer")
                assert result == f.name
                mock_gdf.to_file.assert_called_once_with(f.name, driver="GPKG", layer="test_layer")

    def test_query_to_csv_with_wkt(self) -> None:
        """Test Query.to_csv with WKT conversion."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": [1, 2],
            "geometry_wkt": ["POINT(0 0)", "POINT(1 1)"],
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = q.to_csv(f.name, include_wkt=True)
            assert result == f.name

    def test_query_to_csv_no_wkt(self) -> None:
        """Test Query.to_csv without WKT conversion."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": [1, 2],
            "geometry": [b"test", b"test2"],
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = q.to_csv(f.name, include_wkt=False)
            assert result == f.name


class TestQueryShow:
    """Tests for Query.show method."""

    def test_query_show_no_lonboard(self) -> None:
        """Test Query.show when lonboard not installed."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        q = Query(dataset=mock_dataset)

        with patch.dict("sys.modules", {"lonboard": None}):
            result = q.show()
            assert result is None


class TestQueryWithROI:
    """Tests for Query.within method with ROI."""

    def test_query_within_bbox(self) -> None:
        """Test Query.within with bbox ROI."""
        from geofabric.query import Query
        from geofabric.roi import bbox

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"
        q = Query(dataset=mock_dataset)

        roi = bbox(-122, 37, -121, 38)
        result = q.within(roi)

        assert len(result._where) == 1
        assert "ST_Intersects" in result._where[0]

    def test_query_within_wkt(self) -> None:
        """Test Query.within with WKT ROI."""
        from geofabric.query import Query
        from geofabric.roi import wkt

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"
        q = Query(dataset=mock_dataset)

        roi = wkt("POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))")
        result = q.within(roi)

        assert len(result._where) == 1
        assert "ST_Intersects" in result._where[0]


class TestQueryAggregate:
    """Tests for Query.aggregate method."""

    def test_query_aggregate_with_by(self) -> None:
        """Test Query.aggregate with grouping."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "group_key": ["a", "b"],
            "count": [10, 20],
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.aggregate({"by": "category"})

        assert isinstance(result, pd.DataFrame)

    def test_query_aggregate_without_by(self) -> None:
        """Test Query.aggregate without grouping."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "count": [30],
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.aggregate({})

        assert isinstance(result, pd.DataFrame)


class TestQueryProperties:
    """Tests for Query properties."""

    def test_query_columns_property(self) -> None:
        """Test Query.columns property."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": pd.Series(dtype="int64"),
            "name": pd.Series(dtype="object"),
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        cols = q.columns

        assert "id" in cols
        assert "name" in cols

    def test_query_dtypes_property(self) -> None:
        """Test Query.dtypes property."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.query_to_df.return_value = pd.DataFrame({
            "id": pd.Series(dtype="int64"),
            "name": pd.Series(dtype="object"),
        })
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        dtypes = q.dtypes

        assert "id" in dtypes
        assert "name" in dtypes


class TestQueryParquet:
    """Tests for Query.to_parquet method."""

    def test_query_to_parquet_fallback(self) -> None:
        """Test Query.to_parquet falls back when geopandas fails."""
        from geofabric.errors import MissingDependencyError
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        # Make to_geopandas fail with MissingDependencyError (no geopandas installed)
        with patch.object(q, "to_geopandas", side_effect=MissingDependencyError("no geopandas")):
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                result = q.to_parquet(f.name)
                assert result == f.name
                mock_dataset.engine.copy_to_parquet.assert_called_once()


class TestWrapSqlAsQuery:
    """Tests for _wrap_sql_as_query helper."""

    def test_wrap_sql_as_query(self) -> None:
        """Test _wrap_sql_as_query creates a new query."""
        from geofabric.query import SQLSource, _wrap_sql_as_query

        mock_dataset = MagicMock()
        result = _wrap_sql_as_query(mock_dataset, "SELECT * FROM test")

        assert isinstance(result.dataset.source, SQLSource)
        assert result.dataset.source.sql == "SELECT * FROM test"
