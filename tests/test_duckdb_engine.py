from __future__ import annotations

import tempfile

import pandas as pd
import pytest

from geofabric.engines.duckdb_engine import DuckDBEngine
from geofabric.errors import EngineError
from geofabric.sources.files import FilesSource


class _FakeResult:
    def __init__(self, sql: str):
        self._sql = sql

    def df(self) -> pd.DataFrame:
        return pd.DataFrame({"sql": [self._sql]})

    def arrow(self):
        import pyarrow as pa

        return pa.table({"sql": [self._sql]})


class _FakeConn:
    def __init__(self):
        self.executed: list[str] = []

    def execute(self, sql: str):
        self.executed.append(sql)
        return _FakeResult(sql)


def test_duckdb_engine_relation_sql_parquet(monkeypatch, tmp_path) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    # Create a temp file to test with
    pq_file = tmp_path / "test.parquet"
    pq_file.write_bytes(b"")

    eng = DuckDBEngine()
    source = FilesSource(path=str(pq_file))
    sql = eng.source_to_relation_sql(source)
    assert "read_parquet" in sql


def test_duckdb_engine_relation_sql_dir(monkeypatch) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    with tempfile.TemporaryDirectory() as td:
        eng = DuckDBEngine()
        source = FilesSource(path=td)
        sql = eng.source_to_relation_sql(source)
        assert "read_parquet" in sql
        assert "*.parquet" in sql


def test_duckdb_engine_query_to_df(monkeypatch) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    eng = DuckDBEngine()
    df = eng.query_to_df("SELECT 1 AS x")
    assert isinstance(df, pd.DataFrame)
    assert "sql" in df.columns


def test_duckdb_engine_copy_to_parquet(monkeypatch, tmp_path) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    eng = DuckDBEngine()
    out = tmp_path / "o.parquet"
    eng.copy_to_parquet("SELECT 1", str(out))

    assert any("COPY" in s for s in fake.executed)


def test_duckdb_engine_copy_to_geojson(monkeypatch, tmp_path) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    eng = DuckDBEngine()
    out = tmp_path / "o.geojson"
    eng.copy_to_geojson("SELECT 1", str(out))

    assert any("GDAL" in s for s in fake.executed)


def test_duckdb_engine_unsupported_file_type_raises(monkeypatch, tmp_path) -> None:
    import geofabric.engines.duckdb_engine as mod

    fake = _FakeConn()
    monkeypatch.setattr(mod.duckdb, "connect", lambda database: fake)

    # Create an unknown file type
    unknown_file = tmp_path / "x.unknown"
    unknown_file.write_bytes(b"")

    eng = DuckDBEngine()
    source = FilesSource(path=str(unknown_file))
    with pytest.raises(EngineError):
        eng.source_to_relation_sql(source)
