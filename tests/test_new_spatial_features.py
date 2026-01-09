"""Tests for new spatial features: joins, CRS transform, make_valid, clip, erase."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestSpatialOps:
    """Tests for new spatial operations."""

    def test_make_valid_op(self) -> None:
        """Test MakeValidOp generates correct SQL."""
        from geofabric.spatial import MakeValidOp

        op = MakeValidOp(geometry_col="geometry")
        sql = op.to_sql("geometry")
        assert "ST_MakeValid" in sql
        assert "geometry" in sql

    def test_transform_op(self) -> None:
        """Test TransformOp generates correct SQL."""
        from geofabric.spatial import TransformOp

        op = TransformOp(geometry_col="geometry", from_srid=4326, to_srid=3857)
        sql = op.to_sql("geometry")
        assert "ST_Transform" in sql
        assert "EPSG:4326" in sql
        assert "EPSG:3857" in sql

    def test_intersection_op(self) -> None:
        """Test IntersectionOp generates correct SQL."""
        from geofabric.spatial import IntersectionOp

        op = IntersectionOp(geometry_col="geometry", other_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        sql = op.to_sql("geometry")
        assert "ST_Intersection" in sql
        assert "ST_GeomFromText" in sql
        assert "POLYGON" in sql

    def test_difference_op(self) -> None:
        """Test DifferenceOp generates correct SQL."""
        from geofabric.spatial import DifferenceOp

        op = DifferenceOp(geometry_col="geometry", other_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        sql = op.to_sql("geometry")
        assert "ST_Difference" in sql


class TestQueryMakeValid:
    """Tests for Query.make_valid method."""

    def test_make_valid(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.make_valid method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.make_valid()
        assert result is not None
        assert "ST_MakeValid" in result.sql()


class TestQueryTransform:
    """Tests for Query.transform method."""

    def test_transform_default_from_srid(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.transform with default from_srid."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.transform(to_srid=3857)
        assert result is not None
        sql = result.sql()
        assert "ST_Transform" in sql
        assert "EPSG:4326" in sql  # default from_srid
        assert "EPSG:3857" in sql

    def test_transform_custom_from_srid(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.transform with custom from_srid."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        result = q.transform(to_srid=32610, from_srid=4269)
        sql = result.sql()
        assert "EPSG:4269" in sql
        assert "EPSG:32610" in sql


class TestQueryClipErase:
    """Tests for Query.clip and Query.erase methods."""

    def test_clip(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.clip method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        wkt = "POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))"
        result = q.clip(wkt)
        sql = result.sql()
        assert "ST_Intersection" in sql

    def test_erase(self, mock_dataset_for_spatial: MagicMock) -> None:
        """Test Query.erase method."""
        from geofabric.query import Query

        q = Query(dataset=mock_dataset_for_spatial)

        wkt = "POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))"
        result = q.erase(wkt)
        sql = result.sql()
        assert "ST_Difference" in sql


class TestSpatialJoin:
    """Tests for Query.sjoin method."""

    def _mock_engine(self) -> MagicMock:
        """Create a mock engine that handles SQLSource."""
        from geofabric.query import SQLSource

        mock_engine = MagicMock()

        def source_to_relation_sql(source: object) -> str:
            if isinstance(source, SQLSource):
                return f"({source.sql})"
            return "test_table"

        mock_engine.source_to_relation_sql.side_effect = source_to_relation_sql
        return mock_engine

    def test_sjoin_intersects(self) -> None:
        """Test spatial join with intersects predicate."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="intersects")
        sql = result.sql()
        assert "ST_Intersects" in sql
        assert "JOIN" in sql

    def test_sjoin_within(self) -> None:
        """Test spatial join with within predicate."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="within")
        sql = result.sql()
        assert "ST_Within" in sql

    def test_sjoin_contains(self) -> None:
        """Test spatial join with contains predicate."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="contains")
        sql = result.sql()
        assert "ST_Contains" in sql

    def test_sjoin_left_join(self) -> None:
        """Test spatial join with left join."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.sjoin(q2, predicate="intersects", how="left")
        sql = result.sql()
        assert "LEFT JOIN" in sql

    def test_sjoin_invalid_predicate(self) -> None:
        """Test spatial join with invalid predicate raises ValueError."""
        from geofabric.query import Query

        mock_dataset = MagicMock()
        mock_dataset.engine.source_to_relation_sql.return_value = "test_table"

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        with pytest.raises(ValueError, match="Unknown predicate"):
            q1.sjoin(q2, predicate="invalid")


class TestNearestJoin:
    """Tests for Query.nearest method."""

    def _mock_engine(self) -> MagicMock:
        """Create a mock engine that handles SQLSource."""
        from geofabric.query import SQLSource

        mock_engine = MagicMock()

        def source_to_relation_sql(source: object) -> str:
            if isinstance(source, SQLSource):
                return f"({source.sql})"
            return "test_table"

        mock_engine.source_to_relation_sql.side_effect = source_to_relation_sql
        return mock_engine

    def test_nearest_basic(self) -> None:
        """Test nearest neighbor join."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.nearest(q2, k=3)
        sql = result.sql()
        assert "ST_Distance" in sql
        assert "ORDER BY" in sql
        assert "LIMIT 3" in sql

    def test_nearest_with_max_distance(self) -> None:
        """Test nearest neighbor join with max distance filter."""
        from geofabric.query import Query

        mock_engine = self._mock_engine()
        mock_dataset = MagicMock()
        mock_dataset.engine = mock_engine

        q1 = Query(dataset=mock_dataset)
        q2 = Query(dataset=mock_dataset)

        result = q1.nearest(q2, k=1, max_distance=1000.0)
        sql = result.sql()
        assert "ST_Distance" in sql
        assert "<= 1000.0" in sql


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_retry_success_first_attempt(self) -> None:
        """Test function succeeds on first attempt."""
        from geofabric.util import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """Test function succeeds after some failures."""
        from geofabric.util import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self) -> None:
        """Test function raises after exhausting retries."""
        from geofabric.util import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fail()
        assert call_count == 3  # Initial + 2 retries

    def test_retry_specific_exceptions(self) -> None:
        """Test retry only catches specified exceptions."""
        from geofabric.util import retry_with_backoff

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        def raise_type_error() -> str:
            raise TypeError("Not retryable")

        # TypeError should not be caught
        with pytest.raises(TypeError):
            raise_type_error()


class TestNewErrorTypes:
    """Tests for new error types."""

    def test_network_error(self) -> None:
        """Test NetworkError can be raised."""
        from geofabric.errors import NetworkError

        with pytest.raises(NetworkError):
            raise NetworkError("Connection failed")

    def test_validation_error(self) -> None:
        """Test ValidationError can be raised."""
        from geofabric.errors import ValidationError

        with pytest.raises(ValidationError):
            raise ValidationError("Invalid data")

    def test_geometry_error(self) -> None:
        """Test GeometryError can be raised."""
        from geofabric.errors import GeometryError

        with pytest.raises(GeometryError):
            raise GeometryError("Invalid geometry")

    def test_source_error(self) -> None:
        """Test SourceError can be raised."""
        from geofabric.errors import SourceError

        with pytest.raises(SourceError):
            raise SourceError("Source operation failed")
