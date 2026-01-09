"""Tests for new improvements: validation, spatial ops, CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestInputValidation:
    """Tests for input validation in spatial operations."""

    def test_buffer_negative_distance(self) -> None:
        """Test BufferOp rejects negative distance."""
        from geofabric.spatial import BufferOp

        with pytest.raises(ValueError, match="non-negative"):
            BufferOp(distance=-10)

    def test_buffer_invalid_unit(self) -> None:
        """Test BufferOp rejects invalid unit."""
        from geofabric.spatial import BufferOp

        with pytest.raises(ValueError, match="Invalid unit"):
            BufferOp(distance=100, unit="invalid")

    def test_buffer_valid_units(self) -> None:
        """Test BufferOp accepts all valid units."""
        from geofabric.spatial import BufferOp

        for unit in ["meters", "kilometers", "miles", "feet"]:
            op = BufferOp(distance=100, unit=unit)
            assert op.unit == unit

    def test_simplify_negative_tolerance(self) -> None:
        """Test SimplifyOp rejects negative tolerance."""
        from geofabric.spatial import SimplifyOp

        with pytest.raises(ValueError, match="non-negative"):
            SimplifyOp(tolerance=-0.01)

    def test_densify_non_positive_distance(self) -> None:
        """Test DensifyOp rejects non-positive max_distance."""
        from geofabric.spatial import DensifyOp

        with pytest.raises(ValueError, match="positive"):
            DensifyOp(max_distance=0)

        with pytest.raises(ValueError, match="positive"):
            DensifyOp(max_distance=-1)

    def test_nearest_invalid_k(self) -> None:
        """Test nearest() rejects k < 1."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="at least 1"):
            q1.nearest(q2, k=0)

    def test_nearest_invalid_max_distance(self) -> None:
        """Test nearest() rejects negative max_distance."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="positive"):
            q1.nearest(q2, k=1, max_distance=-100)

    def test_sjoin_invalid_how(self) -> None:
        """Test sjoin() rejects invalid how parameter."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="Invalid join type"):
            q1.sjoin(q2, how="outer")

    def test_to_pmtiles_invalid_zoom(self) -> None:
        """Test to_pmtiles() validates zoom levels."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="minzoom"):
            q.to_pmtiles("/tmp/test.pmtiles", minzoom=-1)

        with pytest.raises(ValueError, match="maxzoom"):
            q.to_pmtiles("/tmp/test.pmtiles", maxzoom=-1)

        with pytest.raises(ValueError, match="<="):
            q.to_pmtiles("/tmp/test.pmtiles", minzoom=10, maxzoom=5)


class TestNewSpatialOperations:
    """Tests for new spatial operations: boundary, explode, densify."""

    def test_boundary_op(self) -> None:
        """Test BoundaryOp generates correct SQL."""
        from geofabric.spatial import BoundaryOp

        op = BoundaryOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_Boundary" in sql
        assert "geometry" in sql

    def test_explode_op(self) -> None:
        """Test ExplodeOp generates correct SQL."""
        from geofabric.spatial import ExplodeOp

        op = ExplodeOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "UNNEST" in sql
        assert "ST_Dump" in sql
        assert "geom" in sql

    def test_densify_op(self) -> None:
        """Test DensifyOp generates correct SQL."""
        from geofabric.spatial import DensifyOp

        op = DensifyOp(geometry_col="geometry", max_distance=100.0)
        sql = op.to_sql("geometry")
        assert "ST_Segmentize" in sql
        assert "100.0" in sql

    def test_query_boundary(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.boundary method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.boundary()
        assert result is not None
        sql = result.sql()
        assert "ST_Boundary" in sql

    def test_query_explode(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.explode method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.explode()
        assert result is not None
        sql = result.sql()
        assert "ST_Dump" in sql

    def test_query_densify(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.densify method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.densify(max_distance=50.0)
        assert result is not None
        sql = result.sql()
        assert "ST_Segmentize" in sql
        assert "50.0" in sql


class TestAllExports:
    """Tests for __all__ exports in modules."""

    def test_errors_all(self) -> None:
        """Test errors module has __all__."""
        from geofabric import errors

        assert hasattr(errors, "__all__")
        assert "GeoFabricError" in errors.__all__
        assert "NetworkError" in errors.__all__
        assert "ValidationError" in errors.__all__

    def test_spatial_all(self) -> None:
        """Test spatial module has __all__."""
        from geofabric import spatial

        assert hasattr(spatial, "__all__")
        assert "BufferOp" in spatial.__all__
        assert "BoundaryOp" in spatial.__all__
        assert "ExplodeOp" in spatial.__all__
        assert "DensifyOp" in spatial.__all__

    def test_query_all(self) -> None:
        """Test query module has __all__."""
        from geofabric import query

        assert hasattr(query, "__all__")
        assert "Query" in query.__all__
        assert "SQLSource" in query.__all__

    def test_util_all(self) -> None:
        """Test util module has __all__."""
        from geofabric import util

        assert hasattr(util, "__all__")
        assert "retry_with_backoff" in util.__all__
        assert "ensure_dir" in util.__all__

    def test_cache_all(self) -> None:
        """Test cache module has __all__."""
        from geofabric import cache

        assert hasattr(cache, "__all__")
        assert "CacheConfig" in cache.__all__
        assert "QueryCache" in cache.__all__

    def test_validation_all(self) -> None:
        """Test validation module has __all__."""
        from geofabric import validation

        assert hasattr(validation, "__all__")
        assert "ValidationResult" in validation.__all__
        assert "DatasetStats" in validation.__all__

    def test_roi_all(self) -> None:
        """Test roi module has __all__."""
        from geofabric import roi

        assert hasattr(roi, "__all__")
        assert "ROI" in roi.__all__
        assert "bbox" in roi.__all__
        assert "wkt" in roi.__all__

    def test_protocols_all(self) -> None:
        """Test protocols module has __all__."""
        from geofabric import protocols

        assert hasattr(protocols, "__all__")
        assert "Source" in protocols.__all__
        assert "Engine" in protocols.__all__
        assert "Sink" in protocols.__all__


class TestCLICommands:
    """Tests for new CLI commands."""

    def test_sample_command_exists(self) -> None:
        """Test sample command function is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "sample")
        assert callable(cli_app.sample)

    def test_stats_command_exists(self) -> None:
        """Test stats command function is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "stats")
        assert callable(cli_app.stats)

    def test_buffer_command_exists(self) -> None:
        """Test buffer command function is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "buffer")
        assert callable(cli_app.buffer)

    def test_simplify_command_exists(self) -> None:
        """Test simplify command function is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "simplify")
        assert callable(cli_app.simplify)

    def test_transform_command_exists(self) -> None:
        """Test transform command function is defined."""
        from geofabric.cli import app as cli_app

        assert hasattr(cli_app, "transform")
        assert callable(cli_app.transform)


class TestExceptionSpecificity:
    """Tests for specific exception handling."""

    def test_to_geopandas_import_error(self) -> None:
        """Test to_geopandas catches ImportError specifically."""
        from geofabric.errors import MissingDependencyError
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"
        q = Query(dataset=mock_dataset)

        # Patch the import to fail
        with patch.dict("sys.modules", {"geopandas": None}):
            with patch("builtins.__import__", side_effect=ImportError("No geopandas")):
                with pytest.raises(MissingDependencyError):
                    q.to_geopandas()

    def test_show_import_error(self) -> None:
        """Test show catches ImportError specifically."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"
        q = Query(dataset=mock_dataset)

        # Patch the import to fail
        with patch.dict("sys.modules", {"lonboard": None}):
            with patch("builtins.__import__", side_effect=ImportError("No lonboard")):
                result = q.show()
                assert result is None


class TestValidUnits:
    """Tests for valid unit handling in BufferOp."""

    def test_meters_conversion(self) -> None:
        """Test meters are passed through unchanged."""
        from geofabric.spatial import BufferOp

        op = BufferOp(distance=100, unit="meters")
        sql = op.to_sql("geom")
        assert "100" in sql

    def test_kilometers_conversion(self) -> None:
        """Test kilometers are converted to meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(distance=1, unit="kilometers")
        sql = op.to_sql("geom")
        assert "1000" in sql

    def test_miles_conversion(self) -> None:
        """Test miles are converted to meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(distance=1, unit="miles")
        sql = op.to_sql("geom")
        assert "1609" in sql

    def test_feet_conversion(self) -> None:
        """Test feet are converted to meters."""
        from geofabric.spatial import BufferOp

        op = BufferOp(distance=100, unit="feet")
        sql = op.to_sql("geom")
        assert "30.48" in sql
