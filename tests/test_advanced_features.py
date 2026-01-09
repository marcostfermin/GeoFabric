"""Tests for advanced features: area, length, dissolve, additional spatial ops."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestAreaAndLengthMethods:
    """Tests for area and length computation methods."""

    def test_with_area(self) -> None:
        """Test with_area adds area column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_area()

        assert result is not None
        sql = result.sql()
        assert "ST_Area" in sql
        assert "AS area" in sql

    def test_with_area_custom_column(self) -> None:
        """Test with_area with custom column name."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_area(column_name="surface_area")

        sql = result.sql()
        assert "AS surface_area" in sql

    def test_with_length(self) -> None:
        """Test with_length adds length column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_length()

        sql = result.sql()
        assert "ST_Length" in sql
        assert "AS length" in sql

    def test_with_perimeter(self) -> None:
        """Test with_perimeter uses ST_Perimeter for polygon perimeters."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_perimeter(column_name="perimeter")

        sql = result.sql()
        assert "ST_Perimeter" in sql
        assert "AS perimeter" in sql

    def test_with_bounds(self) -> None:
        """Test with_bounds adds bounding box columns."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_bounds()

        sql = result.sql()
        assert "ST_XMin" in sql
        assert "ST_YMin" in sql
        assert "ST_XMax" in sql
        assert "ST_YMax" in sql
        assert "minx" in sql
        assert "miny" in sql
        assert "maxx" in sql
        assert "maxy" in sql

    def test_with_geometry_type(self) -> None:
        """Test with_geometry_type adds geometry type column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_geometry_type()

        sql = result.sql()
        assert "ST_GeometryType" in sql
        assert "AS geom_type" in sql

    def test_with_num_points(self) -> None:
        """Test with_num_points adds point count column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_num_points()

        sql = result.sql()
        assert "ST_NPoints" in sql
        assert "AS num_points" in sql

    def test_with_is_valid(self) -> None:
        """Test with_is_valid adds validity column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_is_valid()

        sql = result.sql()
        assert "ST_IsValid" in sql
        assert "AS is_valid" in sql


class TestAdditionalSpatialOperations:
    """Tests for additional spatial operations."""

    def test_point_on_surface_op(self) -> None:
        """Test PointOnSurfaceOp generates correct SQL."""
        from geofabric.spatial import PointOnSurfaceOp

        op = PointOnSurfaceOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_PointOnSurface" in sql

    def test_reverse_op(self) -> None:
        """Test ReverseOp generates correct SQL."""
        from geofabric.spatial import ReverseOp

        op = ReverseOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_Reverse" in sql

    def test_flip_coordinates_op(self) -> None:
        """Test FlipCoordinatesOp generates correct SQL."""
        from geofabric.spatial import FlipCoordinatesOp

        op = FlipCoordinatesOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_FlipCoordinates" in sql

    def test_area_op(self) -> None:
        """Test AreaOp generates correct SQL."""
        from geofabric.spatial import AreaOp

        op = AreaOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_Area" in sql

    def test_length_op(self) -> None:
        """Test LengthOp generates correct SQL."""
        from geofabric.spatial import LengthOp

        op = LengthOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_Length" in sql

    def test_query_point_on_surface(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.point_on_surface method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)
        result = q.point_on_surface()

        assert result is not None
        sql = result.sql()
        assert "ST_PointOnSurface" in sql

    def test_query_reverse(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.reverse method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)
        result = q.reverse()

        assert result is not None
        sql = result.sql()
        assert "ST_Reverse" in sql

    def test_query_flip_coordinates(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.flip_coordinates method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)
        result = q.flip_coordinates()

        assert result is not None
        sql = result.sql()
        assert "ST_FlipCoordinates" in sql


class TestDissolve:
    """Tests for dissolve operation."""

    def test_dissolve_all(self) -> None:
        """Test dissolve without grouping."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.dissolve()

        assert result is not None
        # Check the underlying SQLSource contains the dissolve SQL
        assert isinstance(result.dataset.source, SQLSource)
        assert "ST_Union_Agg" in result.dataset.source.sql

    def test_dissolve_by_column(self) -> None:
        """Test dissolve grouped by column."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.dissolve(by="category")

        assert isinstance(result.dataset.source, SQLSource)
        sql = result.dataset.source.sql
        assert "ST_Union_Agg" in sql
        assert "GROUP BY" in sql
        assert "category" in sql

    def test_dissolve_by_multiple_columns(self) -> None:
        """Test dissolve grouped by multiple columns."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.dissolve(by=["category", "subcategory"])

        assert isinstance(result.dataset.source, SQLSource)
        sql = result.dataset.source.sql
        assert "ST_Union_Agg" in sql
        assert "GROUP BY" in sql
        assert "category" in sql
        assert "subcategory" in sql


