"""Geometry validation and QA utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from geofabric.sql_utils import validate_sql_identifier

if TYPE_CHECKING:
    from geofabric.engines.duckdb_engine import DuckDBEngine

__all__ = [
    "DatasetStats",
    "ValidationIssue",
    "ValidationResult",
    "compute_stats",
    "validate_geometries",
]

# Display formatting constants
_BOUNDS_PRECISION = 4  # Decimal places for coordinate display
_DEFAULT_CRS = "EPSG:4326"  # Assumed CRS when not detectable


@dataclass(frozen=True)
class ValidationIssue:
    """A geometry validation issue."""

    row_id: Any
    issue_type: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of geometry validation."""

    total_rows: int
    valid_count: int
    invalid_count: int
    null_count: int
    issues: list[ValidationIssue]

    @property
    def is_valid(self) -> bool:
        return self.invalid_count == 0

    def summary(self) -> str:
        return (
            f"Validation Result:\n"
            f"  Total rows: {self.total_rows}\n"
            f"  Valid: {self.valid_count}\n"
            f"  Invalid: {self.invalid_count}\n"
            f"  Null: {self.null_count}\n"
            f"  Status: {'✓ All valid' if self.is_valid else '✗ Has issues'}"
        )


@dataclass(frozen=True)
class DatasetStats:
    """Statistics about a dataset."""

    row_count: int
    column_count: int
    columns: list[str]
    dtypes: dict[str, str]
    bounds: tuple[float, float, float, float] | None  # minx, miny, maxx, maxy
    geometry_type: str | None
    crs: str | None
    null_counts: dict[str, int]

    def summary(self) -> str:
        bounds_str = (
            f"({self.bounds[0]:.{_BOUNDS_PRECISION}f}, {self.bounds[1]:.{_BOUNDS_PRECISION}f}, "
            f"{self.bounds[2]:.{_BOUNDS_PRECISION}f}, {self.bounds[3]:.{_BOUNDS_PRECISION}f})"
            if self.bounds
            else "N/A"
        )
        return (
            f"Dataset Statistics:\n"
            f"  Rows: {self.row_count:,}\n"
            f"  Columns: {self.column_count}\n"
            f"  Geometry Type: {self.geometry_type or 'N/A'}\n"
            f"  CRS: {self.crs or 'N/A'}\n"
            f"  Bounds: {bounds_str}"
        )


def validate_geometries(
    engine: DuckDBEngine,
    sql: str,
    geometry_col: str = "geometry",
    id_col: str | None = None,
) -> ValidationResult:
    """Validate geometries in a query result.

    Args:
        engine: DuckDB engine for query execution
        sql: SQL query to validate
        geometry_col: Name of the geometry column
        id_col: Optional column to use as row identifier

    Returns:
        ValidationResult with validation statistics and issues

    Raises:
        ValueError: If sql is empty or column names are invalid
    """
    # Validate inputs
    if not sql or not sql.strip():
        raise ValueError("sql must not be empty")

    # Validate column names to prevent SQL injection
    validate_sql_identifier(geometry_col, "geometry column")
    if id_col:
        validate_sql_identifier(id_col, "id column")

    # Build validation query
    id_expr = id_col if id_col else "ROW_NUMBER() OVER ()"

    # Detect geometry column type
    # DuckDB's binder checks types at parse time
    type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({sql}) LIMIT 1"
    try:
        type_df = engine.query_to_df(type_sql)
        geom_type = type_df["geom_type"].iloc[0] if len(type_df) > 0 else "GEOMETRY"
    except Exception:
        geom_type = "GEOMETRY"

    # Build type-specific expression
    if geom_type in ("WKB_BLOB", "BLOB"):
        geom_expr = f"ST_GeomFromWKB({geometry_col})"
    else:
        geom_expr = geometry_col
    # Note: ST_IsValidReason is not available in DuckDB Spatial,
    # so we just report 'Invalid geometry' as the reason
    validation_sql = f"""
    SELECT
        {id_expr} AS _row_id,
        CASE
            WHEN {geometry_col} IS NULL THEN 'null'
            WHEN ST_IsValid({geom_expr}) THEN 'valid'
            ELSE 'invalid'
        END AS _validity,
        CASE
            WHEN {geometry_col} IS NOT NULL AND NOT ST_IsValid({geom_expr})
            THEN 'Invalid geometry'
            ELSE NULL
        END AS _reason
    FROM ({sql}) _validate_subq
    """  # nosec B608 - geometry_col and id_col validated via validate_sql_identifier

    df = engine.query_to_df(validation_sql)

    total = len(df)
    valid_count = (df["_validity"] == "valid").sum()
    invalid_count = (df["_validity"] == "invalid").sum()
    null_count = (df["_validity"] == "null").sum()

    issues = []
    invalid_rows = df[df["_validity"] == "invalid"]
    for _, row in invalid_rows.iterrows():
        issues.append(
            ValidationIssue(
                row_id=row["_row_id"],
                issue_type="invalid_geometry",
                message=row["_reason"] or "Unknown validation error",
            )
        )

    return ValidationResult(
        total_rows=total,
        valid_count=int(valid_count),
        invalid_count=int(invalid_count),
        null_count=int(null_count),
        issues=issues,
    )


