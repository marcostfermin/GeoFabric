from __future__ import annotations

import pytest

from geofabric.errors import ExternalToolError, MissingDependencyError
from geofabric.sinks.pmtiles import geoquery_to_pmtiles
from geofabric.sources.files import FilesSource
from geofabric.sources.overture import OvertureSource


class _FakeEngine:
    def __init__(self):
        self.geojson_copies: list[tuple[str, str]] = []

    def copy_to_geojson(self, sql: str, path: str) -> None:
        self.geojson_copies.append((sql, path))
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"type":"FeatureCollection","features":[]}')

    def query_to_df(self, sql: str):
        raise AssertionError("Not used in these tests")

    def query_to_arrow(self, sql: str):
        raise AssertionError("Not used in these tests")

    def source_to_relation_sql(self, source: object) -> str:
        return "read_parquet('x')"

    def copy_to_parquet(self, sql: str, path: str) -> None:
        raise AssertionError("Not used in these tests")


def test_files_source_creation() -> None:
    """Test FilesSource can be instantiated with a path."""
    src = FilesSource(path="/tmp/x.parquet")
    assert src.path == "/tmp/x.parquet"
    assert src.source_kind() == "files"


def test_overture_source_from_uri() -> None:
    """Test OvertureSource.from_uri parses URI correctly."""
    uri = "overture://?release=2025-01-01.0&theme=places&type=place"
    src = OvertureSource.from_uri(uri)
    assert src.release == "2025-01-01.0"
    assert src.theme == "places"
    assert src.type_ == "place"


def test_overture_source_s3_prefix() -> None:
    """Test OvertureSource generates correct S3 prefix."""
    src = OvertureSource(release="2025-01-01.0", theme="places", type_="place")
    prefix = src.s3_prefix()
    assert "s3://overturemaps-us-west-2" in prefix
    assert "release/2025-01-01.0" in prefix
    assert "theme=places" in prefix
    assert "type=place" in prefix


def test_geoquery_to_pmtiles_missing_tippecanoe(monkeypatch, tmp_path) -> None:
    """Test geoquery_to_pmtiles raises when tippecanoe is not installed."""
    import geofabric.sinks.pmtiles as pmtiles_mod

    engine = _FakeEngine()

    # Mock shutil.which to return None (tippecanoe not found)
    monkeypatch.setattr(pmtiles_mod.shutil, "which", lambda x: None)

    with pytest.raises(MissingDependencyError, match="tippecanoe"):
        geoquery_to_pmtiles(
            engine=engine,
            sql="SELECT * FROM data",
            pmtiles_path=str(tmp_path / "out.pmtiles"),
            layer="features",
            maxzoom=14,
            minzoom=0,
        )


def test_geoquery_to_pmtiles_success(monkeypatch, tmp_path) -> None:
    """Test geoquery_to_pmtiles succeeds with mocked tippecanoe."""
    import geofabric.sinks.pmtiles as pmtiles_mod

    ran: list[list[str]] = []

    def _fake_run_cmd(args, **kwargs):
        ran.append(list(args))
        # Create the output file to simulate tippecanoe
        for i, arg in enumerate(args):
            if arg == "-o" and i + 1 < len(args):
                with open(args[i + 1], "wb") as f:
                    f.write(b"PMTiles")
        return (0, "", "")

    # Mock shutil.which to return a path (tippecanoe is installed)
    monkeypatch.setattr(pmtiles_mod.shutil, "which", lambda x: "/usr/bin/tippecanoe")
    monkeypatch.setattr(pmtiles_mod, "run_cmd", _fake_run_cmd)

    engine = _FakeEngine()
    out = tmp_path / "out.pmtiles"
    result = geoquery_to_pmtiles(
        engine=engine,
        sql="SELECT * FROM data",
        pmtiles_path=str(out),
        layer="x",
        maxzoom=2,
        minzoom=1,
    )

    assert engine.geojson_copies
    assert ran
    assert "tippecanoe" in ran[0]
    assert result == str(out.resolve())
