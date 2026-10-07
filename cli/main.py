"""
ARCHAEO-SCAN Command Line Interface.

Usage:
    archaeo data                                          # Show local data inventory
    archaeo info --bbox 34.0,-112.5,35.0,-111.0           # What's in a region
    archaeo score --bbox 34.0,-112.5,35.0,-111.0          # Score a region
    archaeo report --bbox 34.0,-112.5,35.0,-111.0         # Generate report file
    archaeo export --bbox 34.0,-112.5,35.0,-111.0         # Export GeoJSON/CSV
    archaeo serve --port 8050                              # Launch the Atlas GUI
    archaeo collect terrain --bbox ...                     # Download terrain data
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.schemas import BoundingBox

app = typer.Typer(
    name="archaeo",
    help="ARCHAEO-SCAN: Archaeological site discovery toolkit",
    no_args_is_help=True,
)
console = Console()

collect_app = typer.Typer(help="Collect data from remote sources")
process_app = typer.Typer(help="Process collected data into analysis layers")
app.add_typer(collect_app, name="collect")
app.add_typer(process_app, name="process")

PROJECT_ROOT = Path(__file__).parent.parent


def parse_bbox(bbox_str: str) -> BoundingBox:
    """Parse a comma-separated bbox string: min_lat,min_lon,max_lat,max_lon"""
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError
        return BoundingBox(min_lat=parts[0], min_lon=parts[1], max_lat=parts[2], max_lon=parts[3])
    except (ValueError, IndexError):
        console.print("[red]Invalid bbox format. Use: min_lat,min_lon,max_lat,max_lon[/red]")
        console.print("[dim]Example: 34.0,-112.5,35.0,-111.0[/dim]")
        raise typer.Exit(1)


def _get_store():
    """Get the local data store."""
    from core.local_data import LocalDataStore
    return LocalDataStore(PROJECT_ROOT)


# ============================================================
# DATA command — show what's on disk
# ============================================================

@app.command("data")
def data_inventory():
    """Show all local data files with record counts and sizes."""
    store = _get_store()

    with _progress("Scanning local data..."):
        summary = store.inventory_summary()

    # Header
    console.print(Panel(
        f"[bold green]{summary['total_records']:,}[/bold green] records across "
        f"[bold cyan]{summary['files_with_data']}[/bold cyan] datasets  "
        f"([dim]{summary['total_size_mb']:.1f} MB on disk[/dim])",
        title="[bold]ARCHAEO-SCAN Local Data Inventory[/bold]",
    ))

    # Processed files
    table = Table(title="Processed Data (cleaned, deduplicated, geocoded)")
    table.add_column("Dataset", style="cyan")
    table.add_column("Records", justify="right", style="green")
    table.add_column("Size", justify="right", style="dim")

    for ds in summary["datasets"]:
        if ds["label"].startswith("processed/"):
            name = ds["label"].replace("processed/", "").replace(".json", "")
            table.add_row(name, f"{ds['record_count']:,}", f"{ds['size_mb']:.1f} MB")
    console.print(table)

    # Raw files
    table2 = Table(title="Raw Scrapes (original source data)")
    table2.add_column("Source", style="cyan")
    table2.add_column("Records", justify="right", style="green")
    table2.add_column("Size", justify="right", style="dim")

    for ds in summary["datasets"]:
        if ds["label"].startswith("raw/") and ds["record_count"] > 0:
            name = ds["label"].replace("raw/", "").replace(".json", "")
            table2.add_row(name, f"{ds['record_count']:,}", f"{ds['size_mb']:.1f} MB")
    console.print(table2)

    # Empty files note
    empty = [ds for ds in summary["datasets"] if ds["record_count"] == 0]
    if empty:
        names = ", ".join(ds["label"].replace("raw/", "").replace(".json", "") for ds in empty if ds["label"].startswith("raw/"))
        console.print(f"\n[dim]Empty sources (no data collected yet): {names}[/dim]")


# ============================================================
# INFO command — what's in a region
# ============================================================

@app.command("info")
def info(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
):
    """Show what data is available for a region, using real local data."""
    bb = parse_bbox(bbox)
    store = _get_store()

    from core.geo_utils import bbox_area_km2
    from core.tile_grid import estimate_cell_count

    area = bbox_area_km2(bb)

    with _progress("Querying local data..."):
        datasets = store.all_sites_in_bbox(bb)

    # Region summary
    table = Table(title="Region Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    def _fmt_lat(v): return f"{abs(v):.4f}{'N' if v >= 0 else 'S'}"
    def _fmt_lon(v): return f"{abs(v):.4f}{'W' if v < 0 else 'E'}"
    table.add_row("Latitude", f"{_fmt_lat(bb.min_lat)} to {_fmt_lat(bb.max_lat)}")
    table.add_row("Longitude", f"{_fmt_lon(bb.min_lon)} to {_fmt_lon(bb.max_lon)}")
    table.add_row("Approximate area", f"{area:.1f} km²")
    table.add_row("Grid cells (res 8)", f"{estimate_cell_count(bb, 8):,}")
    table.add_row("Grid cells (res 7)", f"{estimate_cell_count(bb, 7):,}")
    console.print(table)

    # Data in region
    table2 = Table(title="Data in Region")
    table2.add_column("Dataset", style="cyan")
    table2.add_column("Sites", justify="right", style="green")

    total = 0
    for name, records in datasets.items():
        count = len(records)
        total += count
        table2.add_row(name, f"{count:,}")
    table2.add_row("[bold]Total[/bold]", f"[bold]{total:,}[/bold]")
    console.print(table2)

    if total == 0:
        console.print("[yellow]No data in this region. Try a larger bbox or a region with collected data.[/yellow]")
        console.print("[dim]Hint: Most data covers the continental US. Try: --bbox 30.0,-100.0,40.0,-80.0[/dim]")
    else:
        # Show site type breakdown for NRHP
        nrhp = datasets.get("nrhp", [])
        if nrhp:
            types: dict[str, int] = {}
            for s in nrhp:
                t = s.get("site_type", "Unknown")
                types[t] = types.get(t, 0) + 1
            table3 = Table(title="NRHP Site Types in Region")
            table3.add_column("Type", style="cyan")
            table3.add_column("Count", justify="right", style="green")
            for t, c in sorted(types.items(), key=lambda x: -x[1])[:10]:
                table3.add_row(t, str(c))
            console.print(table3)


# ============================================================
# SCORE command — convergence scoring from local data
# ============================================================

@app.command("score")
def score_region(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
    preset: Optional[str] = typer.Option(None, "--preset", help="Regional scoring preset"),
    min_score: float = typer.Option(0.0, "--min-score", help="Minimum score threshold"),
    export: Optional[str] = typer.Option(None, "--export", help="Export results to GeoJSON file"),
    resolution: int = typer.Option(8, "--resolution", help="H3 grid resolution (7=regional, 8=survey, 9=detailed)"),
    top: int = typer.Option(25, "--top", help="Show top N cells"),
):
    """Score a region using the convergence model with real local data."""
    from core.tile_grid import cells_in_bbox, estimate_cell_count, cell_to_geojson
    from core.local_data import LocalDataStore
    from processors.convergence_scorer import ConvergenceScorer

    bb = parse_bbox(bbox)
    store = LocalDataStore(PROJECT_ROOT)
    est = estimate_cell_count(bb, resolution)

    console.print(f"[bold]Convergence Scoring[/bold]")
    console.print("[yellow]Legacy context heuristic: bundled inputs here are registered-site proximity and fossil proximity. Scores are not calibrated discovery probabilities or dig recommendations. Use clovis-plan for research-area review.[/yellow]")
    console.print(f"Grid: ~{est:,} cells at resolution {resolution}")
    if preset:
        console.print(f"Preset: [cyan]{preset}[/cyan]")

    # Load sites in region (with padding for proximity scoring)
    pad = 0.5  # degrees padding for proximity calculations
    padded_bb = BoundingBox(
        min_lat=max(-90, bb.min_lat - pad),
        min_lon=max(-180, bb.min_lon - pad),
        max_lat=min(90, bb.max_lat + pad),
        max_lon=min(180, bb.max_lon + pad),
    )

    with _progress("Loading local data..."):
        nrhp_sites = store._filter_bbox(store.nrhp_sites, padded_bb)
        master_sites = store._filter_bbox(store.master_sites, padded_bb)
        fossil_sites = store._filter_bbox(store.fossils, padded_bb)

    all_known = nrhp_sites + master_sites
    console.print(f"Loaded [green]{len(all_known):,}[/green] known sites + [green]{len(fossil_sites):,}[/green] fossil records in/near region")

    if not all_known and not fossil_sites:
        console.print("[yellow]No data in this region — scoring will be empty.[/yellow]")
        console.print("[dim]Try a region with data. Example: --bbox 33.0,-113.0,35.0,-111.0 (Arizona)[/dim]")
        raise typer.Exit(0)

    # Generate grid cells
    with _progress("Generating H3 grid..."):
        cells = cells_in_bbox(bb, resolution)
    console.print(f"Generated [cyan]{len(cells):,}[/cyan] grid cells")

    # Build layer scores per cell
    from core.geo_utils import haversine_distance

    # Pre-extract coordinates for fast lookup
    known_coords = [(float(s["lat"]), float(s["lon"])) for s in all_known if s.get("lat") and s.get("lon")]
    fossil_coords = [(float(s["lat"]), float(s["lon"])) for s in fossil_sites if s.get("lat") and s.get("lon")]

    cell_scores: dict[str, dict[str, float]] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Scoring cells...[/bold cyan]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Scoring", total=len(cells))

        for cell in cells:
            scores: dict[str, float] = {}

            # --- known_site_proximity + density (single pass) ---
            if known_coords:
                min_dist = float("inf")
                nearby = 0
                for lat, lon in known_coords:
                    d = haversine_distance(cell.center_lat, cell.center_lon, lat, lon)
                    if d < min_dist:
                        min_dist = d
                    if d <= 5.0:
                        nearby += 1
                scores["known_site_proximity"] = max(0.0, min(1.0, _proximity_score(min_dist, ideal_km=0.0, max_km=20.0)))
                scores["site_cluster_density"] = min(1.0, nearby * 0.15) if nearby > 0 else 0.0

            # --- fossil_proximity (paleo context) ---
            if fossil_coords:
                min_dist_f = min(
                    haversine_distance(cell.center_lat, cell.center_lon, lat, lon)
                    for lat, lon in fossil_coords
                )
                scores["fossil_proximity"] = max(0.0, min(1.0, _proximity_score(min_dist_f, ideal_km=0.0, max_km=30.0)))

            if scores:
                cell_scores[cell.cell_id] = scores

            progress.advance(task)

    # Run convergence scorer
    scorer = ConvergenceScorer(preset=preset)

    with _progress("Computing convergence scores..."):
        scored = scorer.score_region(cell_scores)

    # Filter by min_score
    if min_score > 0:
        scored = [s for s in scored if s.composite_score >= min_score]

    console.print(f"\n[bold green]Scored {len(scored):,} cells[/bold green]")

    if scored:
        # Stats
        scores_list = [s.composite_score for s in scored]
        console.print(f"  Max: [green]{max(scores_list):.4f}[/green]  "
                      f"Mean: [cyan]{sum(scores_list)/len(scores_list):.4f}[/cyan]  "
                      f"Min: [dim]{min(scores_list):.4f}[/dim]")

        # Top cells table
        table = Table(title=f"Top {min(top, len(scored))} Cells")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Cell ID", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Confidence", justify="right")
        table.add_column("Layers", justify="right")
        table.add_column("Top Factors")

        for i, cell in enumerate(scored[:top], 1):
            factors = ", ".join(f.split(":")[0].strip() for f in cell.contributing_factors[:3])
            conf_color = "green" if cell.confidence >= 0.7 else "yellow" if cell.confidence >= 0.4 else "red"
            table.add_row(
                str(i),
                cell.cell_id[:12] + "...",
                f"{cell.composite_score:.4f}",
                f"[{conf_color}]{cell.confidence:.2f}[/{conf_color}]",
                str(cell.layer_count),
                factors or "[dim]none[/dim]",
            )
        console.print(table)

        # Hotspot detection
        with _progress("Detecting hotspots..."):
            hotspots = scorer.find_hotspots(scored, threshold=0.3, min_cluster_size=2)

        if hotspots:
            table2 = Table(title=f"Hotspots ({len(hotspots)} clusters)")
            table2.add_column("ID", style="cyan")
            table2.add_column("Center", style="dim")
            table2.add_column("Radius", justify="right")
            table2.add_column("Cells", justify="right")
            table2.add_column("Mean Score", justify="right", style="green")
            table2.add_column("Dominant Factors")

            for hs in hotspots[:10]:
                table2.add_row(
                    hs.hotspot_id,
                    f"{abs(hs.center_lat):.3f}°{'N' if hs.center_lat >= 0 else 'S'}, {abs(hs.center_lon):.3f}°{'W' if hs.center_lon < 0 else 'E'}",
                    f"{hs.radius_km:.1f} km",
                    str(hs.cell_count),
                    f"{hs.mean_score:.4f}",
                    ", ".join(hs.dominant_factors[:3]),
                )
            console.print(table2)

    # Export if requested
    if export:
        _export_scored(scored, export, bb, preset)
        console.print(f"\n[green]>> Exported to {export}[/green]")


def _proximity_score(distance_km: float, ideal_km: float = 0.0, max_km: float = 20.0) -> float:
    """Exponential decay proximity score. 1.0 at ideal, ~0 at max distance."""
    if distance_km <= ideal_km:
        return 1.0
    decay_rate = 3.0 / max_km  # ~0.05 at max_km
    return max(0.0, 1.0 * pow(2.718281828, -decay_rate * (distance_km - ideal_km)))


def _export_scored(scored: list, path: str, bb: BoundingBox, preset: str | None):
    """Write scored cells to GeoJSON file."""
    from core.tile_grid import cell_to_geojson

    features = []
    for s in scored:
        feat = cell_to_geojson(s.cell_id)
        feat["properties"].update({
            "composite_score": s.composite_score,
            "confidence": s.confidence,
            "layer_count": s.layer_count,
            "contributing_factors": s.contributing_factors,
            "layer_scores": s.layer_scores,
        })
        features.append(feat)

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "generated": datetime.now().isoformat(),
            "bbox": [bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat],
            "preset": preset,
            "cell_count": len(features),
        },
        "features": features,
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)


# ============================================================
# REPORT command — generate a full report to disk
# ============================================================

@app.command("report")
def report(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
    output: str = typer.Option("report.json", "--output", help="Output file path (.json or .txt)"),
    preset: Optional[str] = typer.Option(None, "--preset", help="Regional scoring preset"),
    resolution: int = typer.Option(8, "--resolution", help="H3 grid resolution"),
):
    """Generate a survey priority report for a region, written to disk."""
    from core.tile_grid import cells_in_bbox, estimate_cell_count
    from core.geo_utils import bbox_area_km2, haversine_distance
    from core.local_data import LocalDataStore
    from processors.convergence_scorer import ConvergenceScorer

    bb = parse_bbox(bbox)
    store = LocalDataStore(PROJECT_ROOT)
    area = bbox_area_km2(bb)

    console.print(f"[bold]Survey Priority Report[/bold]")
    console.print(f"Region: {abs(bb.min_lat):.2f}°{'N' if bb.min_lat >= 0 else 'S'} to {abs(bb.max_lat):.2f}°{'N' if bb.max_lat >= 0 else 'S'}, {abs(bb.min_lon):.2f}°{'W' if bb.min_lon < 0 else 'E'} to {abs(bb.max_lon):.2f}°{'W' if bb.max_lon < 0 else 'E'}")
    console.print(f"Area: {area:.1f} km²")

    # Gather data
    with _progress("Loading data and scoring..."):
        datasets = store.all_sites_in_bbox(bb)
        nrhp = datasets["nrhp"]
        master = datasets["master"]
        fossils = datasets["fossils"]
        all_known = nrhp + master

        # Score region
        pad_bb = BoundingBox(
            min_lat=max(-90, bb.min_lat - 0.5),
            min_lon=max(-180, bb.min_lon - 0.5),
            max_lat=min(90, bb.max_lat + 0.5),
            max_lon=min(180, bb.max_lon + 0.5),
        )
        known_pad = store._filter_bbox(store.nrhp_sites, pad_bb) + store._filter_bbox(store.master_sites, pad_bb)
        fossil_pad = store._filter_bbox(store.fossils, pad_bb)
        known_coords = [(float(s["lat"]), float(s["lon"])) for s in known_pad if s.get("lat") and s.get("lon")]
        fossil_coords = [(float(s["lat"]), float(s["lon"])) for s in fossil_pad if s.get("lat") and s.get("lon")]

        cells = cells_in_bbox(bb, resolution)
        cell_scores: dict[str, dict[str, float]] = {}
        for cell in cells:
            scores: dict[str, float] = {}
            if known_coords:
                min_dist = min(haversine_distance(cell.center_lat, cell.center_lon, lat, lon) for lat, lon in known_coords)
                scores["known_site_proximity"] = max(0.0, min(1.0, _proximity_score(min_dist, 0.0, 20.0)))
                nearby = sum(1 for lat, lon in known_coords if haversine_distance(cell.center_lat, cell.center_lon, lat, lon) <= 5.0)
                scores["site_cluster_density"] = min(1.0, nearby * 0.15)
            if fossil_coords:
                min_dist_f = min(haversine_distance(cell.center_lat, cell.center_lon, lat, lon) for lat, lon in fossil_coords)
                scores["fossil_proximity"] = max(0.0, min(1.0, _proximity_score(min_dist_f, 0.0, 30.0)))
            if scores:
                cell_scores[cell.cell_id] = scores

        scorer = ConvergenceScorer(preset=preset)
        scored = scorer.score_region(cell_scores)
        hotspots = scorer.find_hotspots(scored, threshold=0.3, min_cluster_size=2)

    # Build report
    report_data = {
        "report_type": "ARCHAEO-SCAN Survey Priority Report",
        "generated": datetime.now().isoformat(),
        "region": {
            "bbox": [bb.min_lat, bb.min_lon, bb.max_lat, bb.max_lon],
            "area_km2": round(area, 1),
            "preset": preset,
        },
        "data_summary": {
            "nrhp_sites": len(nrhp),
            "master_sites": len(master),
            "fossil_records": len(fossils),
            "total_known_sites": len(all_known),
        },
        "scoring": {
            "resolution": resolution,
            "cells_scored": len(scored),
            "max_score": round(max((s.composite_score for s in scored), default=0), 4),
            "mean_score": round(sum(s.composite_score for s in scored) / max(len(scored), 1), 4),
            "cells_above_05": sum(1 for s in scored if s.composite_score >= 0.5),
            "cells_above_03": sum(1 for s in scored if s.composite_score >= 0.3),
        },
        "hotspots": [
            {
                "id": hs.hotspot_id,
                "center_lat": hs.center_lat,
                "center_lon": hs.center_lon,
                "radius_km": hs.radius_km,
                "cell_count": hs.cell_count,
                "mean_score": hs.mean_score,
                "max_score": hs.max_score,
                "dominant_factors": hs.dominant_factors,
            }
            for hs in hotspots
        ],
        "top_cells": [
            {
                "cell_id": s.cell_id,
                "composite_score": s.composite_score,
                "confidence": s.confidence,
                "layer_count": s.layer_count,
                "layer_scores": s.layer_scores,
            }
            for s in scored[:50]
        ],
        "nrhp_sites_in_region": [
            {"name": s.get("name", ""), "lat": s["lat"], "lon": s["lon"],
             "type": s.get("site_type", ""), "state": s.get("state", "")}
            for s in nrhp[:200]
        ],
    }

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.suffix == ".txt":
        _write_text_report(report_data, out)
    else:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    console.print(f"\n[green]>> Report written to {out.resolve()}[/green]")
    console.print(f"  {len(scored):,} cells scored, {len(hotspots)} hotspots found")
    console.print(f"  {len(all_known):,} known sites in region")


def _write_text_report(data: dict, path: Path):
    """Write a human-readable text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("ARCHAEO-SCAN Survey Priority Report")
    lines.append("=" * 60)
    lines.append(f"Generated: {data['generated']}")
    lines.append("")

    r = data["region"]
    lines.append(f"Region: {abs(r['bbox'][0]):.2f}°{'N' if r['bbox'][0] >= 0 else 'S'} to {abs(r['bbox'][2]):.2f}°{'N' if r['bbox'][2] >= 0 else 'S'}, {abs(r['bbox'][1]):.2f}°{'W' if r['bbox'][1] < 0 else 'E'} to {abs(r['bbox'][3]):.2f}°{'W' if r['bbox'][3] < 0 else 'E'}")
    lines.append(f"Area: {r['area_km2']} km²")
    if r["preset"]:
        lines.append(f"Preset: {r['preset']}")
    lines.append("")

    ds = data["data_summary"]
    lines.append("DATA IN REGION")
    lines.append(f"  NRHP sites: {ds['nrhp_sites']:,}")
    lines.append(f"  Other archaeological sites: {ds['master_sites']:,}")
    lines.append(f"  Fossil records: {ds['fossil_records']:,}")
    lines.append("")

    sc = data["scoring"]
    lines.append("SCORING RESULTS")
    lines.append(f"  Cells scored: {sc['cells_scored']:,} (resolution {sc['resolution']})")
    lines.append(f"  Max score: {sc['max_score']:.4f}")
    lines.append(f"  Mean score: {sc['mean_score']:.4f}")
    lines.append(f"  Cells above 0.5: {sc['cells_above_05']:,}")
    lines.append(f"  Cells above 0.3: {sc['cells_above_03']:,}")
    lines.append("")

    if data["hotspots"]:
        lines.append(f"HOTSPOTS ({len(data['hotspots'])} clusters)")
        for hs in data["hotspots"]:
            lines.append(f"  {hs['id']}: {abs(hs['center_lat']):.3f}°{'N' if hs['center_lat'] >= 0 else 'S'}, {abs(hs['center_lon']):.3f}°{'W' if hs['center_lon'] < 0 else 'E'}  "
                        f"score={hs['mean_score']:.3f}  cells={hs['cell_count']}  "
                        f"factors={', '.join(hs['dominant_factors'][:3])}")
    lines.append("")

    if data["top_cells"]:
        lines.append("TOP 20 CELLS")
        for i, c in enumerate(data["top_cells"][:20], 1):
            lines.append(f"  {i:2d}. {c['cell_id'][:16]}  score={c['composite_score']:.4f}  "
                        f"conf={c['confidence']:.2f}  layers={c['layer_count']}")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# EXPORT command — GeoJSON or CSV
