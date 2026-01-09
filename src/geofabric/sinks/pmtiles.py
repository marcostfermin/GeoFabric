from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from geofabric.engines.duckdb_engine import DuckDBEngine
from geofabric.errors import MissingDependencyError, ValidationError
from geofabric.util import ensure_dir, run_cmd

__all__ = ["PMTilesSink", "PMTilesSinkFactory", "geoquery_to_pmtiles"]

# Valid zoom levels for tippecanoe (web map tiles)
_MIN_ZOOM_LEVEL = 0
_MAX_ZOOM_LEVEL = 28

# Layer name pattern: alphanumeric, underscore, hyphen (no spaces or special chars)
_LAYER_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


def _validate_zoom_levels(minzoom: int, maxzoom: int) -> None:
    """Validate zoom levels are in valid range and properly ordered.

    Args:
        minzoom: Minimum zoom level
        maxzoom: Maximum zoom level

    Raises:
        ValidationError: If zoom levels are invalid
    """
    if not (_MIN_ZOOM_LEVEL <= minzoom <= _MAX_ZOOM_LEVEL):
        raise ValidationError(
            f"minzoom must be between {_MIN_ZOOM_LEVEL} and {_MAX_ZOOM_LEVEL}, got {minzoom}"
        )
    if not (_MIN_ZOOM_LEVEL <= maxzoom <= _MAX_ZOOM_LEVEL):
        raise ValidationError(
            f"maxzoom must be between {_MIN_ZOOM_LEVEL} and {_MAX_ZOOM_LEVEL}, got {maxzoom}"
        )
    if minzoom > maxzoom:
        raise ValidationError(
            f"minzoom ({minzoom}) cannot be greater than maxzoom ({maxzoom})"
        )


def _validate_layer_name(layer: str) -> str:
    """Validate layer name is a valid identifier.

    Args:
        layer: Layer name to validate

    Returns:
        The validated layer name

    Raises:
        ValidationError: If layer name is invalid
    """
    if not layer:
        raise ValidationError("Layer name cannot be empty")
    if not _LAYER_NAME_PATTERN.match(layer):
        raise ValidationError(
            f"Layer name '{layer}' is invalid. "
            "Must start with letter or underscore, "
            "contain only alphanumeric, underscore, or hyphen characters."
        )
    return layer


def geoquery_to_pmtiles(
    *,
    engine: DuckDBEngine,
    sql: str,
    pmtiles_path: str,
    layer: str,
    maxzoom: int,
    minzoom: int,
    geometry_col: str = "geometry",  # noqa: ARG001 - reserved for future use
) -> str:
    """Create PMTiles from a query result.

    Uses DuckDB to export GeoJSON, then tippecanoe to generate PMTiles.

    Args:
        engine: DuckDB engine for query execution
        sql: SQL query to execute
        pmtiles_path: Output path for PMTiles file
        layer: Layer name in the tileset
        maxzoom: Maximum zoom level (0-28)
        minzoom: Minimum zoom level (0-28, must be <= maxzoom)
        geometry_col: Name of geometry column (currently unused - DuckDB
            auto-detects geometry columns during GeoJSON export)

    Returns:
        Path to the generated PMTiles file

    Raises:
        MissingDependencyError: If tippecanoe is not installed
        ValidationError: If zoom levels or layer name are invalid
    """
    # Validate inputs before doing any work
    _validate_zoom_levels(minzoom, maxzoom)
    _validate_layer_name(layer)

    # Check for tippecanoe before doing any work
    if shutil.which("tippecanoe") is None:
        raise MissingDependencyError(
            "tippecanoe is required for PMTiles export but was not found in PATH. "
            "Install from: https://github.com/felt/tippecanoe"
        )

    out_pmtiles = str(Path(pmtiles_path).expanduser().resolve())
    ensure_dir(str(Path(out_pmtiles).parent))

    with tempfile.TemporaryDirectory() as td:
        geojson_path = str(Path(td) / f"{layer}.geojson")
        engine.copy_to_geojson(sql, geojson_path)

        args = [
            "tippecanoe",
            "-o",
            out_pmtiles,
            "-l",
            layer,
            f"--maximum-zoom={int(maxzoom)}",
            f"--minimum-zoom={int(minzoom)}",
            "--projection=EPSG:4326",
            geojson_path,
        ]
        run_cmd(args, check=True)

    return out_pmtiles


class PMTilesSink:
    """Sink for writing data to PMTiles format."""

    def sink_kind(self) -> str:
        return "pmtiles"

    def write(
        self, *, engine: DuckDBEngine, sql: str, out_path: str, options: dict[str, Any]
    ) -> str:
        layer = str(options.get("layer", "features"))
        maxzoom = int(options.get("maxzoom", 14))
        minzoom = int(options.get("minzoom", 0))
        geometry_col = str(options.get("geometry_col", "geometry"))

        return geoquery_to_pmtiles(
            engine=engine,
            sql=sql,
            pmtiles_path=out_path,
            layer=layer,
            maxzoom=maxzoom,
            minzoom=minzoom,
            geometry_col=geometry_col,
        )


from geofabric.registry import SinkClassFactory

# Use generic factory instead of boilerplate class
PMTilesSinkFactory = SinkClassFactory(PMTilesSink)
