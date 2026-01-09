from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import typer
from rich import print as rprint
from rich.table import Table

import geofabric as gf
from geofabric.sources.overture import Overture

if TYPE_CHECKING:
    import pandas as pd

    from geofabric.query import Query

app = typer.Typer(help="GeoFabric CLI (gf)")

overture_app = typer.Typer(help="Overture helpers")
app.add_typer(overture_app, name="overture")


class OutputFormat(str, Enum):
    """Output format options."""

    parquet = "parquet"
    geojson = "geojson"
    csv = "csv"
    flatgeobuf = "flatgeobuf"
    geopackage = "geopackage"


def write_query_to_format(query: "Query", out_path: str, format_: OutputFormat) -> None:
    """Write query results to the specified output format.

    Centralizes format writing logic to eliminate code duplication.
    Uses a dispatch dict pattern for O(1) lookup.

    Args:
        query: The query to write
        out_path: Output file path
        format_: Output format enum value

    Design Principles:
        - DRY: Single implementation of format dispatch
        - Open/Closed: Easy to add new formats by extending dict
    """
    # Dispatch table for format writers (O(1) lookup vs if/elif chain)
    writers = {
        OutputFormat.parquet: query.to_parquet,
        OutputFormat.geojson: query.to_geojson,
        OutputFormat.csv: query.to_csv,
        OutputFormat.flatgeobuf: query.to_flatgeobuf,
        OutputFormat.geopackage: query.to_geopackage,
    }
    writer = writers.get(format_)
    if writer is None:
        raise ValueError(f"Unsupported output format: {format_}")
    writer(out_path)


def write_dataframe_to_format(
    df: "pd.DataFrame", out_path: str, format_: OutputFormat
) -> None:
    """Write a DataFrame to the specified output format.

    Handles the case where methods like sample() return DataFrames directly.
    DataFrames only support a subset of formats.

    Args:
        df: The DataFrame to write
        out_path: Output file path
        format_: Output format enum value

    Raises:
        ValueError: If format is not supported for DataFrames
    """
    if format_ == OutputFormat.parquet:
        df.to_parquet(out_path, index=False)
    elif format_ == OutputFormat.csv:
        df.to_csv(out_path, index=False)
    else:
        # GeoJSON, FlatGeobuf, GeoPackage require Query methods
        raise ValueError(
            f"Format '{format_.value}' not supported for sampled data. "
            "Use 'parquet' or 'csv' format for sample output."
        )


@app.command()
def sql(uri: str, query: str) -> None:
    """
    Run a SQL query against a dataset.
    Use "data" as the table name in your query.
    Example:
      gf sql file:///tmp/x.parquet "SELECT COUNT(*) FROM data"
    """
    ds = gf.open(uri)
    engine = ds.engine
    relation = engine.source_to_relation_sql(ds.source)
    final_sql = query.replace("FROM data", f"FROM {relation}")
    df = engine.query_to_df(final_sql)
    rprint(df.to_string(index=False))