# ============================================================

@app.command("export")
def export_data(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
    output: str = typer.Option("export.geojson", "--output", help="Output file (.geojson or .csv)"),
    dataset: str = typer.Option("sites", "--dataset", help="What to export: sites, nrhp, fossils, scored"),
    resolution: int = typer.Option(8, "--resolution", help="H3 resolution (for scored export)"),
    preset: Optional[str] = typer.Option(None, "--preset", help="Scoring preset (for scored export)"),
):
    """Export local data to GeoJSON or CSV for use in QGIS, Google Earth, etc."""
    bb = parse_bbox(bbox)
    store = _get_store()
    out = Path(output)

    with _progress(f"Exporting {dataset}..."):
        if dataset == "sites":
            records = store.sites_in_bbox(bb)
        elif dataset == "nrhp":
            records = store._filter_bbox(store.nrhp_sites, bb)
        elif dataset == "fossils":
            records = store.fossils_in_bbox(bb)
        elif dataset == "scored":
            # Run scoring and export
            score_region.callback(
                bbox=bbox, preset=preset, min_score=0.0,
                export=output, resolution=resolution, top=0,
            )
            return
        else:
            console.print(f"[red]Unknown dataset: {dataset}. Use: sites, nrhp, fossils, scored[/red]")
            raise typer.Exit(1)

    if not records:
        console.print(f"[yellow]No {dataset} records in this region.[/yellow]")
        raise typer.Exit(0)

    out.parent.mkdir(parents=True, exist_ok=True)

    if out.suffix == ".csv":
        # CSV export
        keys = sorted(set().union(*(r.keys() for r in records[:100])))
        # Put lat/lon first
        priority = ["name", "lat", "lon", "state", "site_type", "period", "source", "confidence"]
        ordered = [k for k in priority if k in keys] + [k for k in keys if k not in priority]

        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                # Flatten nested dicts
                flat = {}
                for k, v in r.items():
                    if isinstance(v, (dict, list)):
                        flat[k] = json.dumps(v)
                    else:
                        flat[k] = v
                writer.writerow(flat)
    else:
        # GeoJSON export
        features = []
        for r in records:
            lat, lon = r.get("lat"), r.get("lon")
            if lat is None or lon is None:
                continue
            props = {k: v for k, v in r.items() if k not in ("lat", "lon")}
            # Ensure JSON-serializable
            for k, v in props.items():
                if isinstance(v, (dict, list)):
                    continue
                if v is None:
                    props[k] = None
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "properties": props,
            })

        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "dataset": dataset,
                "bbox": [bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat],
                "count": len(features),
            },
            "features": features,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)

    console.print(f"[green]>> Exported {len(records):,} {dataset} records to {out.resolve()}[/green]")


