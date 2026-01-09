from __future__ import annotations

import sys
from types import ModuleType

import pandas as pd
import pytest

from geofabric import roi
from geofabric.dataset import Dataset
from geofabric.errors import MissingDependencyError
from geofabric.query import Query
from geofabric.sources.files import FilesSource


class FakeEngine:
    def __init__(self):
        self.copied_to_parquet: list[tuple[str, str]] = []
        self.copied_to_geojson: list[tuple[str, str]] = []

    def source_to_relation_sql(self, source: object) -> str:
        if isinstance(source, FilesSource):
            return f"read_parquet('{source.path}')"
        return "read_parquet('/tmp/fake.parquet')"

    def query_to_df(self, sql: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "id": [1, 2],
                "geometry": [
                    bytes.fromhex("010100000000000000000000000000000000000000"),
                    bytes.fromhex("0101000000000000000000F03F000000000000F03F"),
                ],
            }
        )

    def query_to_arrow(self, sql: str):
        return {"sql": sql}

    def copy_to_parquet(self, sql: str, path: str) -> None:
        self.copied_to_parquet.append((sql, path))

    def copy_to_geojson(self, sql: str, path: str) -> None:
        self.copied_to_geojson.append((sql, path))


class FakeSource:
    path = "/tmp/fake.parquet"

    def source_kind(self) -> str:
        return "fake"


def test_query_sql_building() -> None:
    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = ds.select(["id"]).where("id > 1").limit(1)

    sql = q.sql()
    assert "SELECT id" in sql
    assert "WHERE (id > 1)" in sql
    assert "LIMIT 1" in sql


def test_query_within_roi() -> None:
    """Test Query.within() with ROI objects."""
    ds = Dataset(source=FakeSource(), engine=FakeEngine())

    # Test with bbox ROI
    bbox_roi = roi.bbox(0.0, 0.0, 1.0, 1.0)
    q = Query(dataset=ds).within(bbox_roi)

    sql = q.sql()
    assert "ST_Intersects" in sql
    assert "ST_MakeEnvelope" in sql

    # Test with WKT ROI
    wkt_roi = roi.wkt("POINT (0 0)")
    q2 = Query(dataset=ds).within(wkt_roi)

    sql2 = q2.sql()
    assert "ST_Intersects" in sql2
    assert "ST_GeomFromText" in sql2


def test_to_geopandas_missing_dependency(monkeypatch) -> None:
    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = Query(dataset=ds).select(["id", "geometry"])

    monkeypatch.setitem(sys.modules, "geopandas", None)

    with pytest.raises(MissingDependencyError):
        q.to_geopandas()


def test_to_geopandas_success_with_fake_geopandas(monkeypatch) -> None:
    class _FakeGeoDataFrame(pd.DataFrame):
        def __init__(self, df, geometry, crs: str):
            super().__init__(df)
            self._geometry_col = geometry
            self._crs = crs
            # Store geometry as a column for assertion
            self["geometry"] = geometry

        def to_parquet(self, path: str, index: bool = True) -> None:
            self._wrote_to = path  # type: ignore[attr-defined]

    fake_gpd = ModuleType("geopandas")
    fake_gpd.GeoDataFrame = _FakeGeoDataFrame  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "geopandas", fake_gpd)

    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = Query(dataset=ds).select(["id", "geometry"])

    gdf = q.to_geopandas()
    assert isinstance(gdf, pd.DataFrame)
    assert "geometry" in gdf.columns


def test_to_parquet_falls_back_to_engine(monkeypatch, tmp_path) -> None:
    monkeypatch.setitem(sys.modules, "geopandas", None)

    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = Query(dataset=ds).select(["id", "geometry"])

    out = tmp_path / "out.parquet"
    q.to_parquet(str(out))

    assert ds.engine.copied_to_parquet
    assert ds.engine.copied_to_parquet[0][1] == str(out)


def test_show_missing_dependency(monkeypatch, capsys) -> None:
    monkeypatch.setitem(sys.modules, "lonboard", None)

    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = Query(dataset=ds).select(["id", "geometry"])

    res = q.show()
    assert res is None

    captured = capsys.readouterr()
    assert "lonboard" in captured.out.lower()


def test_show_success_with_fake_lonboard(monkeypatch) -> None:
    """Test show() with a fake lonboard.viz function."""

    class _FakeVizResult:
        def __init__(self, gdf):
            self.gdf = gdf

    def _fake_viz(gdf):
        return _FakeVizResult(gdf)

    fake_lonboard = ModuleType("lonboard")
    fake_lonboard.viz = _fake_viz  # type: ignore[attr-defined]

    # Also need fake geopandas for to_geopandas() call
    class _FakeGeoDataFrame(pd.DataFrame):
        def __init__(self, df, geometry, crs: str):
            super().__init__(df)
            self["geometry"] = geometry

    fake_gpd = ModuleType("geopandas")
    fake_gpd.GeoDataFrame = _FakeGeoDataFrame  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "lonboard", fake_lonboard)
    monkeypatch.setitem(sys.modules, "geopandas", fake_gpd)

    ds = Dataset(source=FakeSource(), engine=FakeEngine())
    q = Query(dataset=ds).select(["id", "geometry"])

    m = q.show()
    assert m is not None
    assert hasattr(m, "gdf")
