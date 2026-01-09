from __future__ import annotations

import os
import sys
import tempfile

import pytest

from geofabric.errors import ExternalToolError
from geofabric.util import ensure_dir, run_cmd


def test_ensure_dir_creates_parent() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "a", "b", "c.txt")
        ensure_dir(out)
        assert os.path.isdir(os.path.join(td, "a", "b"))


def test_run_cmd_success() -> None:
    returncode, stdout, stderr = run_cmd([sys.executable, "-c", "print('ok')"])
    assert returncode == 0
    assert "ok" in stdout


def test_run_cmd_failure_raises() -> None:
    with pytest.raises(ExternalToolError):
        run_cmd([sys.executable, "-c", "import sys; sys.exit(2)"])