def compute_stats(
    engine: DuckDBEngine,
    sql: str,
    geometry_col: str = "geometry",
) -> DatasetStats:
    """Compute statistics for a query result.

    Args:
        engine: DuckDB engine for query execution
        sql: SQL query to compute statistics for
        geometry_col: Name of the geometry column

    Returns:
        DatasetStats with computed statistics

    Raises:
        ValueError: If sql is empty or geometry_col is invalid
    """
    # Validate inputs
    if not sql or not sql.strip():
        raise ValueError("sql must not be empty")

    # Validate geometry column name to prevent SQL injection
    validate_sql_identifier(geometry_col, "geometry column")

    # Get basic info
    info_sql = f"SELECT * FROM ({sql}) _stats_subq LIMIT 0"  # nosec B608
    df_schema = engine.query_to_df(info_sql)
    columns = list(df_schema.columns)
    dtypes = {col: str(df_schema[col].dtype) for col in columns}

    # Get row count
    count_sql = f"SELECT COUNT(*) AS cnt FROM ({sql}) _count_subq"  # nosec B608
    count_df = engine.query_to_df(count_sql)
    row_count = int(count_df["cnt"].iloc[0])

    # Get null counts - quote column names to handle reserved words and special chars
    def _quote_col(col: str) -> str:
        """Quote column name for DuckDB (double quotes, escape existing quotes)."""
        return '"' + col.replace('"', '""') + '"'

    null_exprs = ", ".join(
        f'SUM(CASE WHEN {_quote_col(col)} IS NULL THEN 1 ELSE 0 END) AS "{col}_nulls"'
        for col in columns
    )
    null_sql = f"SELECT {null_exprs} FROM ({sql}) _null_subq"  # nosec B608
    null_df = engine.query_to_df(null_sql)
    null_counts = {col: int(null_df[f"{col}_nulls"].iloc[0]) for col in columns}

    # Get bounds if geometry column exists
    bounds = None
    geometry_type = None
    if geometry_col in columns:
        # Detect geometry column type
        # DuckDB's binder checks types at parse time
        type_sql = f"SELECT typeof({geometry_col}) AS geom_type FROM ({sql}) LIMIT 1"
        try:
            type_df = engine.query_to_df(type_sql)
            col_geom_type = type_df["geom_type"].iloc[0] if len(type_df) > 0 else "GEOMETRY"
        except Exception:
            col_geom_type = "GEOMETRY"

        # Build type-specific expression
        if col_geom_type in ("WKB_BLOB", "BLOB"):
            geom_cast = f"ST_GeomFromWKB({geometry_col})"
        else:
            geom_cast = geometry_col
        bounds_sql = f"""
        SELECT
            MIN(ST_XMin({geom_cast})) AS minx,
            MIN(ST_YMin({geom_cast})) AS miny,
            MAX(ST_XMax({geom_cast})) AS maxx,
            MAX(ST_YMax({geom_cast})) AS maxy,
            MODE(ST_GeometryType({geom_cast})) AS geom_type
        FROM ({sql}) _bounds_subq
        WHERE {geometry_col} IS NOT NULL
        """  # nosec B608 - geometry_col validated via validate_sql_identifier
        try:
            bounds_df = engine.query_to_df(bounds_sql)
            if not bounds_df.empty:
                minx_val = bounds_df["minx"].iloc[0]
                miny_val = bounds_df["miny"].iloc[0]
                maxx_val = bounds_df["maxx"].iloc[0]
                maxy_val = bounds_df["maxy"].iloc[0]
                # Only set bounds if all values are valid (not None/NaN)
                if all(v is not None and v == v for v in [minx_val, miny_val, maxx_val, maxy_val]):
                    bounds = (
                        float(minx_val),
                        float(miny_val),
                        float(maxx_val),
                        float(maxy_val),
                    )
                geometry_type = bounds_df["geom_type"].iloc[0]
        except (ValueError, TypeError, KeyError) as e:
            # Log warning but continue - bounds are optional
            import warnings

            warnings.warn(f"Could not compute geometry bounds: {e}", stacklevel=2)

    return DatasetStats(
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        dtypes=dtypes,
        bounds=bounds,
        geometry_type=geometry_type,
        crs=_DEFAULT_CRS,  # Assume WGS84 for now
        null_counts=null_counts,
    )
