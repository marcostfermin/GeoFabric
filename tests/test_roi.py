from __future__ import annotations

import pytest

from geofabric import roi
from geofabric.roi import ROI


def test_roi_bbox_to_sql() -> None:
    bbox_roi = roi.bbox(minx=0.0, miny=1.0, maxx=2.0, maxy=3.0)

    assert bbox_roi.kind == "bbox"
    assert bbox_roi.minx == 0.0
    assert bbox_roi.miny == 1.0
    assert bbox_roi.maxx == 2.0
    assert bbox_roi.maxy == 3.0

    sql = bbox_roi.to_duckdb_geometry_sql()
    assert "ST_MakeEnvelope" in sql
    assert "0.0" in sql
    assert "1.0" in sql
    assert "2.0" in sql
    assert "3.0" in sql


def test_roi_wkt_to_sql() -> None:
    wkt_roi = roi.wkt("POINT (0 0)")
    assert wkt_roi.kind == "wkt"
    sql = wkt_roi.to_duckdb_geometry_sql()
    assert "ST_GeomFromText" in sql
    assert "POINT (0 0)" in sql


def test_roi_invalid_kind_raises() -> None:
    invalid_roi = ROI(kind="nope")
    with pytest.raises(ValueError):
        invalid_roi.to_duckdb_geometry_sql()
