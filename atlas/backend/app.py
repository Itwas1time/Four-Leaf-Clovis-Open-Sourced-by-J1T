"""
ARCHAEO-SCAN Atlas — FastAPI application server.

Serves the interactive map application that brings all data layers,
scores, and analysis results together into a unified research interface.

Endpoints:
    /api/layers — list available data layers
    /api/scores — query convergence scores by bbox
    /api/hotspots — identified high-priority survey areas
    /api/cells/{cell_id} — detailed cell inspection data
    /api/search — natural language spatial queries
    /api/export — export data in various formats
    /api/timeline — time period metadata for the TimeSlider
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.schemas import BoundingBox, ScoredCell
from core.data_store import DataStore
from core.tile_grid import cells_in_bbox, cell_to_geojson, estimate_cell_count
from core.web_security import configure_local_api

app = FastAPI(
    title="ARCHAEO-SCAN Atlas",
    description="Archaeological site discovery and analysis platform",
    version="0.1.0",
)

configure_local_api(app)

# Default data store path
DATA_STORE_PATH = Path("./data/archaeo_scan.gpkg")


def get_store() -> DataStore:
    return DataStore(DATA_STORE_PATH)


# ============================================================
# Request/Response models
# ============================================================

class BBoxQuery(BoundingBox):
    pass


class ScoreQuery(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    min_score: float = 0.0
    resolution: int = 8


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    bbox: Optional[BBoxQuery] = None


class CellDetail(BaseModel):
    cell_id: str
    center_lat: float
    center_lon: float
    layer_scores: dict[str, float]
    composite_score: float
    confidence: float
    contributing_factors: list[str]
    geometry: dict


class TimelineEntry(BaseModel):
    years_bp: int
    label: str
    sea_level_m: float
    ice_coverage: str
    cultural_period: str


# ============================================================
# API Endpoints
# ============================================================

def validated_bbox(min_lat, min_lon, max_lat, max_lon):
    try:
        return BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)
    except ValueError:
        raise HTTPException(status_code=422, detail="Use finite, ordered latitude/longitude bounds.")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "archaeo-scan-atlas"}


@app.get("/api/layers")
async def list_layers():
    """List all available data layers in the store."""
    try:
        store = get_store()
        layers = store.list_layers()
        return {
            "layers": [
                {
                    "name": l.name,
                    "source": l.source,
                    "format": l.format,
                    "bbox": {
                        "min_lat": l.coverage_bbox.min_lat,
                        "min_lon": l.coverage_bbox.min_lon,
                        "max_lat": l.coverage_bbox.max_lat,
                        "max_lon": l.coverage_bbox.max_lon,
                    },
                }
                for l in layers
            ],
            "count": len(layers),
        }
    except Exception:
        return {"layers": [], "count": 0}


@app.get("/api/scores")
async def get_scores(
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(1000, ge=1, le=10000),
):
    """
    Query convergence scores for a bounding box.

    Returns scored cells as a GeoJSON FeatureCollection for direct
    map rendering. Each feature includes the composite score, confidence,
    and contributing factors.
    """
    bbox = validated_bbox(min_lat, min_lon, max_lat, max_lon)
    store = get_store()
    scores = store.get_scores(bbox=bbox, min_score=min_score)

    features = []
    for score in scores[:limit]:
        geojson = cell_to_geojson(score.cell_id)
        geojson["properties"].update({
            "composite_score": score.composite_score,
            "confidence": score.confidence,
            "layer_count": score.layer_count,
            "contributing_factors": score.contributing_factors,
            "layer_scores": score.layer_scores,
        })
        features.append(geojson)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_scored": len(scores),
            "returned": len(features),
            "min_score_filter": min_score,
        },
    }


@app.get("/api/cells/{cell_id}")
async def get_cell_detail(cell_id: str):
    """
    Full detail view for a single cell — the SiteInspector panel data.

    Returns every data layer's value at this cell, composite score,
    and the specific factors driving the score.
    """
    import h3
    try:
        lat, lon = h3.cell_to_latlng(cell_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cell ID")

    store = get_store()
    scores = store.get_scores()
    cell_score = next((s for s in scores if s.cell_id == cell_id), None)

    geojson = cell_to_geojson(cell_id)

    return CellDetail(
        cell_id=cell_id,
        center_lat=lat,
        center_lon=lon,
        layer_scores=cell_score.layer_scores if cell_score else {},
        composite_score=cell_score.composite_score if cell_score else 0.0,
        confidence=cell_score.confidence if cell_score else 0.0,
        contributing_factors=cell_score.contributing_factors if cell_score else [],
        geometry=geojson["geometry"],
    )


@app.get("/api/grid")
async def get_grid(
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    resolution: int = Query(8, ge=5, le=10),
):
    """Generate H3 grid cells for a bounding box as GeoJSON."""
    bbox = validated_bbox(min_lat, min_lon, max_lat, max_lon)

    est = estimate_cell_count(bbox, resolution)
    if est > 50000:
        raise HTTPException(
            status_code=400,
            detail=f"Region too large: ~{est} cells. Reduce bbox or lower resolution.",
        )

    cells = cells_in_bbox(bbox, resolution)
    features = [cell_to_geojson(c.cell_id) for c in cells]

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "resolution": resolution,
            "cell_count": len(cells),
        },
    }


@app.get("/api/timeline")
async def get_timeline():
    """
    Return time period data for the TimeSlider component.

    This drives the "wow" feature: scrubbing through time to see
    coastlines shift, ice sheets retreat, and climate zones change.
    """
    from processors.shelf_reconstructor import ShelfReconstructor
    reconstructor = ShelfReconstructor()

    periods = [
        TimelineEntry(
            years_bp=25000, label="Pre-LGM",
            sea_level_m=reconstructor.sea_level_at(25000),
            ice_coverage="Laurentide and Cordilleran sheets growing",
            cultural_period="Pre-human (contested)",
        ),
        TimelineEntry(
            years_bp=20000, label="Last Glacial Maximum",
            sea_level_m=reconstructor.sea_level_at(20000),
            ice_coverage="Maximum ice extent — 2km thick over Great Lakes",
            cultural_period="Pre-Clovis (contested)",
        ),
        TimelineEntry(
            years_bp=15000, label="Deglaciation Begins",
            sea_level_m=reconstructor.sea_level_at(15000),
            ice_coverage="Ice-free corridor beginning to open",
            cultural_period="Pre-Clovis (Paisley Caves, Monte Verde)",
        ),
        TimelineEntry(
            years_bp=13500, label="Clovis Horizon",
            sea_level_m=reconstructor.sea_level_at(13500),
            ice_coverage="Rapid retreat, corridor fully open",
            cultural_period="Clovis — first widespread North American culture",
        ),
        TimelineEntry(
            years_bp=12900, label="Younger Dryas",
            sea_level_m=reconstructor.sea_level_at(12900),
            ice_coverage="Brief re-advance, cold snap",
            cultural_period="Folsom, Dalton — megafauna extinction",
        ),
        TimelineEntry(
            years_bp=10000, label="Early Holocene",
            sea_level_m=reconstructor.sea_level_at(10000),
            ice_coverage="Laurentide remnant over Hudson Bay",
            cultural_period="Early Archaic — broad adaptation",
        ),
        TimelineEntry(
            years_bp=5000, label="Mid-Holocene",
            sea_level_m=reconstructor.sea_level_at(5000),
            ice_coverage="Modern ice coverage",
            cultural_period="Late Archaic — Poverty Point, Watson Brake",
        ),
        TimelineEntry(
            years_bp=2000, label="Woodland Period",
            sea_level_m=reconstructor.sea_level_at(2000),
            ice_coverage="Modern",
            cultural_period="Hopewell, Adena — mound building intensifies",
        ),
        TimelineEntry(
            years_bp=1000, label="Mississippian",
            sea_level_m=reconstructor.sea_level_at(1000),
            ice_coverage="Modern",
            cultural_period="Cahokia, Moundville — complex chiefdoms",
        ),
        TimelineEntry(
            years_bp=500, label="Late Prehistoric / Contact",
            sea_level_m=reconstructor.sea_level_at(500),
            ice_coverage="Modern",
            cultural_period="De Soto, Coronado — European contact",
        ),
    ]

    return {"periods": [p.model_dump() for p in periods]}


@app.post("/api/search")
async def search(query: SearchQuery):
    """
    Natural language spatial query.

    Translates queries like "high-scoring caves near rivers in New Mexico"
    into spatial and attribute filters. Placeholder for LLM-powered
    query translation.
    """
    return {
        "query": query.query,
        "status": "parsed",
        "message": "Natural language search requires LLM integration (Step 6)",
        "filters": {
            "text": query.query,
            "bbox": query.bbox.model_dump() if query.bbox else None,
        },
    }


@app.get("/api/export/{format}")
async def export_data(
    format: str,
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(1000, ge=1, le=10000),
):
    """
    Export scored cells in various formats.

    Supported: geojson, csv, kml
    """
    if format not in {"geojson", "csv"}:
        raise HTTPException(status_code=400, detail="Supported export formats: geojson, csv")
    bbox = validated_bbox(min_lat, min_lon, max_lat, max_lon)
    store = get_store()
    scores = store.get_scores(bbox=bbox, min_score=min_score)[:limit]

    if format == "geojson":
        features = []
        for s in scores:
            geojson = cell_to_geojson(s.cell_id)
            geojson["properties"]["composite_score"] = s.composite_score
            geojson["properties"]["confidence"] = s.confidence
            features.append(geojson)

        return {"type": "FeatureCollection", "features": features}

    elif format == "csv":
        import h3
        rows = []
        for s in scores:
            lat, lon = h3.cell_to_latlng(s.cell_id)
            rows.append({
                "cell_id": s.cell_id,
                "lat": lat,
                "lon": lon,
                "composite_score": s.composite_score,
                "confidence": s.confidence,
                "layer_count": s.layer_count,
                "factors": "; ".join(s.contributing_factors),
            })
        return {"format": "csv", "rows": rows}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# Expose only the demo's intended assets, never package files or node_modules.
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    for asset_dir in ("src", "styles"):
        app.mount(f"/{asset_dir}", StaticFiles(directory=str(frontend_path / asset_dir)), name=asset_dir)

    @app.get("/", include_in_schema=False)
    async def frontend_index():
        return FileResponse(frontend_path / "index.html")
