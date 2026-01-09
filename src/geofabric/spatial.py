"""Spatial operations for GeoFabric queries."""

from __future__ import annotations

from dataclasses import dataclass

from geofabric.roi import _validate_srid
from geofabric.sql_utils import escape_wkt

from geofabric.query import Query

__all__ = [
    "AreaOp",
    "BoundaryOp",
    "BufferOp",
    "CentroidOp",
    "ConvexHullOp",
    "DensifyOp",
    "DifferenceOp",
    "EnvelopeOp",
    "ExplodeOp",
    "FlipCoordinatesOp",
    "IntersectionOp",
    "LengthOp",
    "MakeValidOp",
    "PointOnSurfaceOp",
    "ReverseOp",
    "SimplifyOp",
    "SpatialOp",
    "SymmetricDifferenceOp",
    "TransformOp",
    "UnionOp",
    "apply_spatial_op",
]


@dataclass(kw_only=True)
class SpatialOp:
    """Base class for spatial operations."""

    geometry_col: str = "geometry"

    def to_sql(self, input_col: str) -> str:
        """Return SQL expression for this operation."""
        raise NotImplementedError


_VALID_UNITS = {"meters", "kilometers", "miles", "feet"}


@dataclass(kw_only=True)
class BufferOp(SpatialOp):
    """Buffer geometries by a distance."""

    distance: float
    unit: str = "meters"

    def __post_init__(self) -> None:
        if self.distance < 0:
            raise ValueError(f"Buffer distance must be non-negative, got {self.distance}")
        if self.unit not in _VALID_UNITS:
            raise ValueError(f"Invalid unit '{self.unit}'. Must be one of: {sorted(_VALID_UNITS)}")

    def to_sql(self, input_col: str) -> str:
        # DuckDB Spatial uses meters for buffer
        distance = self.distance
        if self.unit == "kilometers":
            distance *= 1000
        elif self.unit == "miles":
            distance *= 1609.34
        elif self.unit == "feet":
            distance *= 0.3048
        return f"ST_Buffer({input_col}, {distance})"


@dataclass(kw_only=True)
class SimplifyOp(SpatialOp):
    """Simplify geometries with a tolerance."""

    tolerance: float
    preserve_topology: bool = True

    def __post_init__(self) -> None:
        if self.tolerance < 0:
            raise ValueError(f"Simplify tolerance must be non-negative, got {self.tolerance}")

    def to_sql(self, input_col: str) -> str:
        if self.preserve_topology:
            return f"ST_SimplifyPreserveTopology({input_col}, {self.tolerance})"
        return f"ST_Simplify({input_col}, {self.tolerance})"


@dataclass(kw_only=True)
class CentroidOp(SpatialOp):
    """Compute centroids of geometries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_Centroid({input_col})"


@dataclass(kw_only=True)
class ConvexHullOp(SpatialOp):
    """Compute convex hulls of geometries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_ConvexHull({input_col})"


@dataclass(kw_only=True)
class EnvelopeOp(SpatialOp):
    """Compute bounding boxes of geometries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_Envelope({input_col})"


@dataclass(kw_only=True)
class UnionOp(SpatialOp):
    """Union all geometries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_Union_Agg({input_col})"


@dataclass(kw_only=True)
class MakeValidOp(SpatialOp):
    """Repair invalid geometries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_MakeValid({input_col})"


@dataclass(kw_only=True)
class TransformOp(SpatialOp):
    """Transform geometry to a different CRS.

    Supports all EPSG spatial reference systems (SRID 1-999999).
    Common SRIDs: 4326 (WGS84), 3857 (Web Mercator), 2154 (French Lambert).
    """

    from_srid: int = 4326
    to_srid: int = 4326

    def __post_init__(self) -> None:
        """Validate SRID values are in valid range."""
        _validate_srid(self.from_srid)
        _validate_srid(self.to_srid)

    def to_sql(self, input_col: str) -> str:
        return f"ST_Transform({input_col}, 'EPSG:{self.from_srid}', 'EPSG:{self.to_srid}')"


@dataclass(kw_only=True)
class IntersectionOp(SpatialOp):
    """Compute intersection with another geometry."""

    other_wkt: str

    def to_sql(self, input_col: str) -> str:
        escaped = escape_wkt(self.other_wkt)
        return f"ST_Intersection({input_col}, ST_GeomFromText('{escaped}'))"


@dataclass(kw_only=True)
class DifferenceOp(SpatialOp):
    """Compute difference from another geometry."""

    other_wkt: str

    def to_sql(self, input_col: str) -> str:
        escaped = escape_wkt(self.other_wkt)
        return f"ST_Difference({input_col}, ST_GeomFromText('{escaped}'))"


@dataclass(kw_only=True)
class SymmetricDifferenceOp(SpatialOp):
    """Compute symmetric difference (XOR) with another geometry.

    Returns parts of each geometry that don't overlap with the other.
    """

    other_wkt: str

    def to_sql(self, input_col: str) -> str:
        escaped = escape_wkt(self.other_wkt)
        return f"ST_SymDifference({input_col}, ST_GeomFromText('{escaped}'))"


@dataclass(kw_only=True)
class BoundaryOp(SpatialOp):
    """Extract geometry boundaries."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_Boundary({input_col})"


