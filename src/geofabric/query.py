from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd
from shapely import wkb as shapely_wkb

from geofabric.errors import MissingDependencyError
from geofabric.roi import ROI
from geofabric.sql_utils import escape_wkt, validate_sql_identifier

if TYPE_CHECKING:
    import pyarrow as pa
    from geofabric.spatial import SpatialOp

__all__ = ["Query", "SQLSource"]


def _validate_geometry_col(geometry_col: str) -> str:
    """Validate geometry column name to prevent SQL injection.

    Args:
        geometry_col: Column name to validate

    Returns:
        The validated column name

    Raises:
        ValueError: If column name is invalid
    """
    return validate_sql_identifier(geometry_col, "geometry column")


def _validate_column_name(column_name: str, field: str = "column") -> str:
    """Validate output column name to prevent SQL injection.

    Args:
        column_name: Column name to validate
        field: Description for error messages

    Returns:
        The validated column name

    Raises:
        ValueError: If column name is invalid
    """
    return validate_sql_identifier(column_name, field)


@dataclass
class Query:
    dataset: Any
    _select: list[str] = field(default_factory=lambda: ["*"])
    _where: list[str] = field(default_factory=list)
    _limit: int | None = None

    def select(self, columns: str | Sequence[str]) -> Query:
        q = self._clone()
        q._select = [columns] if isinstance(columns, str) else list(columns)
        return q

    def where(self, sql_predicate: str) -> Query:
        """Add a WHERE clause predicate to the query.

        Warning:
            This method accepts raw SQL predicates. DO NOT pass untrusted
            user input directly to this method as it may enable SQL injection.

            For user-provided values, use parameterized approaches or validate
            inputs before passing to this method.

        Args:
            sql_predicate: SQL predicate expression (e.g., "name = 'foo'")

        Returns:
            New Query with the predicate added

        Raises:
            ValueError: If predicate contains obvious injection patterns

        Example:
            Safe usage (hardcoded or validated):
                query.where("status = 'active'")
                query.where(f"category = '{validated_category}'")

            Unsafe - DO NOT DO THIS:
                query.where(user_input)  # SQL injection risk!
        """
        if not sql_predicate or not sql_predicate.strip():
            raise ValueError("sql_predicate must not be empty")

        # Basic sanitization to catch obvious SQL injection attempts
        # Note: This is NOT a complete defense - never pass untrusted input!
        predicate_lower = sql_predicate.lower()

        # Reject statements that could modify data or execute multiple queries
        dangerous_patterns = [
            ";",          # Multiple statements
            "--",         # SQL comments
            "/*",         # Block comments
            "drop ",      # DROP statements
            "delete ",    # DELETE statements
            "insert ",    # INSERT statements
            "update ",    # UPDATE statements
            "create ",    # CREATE statements
            "alter ",     # ALTER statements
            "truncate ",  # TRUNCATE statements
            "grant ",     # GRANT statements
            "revoke ",    # REVOKE statements
            "exec ",      # EXEC statements
            "execute ",   # EXECUTE statements
        ]

        for pattern in dangerous_patterns:
            if pattern in predicate_lower:
                raise ValueError(
                    f"SQL predicate contains potentially dangerous pattern: '{pattern.strip()}'. "
                    "WHERE predicates should only contain filter conditions."
                )

        q = self._clone()
        q._where.append(f"({sql_predicate})")
        return q

    def within(self, roi: ROI, geometry_col: str = "geometry") -> Query:
        _validate_geometry_col(geometry_col)
        geom_sql = roi.to_duckdb_geometry_sql()

        # Detect geometry column type by querying the schema
        # DuckDB's binder checks types at parse time, so we need to know
        # the actual type to build appropriate SQL
        inner_sql = self.sql()
        type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({inner_sql}) LIMIT 1"
        try:
            type_df = self.dataset.engine.query_to_df(type_sql)
            geom_type = type_df["geom_type"].iloc[0] if len(type_df) > 0 else "GEOMETRY"
        except Exception:
            geom_type = "GEOMETRY"  # Default assumption

        # Build type-specific SQL based on detected geometry type
        if geom_type in ("WKB_BLOB", "BLOB"):
            # Convert WKB to GEOMETRY for spatial predicate
            geom_expr = f"ST_GeomFromWKB({geometry_col})"
        else:
            # Use geometry directly
            geom_expr = geometry_col

        q = self._clone()
        q._where.append(f"ST_Intersects({geom_expr}, {geom_sql})")
        return q

    def limit(self, n: int) -> Query:
        """Limit query results to n rows.

        Args:
            n: Maximum number of rows to return (must be positive)

        Raises:
            ValueError: If n is not positive
        """
        if n <= 0:
            raise ValueError(f"limit must be positive, got {n}")
        q = self._clone()
        q._limit = int(n)
        return q

    def sql(self) -> str:
        engine = self.dataset.engine
        table_expr = engine.source_to_relation_sql(self.dataset.source)

        select_sql = ", ".join(self._select) if self._select else "*"
        where_sql = " WHERE " + " AND ".join(self._where) if self._where else ""
        limit_sql = f" LIMIT {self._limit}" if self._limit is not None else ""
        return f"SELECT {select_sql} FROM {table_expr}{where_sql}{limit_sql}"  # nosec B608

    def to_arrow(self) -> pa.Table:
        return self.dataset.engine.query_to_arrow(self.sql())

    def to_pandas(self) -> pd.DataFrame:
        return self.dataset.engine.query_to_df(self.sql())

    def to_geopandas(self, geometry_col: str = "geometry") -> Any:
        try:
            import geopandas as gpd
        except ImportError as e:
            raise MissingDependencyError(
                "geopandas is required. Install with: pip install -e '.[viz]'"
            ) from e

        df = self.to_pandas()
        if geometry_col not in df.columns:
            raise ValueError(
                f"Expected geometry column '{geometry_col}' in result. Columns: {list(df.columns)}"
            )

        # Convert geometry bytes to shapely geometries
        # Note: DuckDB may return bytearray instead of bytes, which shapely doesn't accept
        def load_wkb(g: bytes | bytearray | None) -> Any:
            if g is None:
                return None
            # Convert bytearray to bytes if needed (shapely only accepts bytes/str)
            return shapely_wkb.loads(bytes(g) if isinstance(g, bytearray) else g)

        geoms = [load_wkb(g) for g in df[geometry_col].tolist()]
        df = df.drop(columns=[geometry_col])
        return gpd.GeoDataFrame(df, geometry=geoms, crs="EPSG:4326")

    def to_parquet(self, path: str, geometry_col: str = "geometry") -> str:
        # Prefer GeoParquet metadata if geopandas is available
        try:
            gdf = self.to_geopandas(geometry_col=geometry_col)
            gdf.to_parquet(path, index=False)
            return path
        except (MissingDependencyError, ImportError):
            # Fall back to DuckDB parquet writer if geopandas is not available
            self.dataset.engine.copy_to_parquet(self.sql(), path)
            return path

    def to_geojson(self, path: str) -> str:
        self.dataset.engine.copy_to_geojson(self.sql(), path)
        return path

    def to_pmtiles(
        self,
        pmtiles_path: str,
        *,
        layer: str = "features",
        maxzoom: int = 14,
        minzoom: int = 0,
        geometry_col: str = "geometry",
    ) -> str:
        # Validate zoom levels
        if minzoom < 0:
            raise ValueError(f"minzoom must be non-negative, got {minzoom}")
        if maxzoom < 0:
            raise ValueError(f"maxzoom must be non-negative, got {maxzoom}")
        if minzoom > maxzoom:
            raise ValueError(f"minzoom ({minzoom}) must be <= maxzoom ({maxzoom})")

        from geofabric.sinks.pmtiles import geoquery_to_pmtiles

        geoquery_to_pmtiles(
            engine=self.dataset.engine,
            sql=self.sql(),
            pmtiles_path=pmtiles_path,
            layer=layer,
            maxzoom=maxzoom,
            minzoom=minzoom,
            geometry_col=geometry_col,
        )
        return pmtiles_path

    def show(self, geometry_col: str = "geometry") -> Any:
        """Display the query results interactively using lonboard.

        Requires the viz extra: pip install geofabric[viz]
        """
        try:
            from lonboard import viz  # type: ignore
        except ImportError:
            sys.stdout.write("lonboard not installed. Install with: pip install geofabric[viz]\n")
            return None
        gdf = self.to_geopandas(geometry_col=geometry_col)
        return viz(gdf)

    def aggregate(self, agg: dict[str, str]) -> pd.DataFrame:
        """Aggregate query results with optional grouping.

        Args:
            agg: Aggregation options dict. Supported keys:
                - 'by': Column name to group by (optional)

        Returns:
            DataFrame with aggregated results (group_key, count columns)

        Raises:
            ValueError: If unknown keys are provided or column name is invalid
        """
        # Validate only expected keys are provided
        allowed_keys = {"by"}
        unknown_keys = set(agg.keys()) - allowed_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown aggregation keys: {sorted(unknown_keys)}. "
                f"Allowed keys: {sorted(allowed_keys)}"
            )

        by = agg.get("by")
        if by:
            # Validate column name to prevent SQL injection
            validate_sql_identifier(by, "column")
            sql = f"SELECT {by} AS group_key, COUNT(*) AS count FROM ({self.sql()}) t GROUP BY {by}"  # nosec B608
        else:
            sql = f"SELECT COUNT(*) AS count FROM ({self.sql()}) t"  # nosec B608
        return self.dataset.engine.query_to_df(sql)

    def _clone(self) -> Query:
        return Query(
            dataset=self.dataset,
            _select=list(self._select),
            _where=list(self._where),
            _limit=self._limit,
        )

    def _geom_expr(self, geometry_col: str = "geometry") -> str:
        """Get the appropriate geometry expression based on column type.

        Detects whether the geometry column is WKB_BLOB/BLOB (needs ST_GeomFromWKB)
        or already a native GEOMETRY type (use directly).

        Args:
            geometry_col: Name of the geometry column

        Returns:
            SQL expression that yields a GEOMETRY type
        """
        inner_sql = self.sql()
        type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({inner_sql}) LIMIT 1"
        try:
            type_df = self.dataset.engine.query_to_df(type_sql)
            geom_type = type_df["geom_type"].iloc[0] if len(type_df) > 0 else "GEOMETRY"
        except Exception:
            geom_type = "GEOMETRY"  # Default assumption

        if geom_type in ("WKB_BLOB", "BLOB"):
            return f"ST_GeomFromWKB({geometry_col})"
        return geometry_col

    def _with_computed_column(
        self,
        expr: str,
        *,
        replace_star: bool = True,
    ) -> Query:
        """Helper to add a computed column expression to the query.

        This is the foundation for all with_* methods, eliminating code duplication.

        Args:
            expr: The SQL expression to add (should include AS clause)
            replace_star: If True and select is exactly ["*"], sets to ["*", expr];
                          otherwise appends expr to existing select

        Returns:
            A cloned query with the expression added to select
        """
        q = self._clone()
        if replace_star and q._select == ["*"]:
            q._select = ["*", expr]
        else:
            q._select.append(expr)
        return q

    def _with_computed_columns(
        self,
        exprs: list[str],
    ) -> Query:
        """Helper to add multiple computed column expressions to the query.

        Args:
            exprs: List of SQL expressions to add (should include AS clauses)

        Returns:
            A cloned query with the expressions added to select
        """
        q = self._clone()
        if "*" in q._select:
            q._select = ["*"] + exprs
        else:
            q._select.extend(exprs)
        return q

    def _apply_spatial_op(
        self,
        op_class: type[SpatialOp],
        geometry_col: str = "geometry",
        **kwargs: Any,
    ) -> Query:
        """Template Method for applying spatial operations.

        This eliminates code duplication across all spatial operation methods.
        Validates geometry_col and applies the operation.

        Design Pattern: Template Method
        - Defines the algorithm skeleton (validate, create op, apply)
        - Subclasses (spatial ops) provide specific implementations

        Args:
            op_class: The spatial operation class to instantiate
            geometry_col: Name of geometry column (validated)
            **kwargs: Additional arguments for the operation class

        Returns:
            A new Query with the spatial operation applied
        """
        from geofabric.spatial import apply_spatial_op

        _validate_geometry_col(geometry_col)
        op = op_class(geometry_col=geometry_col, **kwargs)
        return apply_spatial_op(self, op)

    # Quick win methods
    def head(self, n: int = 10) -> pd.DataFrame:
        """Return the first n rows as a DataFrame."""
        return self.limit(n).to_pandas()

    def tail(self, n: int = 10) -> pd.DataFrame:
        """Return the last n rows as a DataFrame.

        Args:
            n: Number of rows to return (must be positive)

        Raises:
            ValueError: If n is not positive
        """
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        # Get total count and offset to last n rows
        total = self.count()
        if total <= n:
            return self.to_pandas()
        offset = total - n
        tail_sql = f"""
        SELECT * FROM ({self.sql()}) _tail
        LIMIT {n} OFFSET {offset}
        """  # nosec B608 - n and offset are validated integers
        return self.dataset.engine.query_to_df(tail_sql)

    def sample(self, n: int = 10, seed: int | None = None) -> pd.DataFrame:
        """Return a random sample of n rows.

        Args:
            n: Number of rows to sample (must be positive)
            seed: Optional random seed for reproducibility

        Raises:
            ValueError: If n is not positive
        """
        if n <= 0:
            raise ValueError(f"sample size must be positive, got {n}")

        # Set seed if provided (must be separate statement in DuckDB)
        if seed is not None:
            # DuckDB's SETSEED expects value in range [0, 1]
            seed_value = (seed % (2**31)) / (2**31)
            self.dataset.engine.con().execute(f"SELECT SETSEED({seed_value})")  # nosec B608

        sample_sql = f"""
        SELECT * FROM ({self.sql()}) _sample
        ORDER BY RANDOM()
        LIMIT {n}
        """  # nosec B608 - n validated, self.sql() safe
        return self.dataset.engine.query_to_df(sample_sql)

    def count(self) -> int:
        """Return the number of rows matching the query."""
        count_sql = f"SELECT COUNT(*) AS cnt FROM ({self.sql()}) _count"  # nosec B608
        df = self.dataset.engine.query_to_df(count_sql)
        return int(df["cnt"].iloc[0])

    @property
    def columns(self) -> list[str]:
        """Return list of column names."""
        schema_sql = f"SELECT * FROM ({self.sql()}) _schema LIMIT 0"  # nosec B608
        df = self.dataset.engine.query_to_df(schema_sql)
        return list(df.columns)

    @property
    def dtypes(self) -> dict[str, str]:
        """Return mapping of column names to their data types."""
        schema_sql = f"SELECT * FROM ({self.sql()}) _schema LIMIT 0"  # nosec B608
        df = self.dataset.engine.query_to_df(schema_sql)
        return {col: str(df[col].dtype) for col in df.columns}

    def describe(self, geometry_col: str = "geometry") -> pd.DataFrame:
        """Return summary statistics for numeric columns."""
        from geofabric.validation import compute_stats

        stats = compute_stats(self.dataset.engine, self.sql(), geometry_col)
        return pd.DataFrame(
            [
                {
                    "rows": stats.row_count,
                    "columns": stats.column_count,
                    "geometry_type": stats.geometry_type,
                    "crs": stats.crs,
                    "bounds": stats.bounds,
                }
            ]
        )

    def explain(self) -> str:
        """Return the query execution plan."""
        explain_sql = f"EXPLAIN {self.sql()}"
        df = self.dataset.engine.query_to_df(explain_sql)
        return str(df.to_string(index=False))

    # Spatial operations - using Template Method pattern via _apply_spatial_op
    def buffer(
        self,
        distance: float,
        unit: str = "meters",
        geometry_col: str = "geometry",
    ) -> Query:
        """Buffer geometries by a distance."""
        from geofabric.spatial import BufferOp

        return self._apply_spatial_op(BufferOp, geometry_col, distance=distance, unit=unit)

    def simplify(
        self,
        tolerance: float,
        preserve_topology: bool = True,
        geometry_col: str = "geometry",
    ) -> Query:
        """Simplify geometries with a tolerance."""
        from geofabric.spatial import SimplifyOp

        return self._apply_spatial_op(
            SimplifyOp, geometry_col, tolerance=tolerance, preserve_topology=preserve_topology
        )

    def centroid(self, geometry_col: str = "geometry") -> Query:
        """Replace geometries with their centroids."""
        from geofabric.spatial import CentroidOp

        return self._apply_spatial_op(CentroidOp, geometry_col)

    def convex_hull(self, geometry_col: str = "geometry") -> Query:
        """Replace geometries with their convex hulls."""
        from geofabric.spatial import ConvexHullOp

        return self._apply_spatial_op(ConvexHullOp, geometry_col)

    def envelope(self, geometry_col: str = "geometry") -> Query:
        """Replace geometries with their bounding boxes."""
        from geofabric.spatial import EnvelopeOp

        return self._apply_spatial_op(EnvelopeOp, geometry_col)

    def make_valid(self, geometry_col: str = "geometry") -> Query:
        """Repair invalid geometries using ST_MakeValid."""
        from geofabric.spatial import MakeValidOp

        return self._apply_spatial_op(MakeValidOp, geometry_col)

    def transform(
        self,
        to_srid: int,
        from_srid: int = 4326,
        geometry_col: str = "geometry",
    ) -> Query:
        """Transform geometries to a different CRS.

        Args:
            to_srid: Target SRID (e.g., 3857 for Web Mercator)
            from_srid: Source SRID (default: 4326 WGS84)
            geometry_col: Name of geometry column
        """
        from geofabric.spatial import TransformOp

        return self._apply_spatial_op(
            TransformOp, geometry_col, from_srid=from_srid, to_srid=to_srid
        )

    def clip(
        self,
        clip_wkt: str,
        geometry_col: str = "geometry",
    ) -> Query:
        """Clip geometries to a boundary (intersection)."""
        from geofabric.spatial import IntersectionOp

        return self._apply_spatial_op(IntersectionOp, geometry_col, other_wkt=clip_wkt)

    def erase(
        self,
        erase_wkt: str,
        geometry_col: str = "geometry",
    ) -> Query:
        """Erase a region from geometries (difference)."""
        from geofabric.spatial import DifferenceOp

        return self._apply_spatial_op(DifferenceOp, geometry_col, other_wkt=erase_wkt)

    def boundary(self, geometry_col: str = "geometry") -> Query:
        """Extract geometry boundaries."""
        from geofabric.spatial import BoundaryOp

        return self._apply_spatial_op(BoundaryOp, geometry_col)

    def explode(self, geometry_col: str = "geometry") -> Query:
        """Explode multi-part geometries into single-part geometries.

        Note: This changes the number of rows in the result.
        """
        from geofabric.spatial import ExplodeOp

        return self._apply_spatial_op(ExplodeOp, geometry_col)

    def densify(self, max_distance: float, geometry_col: str = "geometry") -> Query:
        """Add intermediate vertices along geometry edges.

        Args:
            max_distance: Maximum distance between vertices (in geometry units)
            geometry_col: Name of geometry column
        """
        from geofabric.spatial import DensifyOp

        return self._apply_spatial_op(DensifyOp, geometry_col, max_distance=max_distance)

    def point_on_surface(self, geometry_col: str = "geometry") -> Query:
        """Replace geometries with a point guaranteed to be on the surface.

        Unlike centroid, this point is always inside the geometry.
        """
        from geofabric.spatial import PointOnSurfaceOp

        return self._apply_spatial_op(PointOnSurfaceOp, geometry_col)

    def reverse(self, geometry_col: str = "geometry") -> Query:
        """Reverse the order of vertices in geometries."""
        from geofabric.spatial import ReverseOp

        return self._apply_spatial_op(ReverseOp, geometry_col)

    def flip_coordinates(self, geometry_col: str = "geometry") -> Query:
        """Flip X and Y coordinates (useful for lat/lon vs lon/lat issues)."""
        from geofabric.spatial import FlipCoordinatesOp

        return self._apply_spatial_op(FlipCoordinatesOp, geometry_col)

    def with_area(
        self,
        column_name: str = "area",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add an area column computed from geometries.

        Args:
            column_name: Name for the new area column
            geometry_col: Name of geometry column
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_Area({geom_expr}) AS {column_name}"
        )

    def with_length(
        self,
        column_name: str = "length",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a length/perimeter column computed from geometries.

        Args:
            column_name: Name for the new length column
            geometry_col: Name of geometry column
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_Length({geom_expr}) AS {column_name}"
        )

    def with_perimeter(
        self,
        column_name: str = "perimeter",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a perimeter column computed from polygon geometries.

        Uses ST_Perimeter which correctly calculates the perimeter of polygons.
        For LineStrings, use with_length() instead.

        Args:
            column_name: Name for the new perimeter column
            geometry_col: Name of geometry column
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_Perimeter({geom_expr}) AS {column_name}"
        )

    def with_bounds(
        self,
        geometry_col: str = "geometry",
    ) -> Query:
        """Add columns for geometry bounding box (minx, miny, maxx, maxy)."""
        _validate_geometry_col(geometry_col)
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_columns([
            f"ST_XMin({geom_expr}) AS minx",
            f"ST_YMin({geom_expr}) AS miny",
            f"ST_XMax({geom_expr}) AS maxx",
            f"ST_YMax({geom_expr}) AS maxy",
        ])

    def with_geometry_type(
        self,
        column_name: str = "geom_type",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column with the geometry type (Point, LineString, Polygon, etc.)."""
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_GeometryType({geom_expr}) AS {column_name}"
        )

    def with_num_points(
        self,
        column_name: str = "num_points",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column with the number of points in each geometry."""
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_NPoints({geom_expr}) AS {column_name}"
        )

    def with_is_valid(
        self,
        column_name: str = "is_valid",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column indicating if each geometry is valid."""
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_IsValid({geom_expr}) AS {column_name}"
        )

    def with_distance_to(
        self,
        reference_wkt: str,
        column_name: str = "distance",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column with distance to a reference geometry.

        Args:
            reference_wkt: WKT string of reference geometry (e.g., 'POINT(-73.9 40.7)')
            column_name: Name for the distance column
            geometry_col: Name of geometry column
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        # Escape WKT to prevent SQL injection
        escaped = escape_wkt(reference_wkt)
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_Distance({geom_expr}, "
            f"ST_GeomFromText('{escaped}')) AS {column_name}"
        )

    def with_x(
        self,
        column_name: str = "x",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column with X coordinate (longitude) of point geometries.

        Note: For non-point geometries, returns X of the centroid.
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_X(ST_Centroid({geom_expr})) AS {column_name}"
        )

    def with_y(
        self,
        column_name: str = "y",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add a column with Y coordinate (latitude) of point geometries.

        Note: For non-point geometries, returns Y of the centroid.
        """
        _validate_geometry_col(geometry_col)
        _validate_column_name(column_name, "column name")
        geom_expr = self._geom_expr(geometry_col)
        return self._with_computed_column(
            f"ST_Y(ST_Centroid({geom_expr})) AS {column_name}"
        )

    def with_coordinates(
        self,
        x_column: str = "x",
        y_column: str = "y",
        geometry_col: str = "geometry",
    ) -> Query:
        """Add X and Y coordinate columns for point geometries.

        Convenience method that adds both X (longitude) and Y (latitude) columns.
        """
        # Validation handled by with_x and with_y
        return self.with_x(column_name=x_column, geometry_col=geometry_col).with_y(
            column_name=y_column, geometry_col=geometry_col
        )

    def collect(self, geometry_col: str = "geometry") -> Query:
        """Collect all geometries into a single MultiGeometry.

        Opposite of explode() - gathers multiple geometries into one.
        """
        _validate_geometry_col(geometry_col)
        geom_expr = self._geom_expr(geometry_col)
        # Wrap in ST_AsWKB for consistent WKB output
        collect_sql = f"""
        SELECT ST_AsWKB(ST_Collect(list({geom_expr}))) AS {geometry_col}
        FROM ({self.sql()}) _collect
        """  # nosec B608 - geometry_col validated above
        return _wrap_sql_as_query(self.dataset, collect_sql)

    def symmetric_difference(
        self,
        other_wkt: str,
        geometry_col: str = "geometry",
    ) -> Query:
        """Compute symmetric difference (XOR) with another geometry.

        Returns parts of geometries that don't overlap with the reference.

        Args:
            other_wkt: WKT string of the other geometry
            geometry_col: Name of geometry column
        """
        from geofabric.spatial import SymmetricDifferenceOp

        return self._apply_spatial_op(SymmetricDifferenceOp, geometry_col, other_wkt=other_wkt)

    # Spatial joins
    def sjoin(
        self,
        other: Query,
        predicate: str = "intersects",
        how: str = "inner",
        lsuffix: str = "_left",  # Currently unused - kept for API compatibility
        rsuffix: str = "_right",  # Currently unused - kept for API compatibility
        geometry_col: str = "geometry",
    ) -> Query:
        """Spatial join with another query.

        Args:
            other: Other query to join with
            predicate: Spatial predicate - 'intersects', 'within', 'contains'
            how: Join type - 'inner', 'left'
            lsuffix: Suffix for left columns (not yet implemented)
            rsuffix: Suffix for right columns (not yet implemented)
            geometry_col: Geometry column name

        Note:
            lsuffix and rsuffix are not yet implemented. Conflicting column
            names are not automatically renamed. Use select() to rename
            columns before joining if needed.
        """
        # Warn if non-default suffix values are provided (they're not implemented)
        if lsuffix != "_left" or rsuffix != "_right":
            import warnings

            warnings.warn(
                "lsuffix and rsuffix parameters are not yet implemented and will be ignored. "
                "Use select() to rename columns before joining if needed.",
                stacklevel=2,
            )

        # Validate geometry column to prevent SQL injection
        _validate_geometry_col(geometry_col)

        # Validate how parameter
        valid_how = {"inner", "left"}
        if how not in valid_how:
            raise ValueError(f"Invalid join type '{how}'. Must be one of: {sorted(valid_how)}")

        left_sql = self.sql()
        right_sql = other.sql()

        # Map predicate to DuckDB spatial function
        predicate_map = {
            "intersects": "ST_Intersects",
            "within": "ST_Within",
            "contains": "ST_Contains",
            "touches": "ST_Touches",
            "crosses": "ST_Crosses",
            "overlaps": "ST_Overlaps",
        }
        if predicate not in predicate_map:
            raise ValueError(
                f"Unknown predicate: {predicate}. Use one of {list(predicate_map.keys())}"
            )

        st_func = predicate_map[predicate]
        join_type = "LEFT JOIN" if how == "left" else "JOIN"

        # Detect geometry types for both sides
        # DuckDB's binder checks types at parse time
        l_type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({left_sql}) LIMIT 1"
        r_type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({right_sql}) LIMIT 1"
        try:
            l_type_df = self.dataset.engine.query_to_df(l_type_sql)
            l_geom_type = l_type_df["geom_type"].iloc[0] if len(l_type_df) > 0 else "GEOMETRY"
        except Exception:
            l_geom_type = "GEOMETRY"
        try:
            r_type_df = other.dataset.engine.query_to_df(r_type_sql)
            r_geom_type = r_type_df["geom_type"].iloc[0] if len(r_type_df) > 0 else "GEOMETRY"
        except Exception:
            r_geom_type = "GEOMETRY"

        # Build type-specific expressions
        if l_geom_type in ("WKB_BLOB", "BLOB"):
            l_geom = f"ST_GeomFromWKB(l.{geometry_col})"
        else:
            l_geom = f"l.{geometry_col}"
        if r_geom_type in ("WKB_BLOB", "BLOB"):
            r_geom = f"ST_GeomFromWKB(r.{geometry_col})"
        else:
            r_geom = f"r.{geometry_col}"

        join_sql = f"""
        SELECT l.*, r.* EXCLUDE ({geometry_col})
        FROM ({left_sql}) l
        {join_type} ({right_sql}) r
        ON {st_func}({l_geom}, {r_geom})
        """  # nosec B608 - geometry_col validated, predicate from whitelist
        return _wrap_sql_as_query(self.dataset, join_sql)

    def nearest(
        self,
        other: Query,
        k: int = 1,
        max_distance: float | None = None,
        geometry_col: str = "geometry",
    ) -> Query:
        """Find k nearest neighbors from another query.

        Columns from the right query are automatically renamed with a '_right'
        suffix when they would conflict with columns from the left query.
        The distance to each neighbor is returned in the '_distance' column.

        Args:
            other: Other query containing features to find nearest to
            k: Number of nearest neighbors to find
            max_distance: Maximum distance to search (optional)
            geometry_col: Geometry column name

        Returns:
            Query with left columns, renamed right columns, and _distance column
        """
        # Validate geometry column to prevent SQL injection
        _validate_geometry_col(geometry_col)

        # Validate parameters
        if k < 1:
            raise ValueError(f"k must be at least 1, got {k}")
        if max_distance is not None and max_distance <= 0:
            raise ValueError(f"max_distance must be positive, got {max_distance}")

        left_sql = self.sql()
        right_sql = other.sql()

        # Get column names from both sides to handle naming conflicts
        try:
            left_cols_df = self.dataset.engine.query_to_df(
                f"SELECT column_name FROM (DESCRIBE ({left_sql}))"
            )
            left_cols = set(left_cols_df["column_name"].tolist())
        except Exception:
            left_cols = set()

        try:
            right_cols_df = other.dataset.engine.query_to_df(
                f"SELECT column_name FROM (DESCRIBE ({right_sql}))"
            )
            right_cols = right_cols_df["column_name"].tolist()
        except Exception:
            right_cols = []

        # Detect geometry types for both sides
        # DuckDB's binder checks types at parse time
        l_type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({left_sql}) LIMIT 1"
        r_type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({right_sql}) LIMIT 1"
        try:
            l_type_df = self.dataset.engine.query_to_df(l_type_sql)
            l_geom_type = l_type_df["geom_type"].iloc[0] if len(l_type_df) > 0 else "GEOMETRY"
        except Exception:
            l_geom_type = "GEOMETRY"
        try:
            r_type_df = other.dataset.engine.query_to_df(r_type_sql)
            r_geom_type = r_type_df["geom_type"].iloc[0] if len(r_type_df) > 0 else "GEOMETRY"
        except Exception:
            r_geom_type = "GEOMETRY"

        # Build type-specific expressions
        if l_geom_type in ("WKB_BLOB", "BLOB"):
            l_geom = f"ST_GeomFromWKB(l.{geometry_col})"
        else:
            l_geom = f"l.{geometry_col}"
        if r_geom_type in ("WKB_BLOB", "BLOB"):
            r_geom = f"ST_GeomFromWKB(r.{geometry_col})"
        else:
            r_geom = f"r.{geometry_col}"

        distance_filter = ""
        if max_distance is not None:
            distance_filter = f"AND ST_Distance({l_geom}, {r_geom}) <= {max_distance}"

        # Build right column expressions with _right suffix for conflicts
        # Exclude the geometry column from the right side
        right_col_exprs = []
        for col in right_cols:
            if col == geometry_col:
                continue  # Skip geometry column from right side
            if col in left_cols:
                # Conflict: rename with _right suffix
                right_col_exprs.append(f'r."{col}" AS "{col}_right"')
            else:
                # No conflict: keep original name
                right_col_exprs.append(f'r."{col}"')

        # If we couldn't get column info, fall back to r.* EXCLUDE
        if right_col_exprs:
            right_select = ", ".join(right_col_exprs)
        else:
            right_select = f"r.* EXCLUDE ({geometry_col})"

        nearest_sql = f"""
        SELECT l.*, {right_select},
               ST_Distance({l_geom}, {r_geom}) AS _distance
        FROM ({left_sql}) l
        CROSS JOIN LATERAL (
            SELECT *
            FROM ({right_sql}) r
            WHERE TRUE {distance_filter}
            ORDER BY ST_Distance({l_geom}, {r_geom})
            LIMIT {k}
        ) r
        """  # nosec B608 - geometry_col validated, k/max_distance are validated numerics
        return _wrap_sql_as_query(self.dataset, nearest_sql)

    # Streaming / chunked processing
    def iter_chunks(
        self,
        chunk_size: int = 10000,
    ) -> Iterator[pa.RecordBatch]:
        """Iterate over query results in chunks.

        Args:
            chunk_size: Number of rows per chunk (must be >= 1)

        Yields:
            RecordBatch objects with up to chunk_size rows

        Raises:
            ValueError: If chunk_size < 1
        """
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        arrow_table = self.to_arrow()
        yield from arrow_table.to_batches(max_chunksize=chunk_size)

    def iter_dataframes(
        self,
        chunk_size: int = 10000,
    ) -> Iterator[pd.DataFrame]:
        """Iterate over query results as DataFrames.

        Args:
            chunk_size: Number of rows per chunk (must be >= 1)

        Yields:
            DataFrame objects with up to chunk_size rows

        Raises:
            ValueError: If chunk_size < 1
        """
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        for batch in self.iter_chunks(chunk_size):
            yield batch.to_pandas()

    # Additional output formats
    def to_flatgeobuf(self, path: str, geometry_col: str = "geometry") -> str:
        """Export to FlatGeobuf format."""
        _validate_geometry_col(geometry_col)
        gdf = self.to_geopandas(geometry_col=geometry_col)
        gdf.to_file(path, driver="FlatGeobuf")
        return path

    def to_geopackage(
        self,
        path: str,
        layer: str = "data",
        geometry_col: str = "geometry",
    ) -> str:
        """Export to GeoPackage format."""
        _validate_geometry_col(geometry_col)
        # Validate layer name (it's used as identifier)
        _validate_column_name(layer, "layer name")
        gdf = self.to_geopandas(geometry_col=geometry_col)
        gdf.to_file(path, driver="GPKG", layer=layer)
        return path

    def to_csv(self, path: str, include_wkt: bool = True, geometry_col: str = "geometry") -> str:
        """Export to CSV format (optionally with WKT geometry)."""
        _validate_geometry_col(geometry_col)
        if include_wkt:
            geom_expr = self._geom_expr(geometry_col)
            wkt_sql = f"""
            SELECT * EXCLUDE ({geometry_col}),
                   ST_AsText({geom_expr}) AS {geometry_col}_wkt
            FROM ({self.sql()}) _csv
            """  # nosec B608 - geometry_col validated above
            df = self.dataset.engine.query_to_df(wkt_sql)
        else:
            df = self.to_pandas()
            if geometry_col in df.columns:
                df = df.drop(columns=[geometry_col])
        df.to_csv(path, index=False)
        return path

    # Aggregations
    def dissolve(
        self,
        by: str | list[str] | None = None,
        geometry_col: str = "geometry",
    ) -> Query:
        """Dissolve geometries, optionally grouped by columns."""
        # Validate geometry_col to prevent SQL injection
        validate_sql_identifier(geometry_col, "geometry column")

        geom_expr = self._geom_expr(geometry_col)
        q = self._clone()
        if by is None:
            # Dissolve all into one geometry
            # Wrap in ST_AsWKB for consistent WKB output
            new_sql = f"""
            SELECT ST_AsWKB(ST_Union_Agg({geom_expr})) AS {geometry_col}
            FROM ({self.sql()}) _dissolve
            """  # nosec B608 - geometry_col validated above
        else:
            by_cols = [by] if isinstance(by, str) else by
            # Validate all column names to prevent SQL injection
            for col in by_cols:
                validate_sql_identifier(col, "column")
            by_sql = ", ".join(by_cols)
            # Wrap in ST_AsWKB for consistent WKB output
            new_sql = f"""
            SELECT {by_sql},
                   ST_AsWKB(ST_Union_Agg({geom_expr})) AS {geometry_col}
            FROM ({self.sql()}) _dissolve
            GROUP BY {by_sql}
            """  # nosec B608 - geometry_col and by_cols validated above
        # Return a new query wrapping the dissolved result
        q._select = ["*"]
        q._where = []
        q._limit = None
        # We need to create a modified dataset that uses this SQL
        return _wrap_sql_as_query(self.dataset, new_sql)


@dataclass
class SQLSource:
    """A source that wraps raw SQL.

    Implements SourceWithDuckDBRelation protocol.
    """

    sql: str

    def source_kind(self) -> str:
        return "sql"

    def to_duckdb_relation_sql(self, engine: Any) -> str:
        """Return the raw SQL wrapped in parentheses."""
        return f"({self.sql})"


def _wrap_sql_as_query(dataset: Any, sql: str) -> Query:
    """Create a query that wraps raw SQL."""
    from geofabric.dataset import Dataset

    # Create a new dataset with a SQL source
    new_dataset = Dataset(source=SQLSource(sql=sql), engine=dataset.engine)
    return Query(dataset=new_dataset)