@app.command()
def pull(
    uri: str,
    out: str,
    where: str = typer.Option("", help="SQL WHERE predicate"),
    limit: int = typer.Option(0, help="Limit rows (0 = no limit)"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Pull a subset of a dataset to a file.
    """
    ds = gf.open(uri)
    q = ds.query()
    if where.strip():
        q = q.where(where.strip())
    if limit > 0:
        q = q.limit(limit)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote[/green] {out}")


@app.command()
def info(
    uri: str,
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
) -> None:
    """
    Show information about a dataset.
    """
    ds = gf.open(uri)

    # Get basic info
    stats = ds.stats(geometry_col=geometry_col)

    # Create a table for display
    table = Table(title="Dataset Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Rows", f"{stats.row_count:,}")
    table.add_row("Columns", str(stats.column_count))
    table.add_row("Geometry Type", stats.geometry_type or "N/A")
    table.add_row("CRS", stats.crs or "N/A")

    if stats.bounds:
        bounds_str = (
            f"({stats.bounds[0]:.4f}, {stats.bounds[1]:.4f}, "
            f"{stats.bounds[2]:.4f}, {stats.bounds[3]:.4f})"
        )
        table.add_row("Bounds", bounds_str)
    else:
        table.add_row("Bounds", "N/A")

    rprint(table)

    # Show columns
    rprint("\n[bold]Columns:[/bold]")
    for col, dtype in stats.dtypes.items():
        null_count = stats.null_counts.get(col, 0)
        null_pct = (null_count / stats.row_count * 100) if stats.row_count > 0 else 0
        rprint(f"  {col}: {dtype} ({null_pct:.1f}% null)")


@app.command()
def validate(
    uri: str,
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
) -> None:
    """
    Validate geometries in a dataset.
    """
    ds = gf.open(uri)
    result = ds.validate(geometry_col=geometry_col)
    rprint(result.summary())

    if result.issues:
        rprint("\n[bold red]Issues found:[/bold red]")
        for issue in result.issues[:10]:  # Show first 10 issues
            rprint(f"  Row {issue.row_id}: {issue.message}")
        if len(result.issues) > 10:
            rprint(f"  ... and {len(result.issues) - 10} more issues")


@app.command()
def head(
    uri: str,
    n: int = typer.Option(10, help="Number of rows to show"),
) -> None:
    """
    Show the first N rows of a dataset.
    """
    ds = gf.open(uri)
    df = ds.head(n)
    rprint(df.to_string(index=False))


@app.command()
def sample(
    uri: str,
    out: str,
    n: int = typer.Option(1000, help="Number of rows to sample"),
    seed: int | None = typer.Option(None, help="Random seed for reproducibility"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format (parquet or csv)",
    ),
) -> None:
    """
    Sample random rows from a dataset.

    Note: sample returns a DataFrame, so only parquet and csv formats are supported.
    """
    ds = gf.open(uri)
    df = ds.query().sample(n, seed=seed)

    write_dataframe_to_format(df, out, format_)
    rprint(f"[green]Wrote {n} samples to[/green] {out}")


@app.command()
def stats(
    uri: str,
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
) -> None:
    """
    Display detailed statistics about a dataset.
    """
    ds = gf.open(uri)
    dataset_stats = ds.stats(geometry_col=geometry_col)

    # Display statistics
    rprint(dataset_stats.summary())

    # Show null counts
    rprint("\n[bold]Null Counts:[/bold]")
    for col, count in dataset_stats.null_counts.items():
        if count > 0:
            pct = (count / dataset_stats.row_count * 100) if dataset_stats.row_count > 0 else 0
            rprint(f"  {col}: {count:,} ({pct:.1f}%)")


@app.command()
def buffer(
    uri: str,
    out: str,
    distance: float = typer.Option(..., help="Buffer distance"),
    unit: str = typer.Option("meters", help="Distance unit (meters, kilometers, miles, feet)"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Buffer geometries by a distance.
    """
    ds = gf.open(uri)
    q = ds.query().buffer(distance=distance, unit=unit, geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote buffered geometries to[/green] {out}")


@app.command()
def simplify(
    uri: str,
    out: str,
    tolerance: float = typer.Option(..., help="Simplification tolerance"),
    preserve_topology: bool = typer.Option(True, help="Preserve topology"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Simplify geometries with a tolerance.
    """
    ds = gf.open(uri)
    q = ds.query().simplify(
        tolerance=tolerance,
        preserve_topology=preserve_topology,
        geometry_col=geometry_col,
    )

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote simplified geometries to[/green] {out}")


@app.command()
def transform(
    uri: str,
    out: str,
    to_srid: int = typer.Option(..., help="Target SRID (e.g., 3857 for Web Mercator)"),
    from_srid: int = typer.Option(4326, help="Source SRID (default: 4326 WGS84)"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Transform geometries to a different coordinate reference system.
    """
    ds = gf.open(uri)
    q = ds.query().transform(
        to_srid=to_srid,
        from_srid=from_srid,
        geometry_col=geometry_col,
    )

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote transformed geometries to[/green] {out}")


@app.command()
def centroid(
    uri: str,
    out: str,
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Replace geometries with their centroids.
    """
    ds = gf.open(uri)
    q = ds.query().centroid(geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote centroids to[/green] {out}")


@app.command()
def convex_hull(
    uri: str,
    out: str,
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Replace geometries with their convex hulls.
    """
    ds = gf.open(uri)
    q = ds.query().convex_hull(geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote convex hulls to[/green] {out}")


@app.command()
def dissolve(
    uri: str,
    out: str,
    by: str | None = typer.Option(None, help="Column(s) to group by (comma-separated)"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Dissolve (merge) geometries, optionally grouped by columns.
    """
    ds = gf.open(uri)
    by_cols = by.split(",") if by else None
    q = ds.query().dissolve(by=by_cols, geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote dissolved geometries to[/green] {out}")


@app.command()
def add_area(
    uri: str,
    out: str,
    column_name: str = typer.Option("area", help="Name for the area column"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Add an area column to the dataset.
    """
    ds = gf.open(uri)
    q = ds.query().with_area(column_name=column_name, geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote dataset with area column to[/green] {out}")


@app.command()
def add_length(
    uri: str,
    out: str,
    column_name: str = typer.Option("length", help="Name for the length column"),
    geometry_col: str = typer.Option("geometry", help="Geometry column name"),
    format_: OutputFormat = typer.Option(
        OutputFormat.parquet,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """
    Add a length/perimeter column to the dataset.
    """
    ds = gf.open(uri)
    q = ds.query().with_length(column_name=column_name, geometry_col=geometry_col)

    write_query_to_format(q, out, format_)
    rprint(f"[green]Wrote dataset with length column to[/green] {out}")


@overture_app.command("download")
def overture_download(
    release: str = typer.Option(..., help="Overture release, e.g. 2025-12-17.0"),
    theme: str = typer.Option(..., help="theme, e.g. base"),
    type_: str = typer.Option(..., "--type", help="type, e.g. infrastructure"),
    dest: str = typer.Option(..., help="Destination directory"),
) -> None:
    """
    Download Overture partition to local folder (requires AWS CLI).
    """
    ov = Overture(release=release, theme=theme, type_=type_)
    out_dir = ov.download(dest)
    rprint(f"[green]Downloaded to[/green] {out_dir}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
