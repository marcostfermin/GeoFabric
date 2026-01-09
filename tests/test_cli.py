from __future__ import annotations

import os
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq
from typer.testing import CliRunner

from geofabric.cli.app import app

runner = CliRunner()


def test_cli_sql_count() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "t.parquet")

        geoms = [
            bytes.fromhex("010100000000000000000000000000000000000000"),
            bytes.fromhex("0101000000000000000000F03F000000000000F03F"),
        ]
        table = pa.table(
            {"id": pa.array([1, 2], pa.int64()), "geometry": pa.array(geoms, pa.binary())}
        )
        pq.write_table(table, path)

        result = runner.invoke(app, ["sql", path, "SELECT COUNT(*) AS c FROM data"])
        assert result.exit_code == 0
        assert "2" in result.stdout
