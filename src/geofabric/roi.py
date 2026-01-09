from __future__ import annotations

import math
from dataclasses import dataclass

from geofabric.sql_utils import escape_wkt

__all__ = ["ROI", "bbox", "wkt"]

# Valid SRID range: 1-999999
# Common SRIDs: 4326 (WGS84), 3857 (Web Mercator), 2154 (French Lambert)
# See https://epsg.io/ for reference
_SRID_MIN = 1
_SRID_MAX = 999999


def _validate_srid(srid: int) -> int:
    """Validate SRID is in valid range.

    Args:
        srid: Spatial Reference ID to validate

    Returns:
        The validated SRID

    Raises:
        ValueError: If SRID is out of valid range
    """
    if not (_SRID_MIN <= srid <= _SRID_MAX):
        raise ValueError(
            f"srid must be between {_SRID_MIN} and {_SRID_MAX}, got {srid}"
        )
    return srid


@dataclass(frozen=True)
class ROI:
    kind: str
    wkt: str | None = None
    minx: float | None = None
    miny: float | None = None
    maxx: float | None = None
    maxy: float | None = None
    srid: int = 4326

    def to_duckdb_geometry_sql(self) -> str:
        if self.kind == "bbox":
            if None in (self.minx, self.miny, self.maxx, self.maxy):
                raise ValueError("bbox ROI requires minx, miny, maxx, maxy")
            return f"ST_MakeEnvelope({self.minx}, {self.miny}, {self.maxx}, {self.maxy})"
        if self.kind == "wkt":
            if not self.wkt:
                raise ValueError("wkt ROI requires wkt text")
            escaped = escape_wkt(self.wkt)
            return f"ST_GeomFromText('{escaped}')"
        raise ValueError(f"Unknown ROI kind: {self.kind}")


def bbox(minx: float, miny: float, maxx: float, maxy: float, srid: int = 4326) -> ROI:
    """Create a bounding box ROI.

    Args:
        minx: Minimum X coordinate (west)
        miny: Minimum Y coordinate (south)
        maxx: Maximum X coordinate (east)
        maxy: Maximum Y coordinate (north)
        srid: Spatial reference ID (default: 4326 for WGS84)

    Raises:
        ValueError: If coordinates are invalid (NaN, inf, or inverted bounds)
    """
    # Validate coordinates are finite numbers
    for name, val in [("minx", minx), ("miny", miny), ("maxx", maxx), ("maxy", maxy)]:
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            raise ValueError(f"{name} must be a finite number, got {val}")

    # Validate bounds are not inverted
    if minx > maxx:
        raise ValueError(f"minx ({minx}) must be <= maxx ({maxx})")
    if miny > maxy:
        raise ValueError(f"miny ({miny}) must be <= maxy ({maxy})")

    # Validate SRID is in valid range
    _validate_srid(srid)

    return ROI(kind="bbox", minx=minx, miny=miny, maxx=maxx, maxy=maxy, srid=srid)


def wkt(wkt_text: str, srid: int = 4326) -> ROI:
    """Create a WKT-based ROI.

    Args:
        wkt_text: WKT (Well-Known Text) geometry string
        srid: Spatial reference ID (default: 4326 for WGS84)

    Raises:
        ValueError: If WKT text is empty or SRID is invalid
    """
    if not wkt_text or not wkt_text.strip():
        raise ValueError("wkt_text cannot be empty")

    # Validate SRID is in valid range
    _validate_srid(srid)

    return ROI(kind="wkt", wkt=wkt_text, srid=srid)