class TestSpatialPredicates:
    """Tests for spatial join predicates."""

    def test_sjoin_touches(self) -> None:
        """Test sjoin with touches predicate."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="touches")
        assert isinstance(result.dataset.source, SQLSource)
        assert "ST_Touches" in result.dataset.source.sql

    def test_sjoin_crosses(self) -> None:
        """Test sjoin with crosses predicate."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="crosses")
        assert isinstance(result.dataset.source, SQLSource)
        assert "ST_Crosses" in result.dataset.source.sql

    def test_sjoin_overlaps(self) -> None:
        """Test sjoin with overlaps predicate."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="overlaps")
        assert isinstance(result.dataset.source, SQLSource)
        assert "ST_Overlaps" in result.dataset.source.sql

    def test_sjoin_invalid_predicate(self) -> None:
        """Test sjoin rejects invalid predicate."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="Unknown predicate"):
            q1.sjoin(q2, predicate="invalid_predicate")


class TestProgressIndicators:
    """Tests for progress tracking utilities."""

    def test_progress_tracker_context(self) -> None:
        """Test ProgressTracker works as context manager."""
        from geofabric.util import ProgressTracker

        with ProgressTracker("Test", total=10, show_progress=False) as progress:
            for _ in range(10):
                progress.advance()

        # Should complete without error

    def test_progress_bar_generator(self) -> None:
        """Test progress_bar wraps iterables."""
        from geofabric.util import progress_bar

        items = list(range(5))
        result = list(progress_bar(items, show_progress=False))

        assert result == items

    def test_progress_tracker_methods(self) -> None:
        """Test ProgressTracker methods work when progress is disabled."""
        from geofabric.util import ProgressTracker

        with ProgressTracker("Test", total=10, show_progress=False) as progress:
            progress.advance(5)
            progress.update(7)
            progress.set_description("New description")


class TestNewCLICommands:
    """Tests for new CLI commands."""

    def test_centroid_command_exists(self) -> None:
        """Test centroid command is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "centroid")
        assert callable(cli_app.centroid)

    def test_convex_hull_command_exists(self) -> None:
        """Test convex_hull command is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "convex_hull")
        assert callable(cli_app.convex_hull)

    def test_dissolve_command_exists(self) -> None:
        """Test dissolve command is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "dissolve")
        assert callable(cli_app.dissolve)

    def test_add_area_command_exists(self) -> None:
        """Test add_area command is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "add_area")
        assert callable(cli_app.add_area)

    def test_add_length_command_exists(self) -> None:
        """Test add_length command is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "add_length")
        assert callable(cli_app.add_length)


class TestSpatialAllExports:
    """Tests for spatial module __all__ exports."""

    def test_new_ops_exported(self) -> None:
        """Test new spatial operations are exported."""
        from geofabric import spatial

        assert "AreaOp" in spatial.__all__
        assert "LengthOp" in spatial.__all__
        assert "PointOnSurfaceOp" in spatial.__all__
        assert "ReverseOp" in spatial.__all__
        assert "FlipCoordinatesOp" in spatial.__all__


class TestUtilAllExports:
    """Tests for util module __all__ exports."""

    def test_progress_utilities_exported(self) -> None:
        """Test progress utilities are exported."""
        from geofabric import util

        assert "ProgressTracker" in util.__all__
        assert "progress_bar" in util.__all__


class TestDistanceAndCoordinates:
    """Tests for distance and coordinate extraction methods."""

    def test_with_distance_to(self) -> None:
        """Test with_distance_to adds distance column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_distance_to("POINT(0 0)")

        sql = result.sql()
        assert "ST_Distance" in sql
        assert "POINT(0 0)" in sql
        assert "AS distance" in sql

    def test_with_distance_to_custom_column(self) -> None:
        """Test with_distance_to with custom column name."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_distance_to("POINT(0 0)", column_name="dist_to_origin")

        sql = result.sql()
        assert "AS dist_to_origin" in sql

    def test_with_x(self) -> None:
        """Test with_x adds X coordinate column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_x()

        sql = result.sql()
        assert "ST_X" in sql
        assert "ST_Centroid" in sql
        assert "AS x" in sql

    def test_with_y(self) -> None:
        """Test with_y adds Y coordinate column."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_y()

        sql = result.sql()
        assert "ST_Y" in sql
        assert "ST_Centroid" in sql
        assert "AS y" in sql

    def test_with_coordinates(self) -> None:
        """Test with_coordinates adds both X and Y columns."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.with_coordinates()

        sql = result.sql()
        assert "ST_X" in sql
        assert "ST_Y" in sql
        assert "AS x" in sql
        assert "AS y" in sql


class TestCollectAndSymmetricDifference:
    """Tests for collect and symmetric_difference methods."""

    def test_collect(self) -> None:
        """Test collect gathers geometries into MultiGeometry."""
        from geofabric.query import Query, SQLSource

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)
        result = q.collect()

        assert isinstance(result.dataset.source, SQLSource)
        assert "ST_Collect" in result.dataset.source.sql

    def test_symmetric_difference(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test symmetric_difference computes XOR."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)
        result = q.symmetric_difference("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")

        sql = result.sql()
        assert "ST_SymDifference" in sql

    def test_symmetric_difference_op(self) -> None:
        """Test SymmetricDifferenceOp generates correct SQL."""
        from geofabric.spatial import SymmetricDifferenceOp

        op = SymmetricDifferenceOp(geometry_col="geom", other_wkt="POINT(0 0)")
        sql = op.to_sql("geom")
        assert "ST_SymDifference" in sql
        assert "POINT(0 0)" in sql
