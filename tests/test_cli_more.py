from __future__ import annotations

import os
import tempfile

from typer.testing import CliRunner

from geofabric.cli.app import app

runner = CliRunner()


def test_cli_sql_count_against_parquet(write_tiny_parquet_with_wkb_geometry) -> None:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "t.parquet")
        write_tiny_parquet_with_wkb_geometry(path)

        result = runner.invoke(app, ["sql", path, "SELECT COUNT(*) AS c FROM data"])
        assert result.exit_code == 0
        assert "2" in result.stdout
