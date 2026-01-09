"""Extended tests for ROI module."""

from __future__ import annotations

import pytest

from geofabric.roi import ROI, bbox, wkt


class TestROIDataclass:
    """Tests for ROI dataclass."""

    def test_roi_bbox_kind(self) -> None:
        """Test ROI with bbox kind."""
        roi = ROI(
            kind="bbox",
            minx=-122.0,
            miny=37.0,
            maxx=-121.0,
            maxy=38.0,
        )
        assert roi.kind == "bbox"
        assert roi.srid == 4326

    def test_roi_wkt_kind(self) -> None:
        """Test ROI with wkt kind."""
        roi = ROI(
            kind="wkt",
            wkt="POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))",
        )
        assert roi.kind == "wkt"
        assert roi.wkt is not None

    def test_roi_custom_srid(self) -> None:
        """Test ROI with custom SRID."""
        roi = bbox(-122, 37, -121, 38, srid=3857)
        assert roi.srid == 3857


class TestROIToDuckDBGeometry:
    """Tests for ROI.to_duckdb_geometry_sql method."""

    def test_bbox_to_duckdb_geometry_sql(self) -> None:
        """Test bbox ROI to DuckDB SQL."""
        roi = bbox(-122.5, 37.5, -122.0, 38.0)
        sql = roi.to_duckdb_geometry_sql()

        assert "ST_MakeEnvelope" in sql
        assert "-122.5" in sql
        assert "37.5" in sql
        assert "-122.0" in sql
        assert "38.0" in sql

    def test_wkt_to_duckdb_geometry_sql(self) -> None:
        """Test wkt ROI to DuckDB SQL."""
        roi = wkt("POLYGON((-122 37, -121 37, -121 38, -122 38, -122 37))")
        sql = roi.to_duckdb_geometry_sql()

        assert "ST_GeomFromText" in sql
        assert "POLYGON" in sql

    def test_bbox_missing_coords_raises(self) -> None:
        """Test bbox ROI with missing coords raises ValueError."""
        roi = ROI(kind="bbox", minx=-122.0)  # Missing other coords
        with pytest.raises(ValueError, match="bbox ROI requires"):
            roi.to_duckdb_geometry_sql()

    def test_wkt_missing_text_raises(self) -> None:
        """Test wkt ROI with missing text raises ValueError."""
        roi = ROI(kind="wkt")  # Missing wkt text
        with pytest.raises(ValueError, match="wkt ROI requires wkt text"):
            roi.to_duckdb_geometry_sql()

    def test_unknown_kind_raises(self) -> None:
        """Test unknown ROI kind raises ValueError."""
        roi = ROI(kind="unknown")
        with pytest.raises(ValueError, match="Unknown ROI kind"):
            roi.to_duckdb_geometry_sql()


class TestROIFactoryFunctions:
    """Tests for bbox and wkt factory functions."""

    def test_bbox_factory(self) -> None:
        """Test bbox factory function."""
        roi = bbox(-122.5, 37.5, -122.0, 38.0)

        assert roi.kind == "bbox"
        assert roi.minx == -122.5
        assert roi.miny == 37.5
        assert roi.maxx == -122.0
        assert roi.maxy == 38.0

    def test_wkt_factory(self) -> None:
        """Test wkt factory function."""
        wkt_text = "POINT(-122 37)"
        roi = wkt(wkt_text)

        assert roi.kind == "wkt"
        assert roi.wkt == wkt_text

    def test_bbox_with_custom_srid(self) -> None:
        """Test bbox with custom SRID."""
        roi = bbox(-122, 37, -121, 38, srid=32610)
        assert roi.srid == 32610

    def test_wkt_with_custom_srid(self) -> None:
        """Test wkt with custom SRID."""
        roi = wkt("POINT(0 0)", srid=32610)
        assert roi.srid == 32610