@dataclass(kw_only=True)
class ExplodeOp(SpatialOp):
    """Explode multi-part geometries into single-part geometries.

    Note: This operation requires UNNEST which changes the number of rows.
    """

    def to_sql(self, input_col: str) -> str:
        # ST_Dump returns a struct with path and geom, we extract just the geometry
        return f"UNNEST(ST_Dump({input_col})).geom"


@dataclass(kw_only=True)
class DensifyOp(SpatialOp):
    """Add intermediate vertices along geometry edges.

    Args:
        max_distance: Maximum distance between vertices (in geometry units)
    """

    max_distance: float

    def __post_init__(self) -> None:
        if self.max_distance <= 0:
            raise ValueError(f"Densify max_distance must be positive, got {self.max_distance}")

    def to_sql(self, input_col: str) -> str:
        return f"ST_Segmentize({input_col}, {self.max_distance})"


@dataclass(kw_only=True)
class AreaOp(SpatialOp):
    """Compute area of geometries.

    Returns area in square units of the geometry's CRS.
    For geographic coordinates (EPSG:4326), consider transforming first.
    """

    def to_sql(self, input_col: str) -> str:
        return f"ST_Area({input_col})"


@dataclass(kw_only=True)
class LengthOp(SpatialOp):
    """Compute length/perimeter of geometries.

    For lines, returns the length.
    For polygons, returns the perimeter.
    Returns length in units of the geometry's CRS.
    """

    def to_sql(self, input_col: str) -> str:
        return f"ST_Length({input_col})"


@dataclass(kw_only=True)
class PointOnSurfaceOp(SpatialOp):
    """Compute a point guaranteed to be on the surface of the geometry.

    Unlike centroid, this point is always inside the geometry.
    """

    def to_sql(self, input_col: str) -> str:
        return f"ST_PointOnSurface({input_col})"


@dataclass(kw_only=True)
class ReverseOp(SpatialOp):
    """Reverse the order of vertices in a geometry."""

    def to_sql(self, input_col: str) -> str:
        return f"ST_Reverse({input_col})"


@dataclass(kw_only=True)
class FlipCoordinatesOp(SpatialOp):
    """Flip X and Y coordinates of a geometry.

    Useful for correcting lat/lon vs lon/lat issues.
    """

    def to_sql(self, input_col: str) -> str:
        return f"ST_FlipCoordinates({input_col})"


def apply_spatial_op(query: Query, op: SpatialOp) -> Query:
    """Apply a spatial operation to a query, transforming the geometry column.

    Handles both WKB_BLOB (from GeoJSON via ST_Read) and GEOMETRY (from
    GeoParquet via read_parquet) types. Converts to GEOMETRY for spatial
    operations, then back to WKB for consistent storage.

    Returns a new Query wrapping the transformed result as a subquery,
    ensuring subsequent operations (like with_area) reference the
    transformed geometry, not the original.
    """
    from geofabric.query import SQLSource
    from geofabric.dataset import Dataset

    # Detect geometry column type by querying the schema
    # DuckDB's binder checks types at parse time, so we need to know
    # the actual type to build appropriate SQL
    inner_sql = query.sql()
    type_sql = f"SELECT typeof({op.geometry_col}) AS geom_type FROM ({inner_sql}) LIMIT 1"
    try:
        type_df = query.dataset.engine.query_to_df(type_sql)
        geom_type = type_df["geom_type"].iloc[0] if len(type_df) > 0 else "GEOMETRY"
    except Exception:
        geom_type = "GEOMETRY"  # Default assumption

    # Build type-specific SQL based on detected geometry type
    if geom_type in ("WKB_BLOB", "BLOB"):
        # Convert WKB to GEOMETRY for spatial operation
        geom_input = f"ST_GeomFromWKB({op.geometry_col})"
    else:
        # Use geometry directly
        geom_input = op.geometry_col

    spatial_sql = op.to_sql(geom_input)
    # Convert output back to WKB for consistent storage
    transformed = f"ST_AsWKB({spatial_sql}) AS {op.geometry_col}"

    # Build the transformed SQL as a subquery
    # This ensures subsequent operations reference the transformed geometry
    new_sql = f"""
    SELECT * EXCLUDE ({op.geometry_col}), {transformed}
    FROM ({inner_sql}) _spatial_op
    """  # nosec B608 - geometry_col validated by caller

    # Wrap in a new Query so subsequent operations reference the transformed result
    new_dataset = Dataset(source=SQLSource(sql=new_sql), engine=query.dataset.engine)
    return Query(dataset=new_dataset)