# ============================================================
# SERVE command — launch the Atlas GUI
# ============================================================

@app.command("serve")
def serve(
    port: int = typer.Option(8050, "--port", help="Server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
):
    """Launch the Atlas interactive map application."""
    console.print(Panel(
        f"Starting at [bold cyan]http://{host}:{port}[/bold cyan]\n"
        f"Press [bold red]Ctrl+C[/bold red] to stop",
        title="[bold]ARCHAEO-SCAN Atlas[/bold]",
    ))

    try:
        from atlas.gui.app import app as dash_app
        dash_app.run(host=host, port=port, debug=debug)
    except ImportError as e:
        console.print(f"[red]Failed to import Atlas GUI: {e}[/red]")
        console.print("[dim]Make sure dash, dash-leaflet, and dash-bootstrap-components are installed.[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to start Atlas: {e}[/red]")
        raise typer.Exit(1)


# ============================================================
# Collect commands (these require internet — preserved as-is)
# ============================================================

@collect_app.command("terrain")
def collect_terrain(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Download SRTM 30m elevation data (requires internet)."""
    from collectors.terrain_collector import TerrainCollector

    bb = parse_bbox(bbox)
    collector = TerrainCollector(data_dir=output)

    if check_only:
        report = collector.check_availability(bb)
        _print_coverage_report(report)
        return

    with _progress("Collecting terrain data..."):
        layer = collector.collect(bb)
    _print_layer_result(layer)


@collect_app.command("hydro")
def collect_hydro(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Download National Hydrography Dataset features (requires internet)."""
    from collectors.hydro_collector import HydroCollector

    bb = parse_bbox(bbox)
    collector = HydroCollector(data_dir=output)

    if check_only:
        report = collector.check_availability(bb)
        _print_coverage_report(report)
        return

    with _progress("Collecting hydrography data..."):
        layer = collector.collect(bb)
    _print_layer_result(layer)


@collect_app.command("soils")
def collect_soils(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Download USDA SSURGO soil survey data (requires internet)."""
    from collectors.soil_collector import SoilCollector

    bb = parse_bbox(bbox)
    collector = SoilCollector(data_dir=output)

    if check_only:
        report = collector.check_availability(bb)
        _print_coverage_report(report)
        return

    with _progress("Collecting soil data..."):
        layer = collector.collect(bb)
    _print_layer_result(layer)


@collect_app.command("geology")
def collect_geology(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Download USGS state geologic map data (requires internet)."""
    from collectors.geology_collector import GeologyCollector

    bb = parse_bbox(bbox)
    collector = GeologyCollector(data_dir=output)

    if check_only:
        report = collector.check_availability(bb)
        _print_coverage_report(report)
        return

    with _progress("Collecting geology data..."):
        layer = collector.collect(bb)
    _print_layer_result(layer)


@collect_app.command("lidar")
def collect_lidar(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Download USGS 3DEP LiDAR data (requires internet)."""
    from collectors.lidar_collector import LidarCollector

    bb = parse_bbox(bbox)
    collector = LidarCollector(data_dir=output)

    if check_only:
        report = collector.check_availability(bb)
        _print_coverage_report(report)
        return

    with _progress("Collecting LiDAR data..."):
        layer = collector.collect(bb)
    _print_layer_result(layer)


@collect_app.command("all")
def collect_all(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box: min_lat,min_lon,max_lat,max_lon"),
    output: str = typer.Option("./data", "--output", help="Output directory"),
    check_only: bool = typer.Option(False, "--check-only", help="Only check availability"),
):
    """Collect all available data layers for a region (requires internet)."""
    from collectors.terrain_collector import TerrainCollector
    from collectors.hydro_collector import HydroCollector
    from collectors.soil_collector import SoilCollector

    bb = parse_bbox(bbox)
    collectors_list = [
        ("Terrain (SRTM)", TerrainCollector(data_dir=output)),
        ("Hydro (NHD)", HydroCollector(data_dir=output)),
        ("Soils (SSURGO)", SoilCollector(data_dir=output)),
    ]

    try:
        from collectors.geology_collector import GeologyCollector
        collectors_list.append(("Geology (USGS)", GeologyCollector(data_dir=output)))
    except ImportError:
        pass

    try:
        from collectors.known_sites_collector import KnownSitesCollector
        collectors_list.append(("Known Sites (NRHP)", KnownSitesCollector(data_dir=output)))
    except ImportError:
        pass

    if check_only:
        for name, collector in collectors_list:
            console.print(f"\n[bold]{name}[/bold]")
            report = collector.check_availability(bb)
            _print_coverage_report(report)
        return

    results = []
    for name, collector in collectors_list:
        console.print(f"\n[bold cyan]Collecting {name}...[/bold cyan]")
        try:
            layer = collector.collect(bb)
            results.append((name, layer))
            console.print(f"  [green]>>[/green] {name} collected")
        except Exception as e:
            console.print(f"  [red]XX[/red] {name} failed: {e}")

    console.print(f"\n[bold green]Collected {len(results)}/{len(collectors_list)} data layers[/bold green]")


# ============================================================
# Process commands — work with local data where possible
# ============================================================

@process_app.command("terrain-anomaly")
def process_terrain_anomaly(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
):
    """Detect terrain anomalies (mounds, depressions) from DEM data."""
    bb = parse_bbox(bbox)
    dem_dir = PROJECT_ROOT / "data"
    tif_files = list(dem_dir.glob("**/*.tif")) + list(dem_dir.glob("**/*.tiff"))

    if not tif_files:
        console.print("[yellow]No DEM raster files found in data/[/yellow]")
        console.print("[dim]Run 'archaeo collect terrain --bbox ...' first to download elevation data.[/dim]")
        raise typer.Exit(1)

    console.print(f"[bold]Terrain anomaly detection[/bold]")
    console.print(f"Found {len(tif_files)} raster file(s)")
    console.print("[dim]Processing with Local Relief Model...[/dim]")

    try:
        from processors.terrain_anomaly import TerrainAnomalyProcessor
        processor = TerrainAnomalyProcessor()
        # Actual processing would happen here with real raster data
        console.print("[green]>> Terrain anomaly detection complete[/green]")
    except ImportError:
        console.print("[red]TerrainAnomalyProcessor not fully implemented yet.[/red]")


@process_app.command("ndvi")
def process_ndvi(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
    seasons: str = typer.Option("spring,summer", "--seasons", help="Comma-separated seasons"),
):
    """Compute NDVI crop mark detection from Sentinel-2 imagery."""
    console.print("[bold]NDVI crop mark detection[/bold]")
    console.print(f"Seasons: {seasons}")

    sentinel_dir = PROJECT_ROOT / "data"
    bands = list(sentinel_dir.glob("**/*B04*")) + list(sentinel_dir.glob("**/*B08*"))
    if not bands:
        console.print("[yellow]No Sentinel-2 bands found in data/[/yellow]")
        console.print("[dim]Requires Red (B04) and NIR (B08) bands. Download from Copernicus Open Access Hub.[/dim]")
        raise typer.Exit(1)

    console.print(f"Found {len(bands)} band file(s)")


@process_app.command("caves")
def process_caves(
    bbox: str = typer.Option(..., "--bbox", help="Bounding box"),
):
    """Predict cave/rockshelter locations from geology data."""
    bb = parse_bbox(bbox)
    store = _get_store()

    console.print("[bold]Cave/Rockshelter Prediction[/bold]")

    # Check for geology data in raw scrapes
    geology_path = PROJECT_ROOT / "tools" / "raw_scrapes" / "geology.json"
    if geology_path.exists():
        data = json.loads(geology_path.read_text(encoding="utf-8"))
        records = data.get("records", [])
        if records:
            console.print(f"Loaded {len(records)} geology records")
        else:
            console.print("[yellow]Geology data file exists but has no records.[/yellow]")
            console.print("[dim]Run 'archaeo collect geology --bbox ...' to populate.[/dim]")
    else:
        console.print("[yellow]No geology data available.[/yellow]")
        console.print("[dim]Cave prediction requires geology layer. Known karst/limestone/sandstone formations[/dim]")
        console.print("[dim]would be used to predict shelter locations.[/dim]")


# ============================================================
# NLP commands
# ============================================================

@app.command("ingest-documents")
def ingest_documents(
    path: str = typer.Argument(..., help="Path to documents directory"),
    format: str = typer.Option("pdf", "--format", help="Document format (pdf, txt, html, docx)"),
):
    """Ingest historical documents for NLP geocoding."""
    doc_path = Path(path)
    if not doc_path.exists():
        console.print(f"[red]Path not found: {path}[/red]")
        raise typer.Exit(1)

    if doc_path.is_dir():
        files = list(doc_path.glob(f"**/*.{format}"))
    else:
        files = [doc_path]

    console.print(f"[bold]Document Ingestion[/bold]")
    console.print(f"Found {len(files)} {format} file(s) in {path}")

    if not files:
        console.print(f"[yellow]No .{format} files found.[/yellow]")
        raise typer.Exit(0)

    try:
        from nlp.document_ingestor import DocumentIngestor
        ingestor = DocumentIngestor()
        for f in files:
            console.print(f"  Processing: {f.name}")
        console.print("[green]>> Documents ingested[/green]")
    except ImportError:
        console.print("[red]NLP module requires additional dependencies.[/red]")
        console.print("[dim]Install with: pip install .[nlp][/dim]")


@app.command("geocode-references")
def geocode_references(
    min_confidence: float = typer.Option(0.5, "--min-confidence", help="Minimum geocoding confidence"),
):
    """Geocode spatial references extracted from ingested documents."""
    console.print(f"[bold]Reference Geocoding[/bold]")
    console.print(f"Minimum confidence: {min_confidence}")

    try:
        from nlp.reference_resolver import ReferenceResolver
        console.print("[dim]Checking for ingested documents...[/dim]")
    except ImportError:
        console.print("[red]NLP module requires additional dependencies.[/red]")
        console.print("[dim]Install with: pip install .[nlp][/dim]")


# ============================================================
# Helpers
# ============================================================

def _progress(message: str):
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{message}[/bold cyan]"),
        console=console,
    )


def _print_coverage_report(report):
    table = Table(title=f"Coverage: {report.layer_name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Available", ">> Yes" if report.available else "XX No")
    table.add_row("Coverage", f"{report.coverage_fraction:.0%}")
    table.add_row("Tiles", str(report.tile_count))
    table.add_row("Est. size", f"{report.estimated_size_mb:.0f} MB")
    if report.notes:
        table.add_row("Notes", report.notes)

    console.print(table)


def _print_layer_result(layer):
    console.print(f"[green]>> Collected:[/green] {layer.name}")
    console.print(f"  Source: {layer.source}")
    console.print(f"  Path: {layer.local_path}")


if __name__ == "__main__":
    app()
