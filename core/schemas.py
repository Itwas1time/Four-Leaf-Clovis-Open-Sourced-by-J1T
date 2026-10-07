"""
Pydantic data models for all ARCHAEO-SCAN data structures.

These schemas define the lingua franca of the system — every module speaks
in these types. Archaeological data is inherently multi-layered and uncertain,
so confidence scores and provenance tracking are first-class citizens.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class BoundingBox(BaseModel):
    """
    Geographic bounding box in WGS84 (EPSG:4326).

    Used to define areas of interest for collection, processing, and queries.
    All coordinates are in decimal degrees.
    """

    min_lat: float = Field(..., ge=-90, le=90, description="Southern boundary")
    min_lon: float = Field(..., ge=-180, le=180, description="Western boundary")
    max_lat: float = Field(..., ge=-90, le=90, description="Northern boundary")
    max_lon: float = Field(..., ge=-180, le=180, description="Eastern boundary")

    @model_validator(mode="after")
    def validate_bounds(self) -> BoundingBox:
        if self.min_lat >= self.max_lat:
            raise ValueError(f"min_lat ({self.min_lat}) must be less than max_lat ({self.max_lat})")
        if self.min_lon >= self.max_lon:
            raise ValueError(f"min_lon ({self.min_lon}) must be less than max_lon ({self.max_lon})")
        return self

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2

    @property
    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return as (min_lon, min_lat, max_lon, max_lat) — standard GIS order."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def contains_point(self, lat: float, lon: float) -> bool:
        return (self.min_lat <= lat <= self.max_lat and
                self.min_lon <= lon <= self.max_lon)

    def intersects(self, other: BoundingBox) -> bool:
        return not (self.max_lat < other.min_lat or
                    self.min_lat > other.max_lat or
                    self.max_lon < other.min_lon or
                    self.min_lon > other.max_lon)

    def intersection(self, other: BoundingBox) -> BoundingBox | None:
        if not self.intersects(other):
            return None
        return BoundingBox(
            min_lat=max(self.min_lat, other.min_lat),
            min_lon=max(self.min_lon, other.min_lon),
            max_lat=min(self.max_lat, other.max_lat),
            max_lon=min(self.max_lon, other.max_lon),
        )

    def union(self, other: BoundingBox) -> BoundingBox:
        return BoundingBox(
            min_lat=min(self.min_lat, other.min_lat),
            min_lon=min(self.min_lon, other.min_lon),
            max_lat=max(self.max_lat, other.max_lat),
            max_lon=max(self.max_lon, other.max_lon),
        )


class GridCell(BaseModel):
    """
    A single spatial analysis cell, addressed by H3 hexagonal index.

    H3 hexagons tessellate uniformly (unlike square grids) which eliminates
    edge-effect bias in spatial analysis. Resolution 8 ≈ 0.74 km² is the
    default — roughly the area a field surveyor covers in a day.
    """

    cell_id: str = Field(..., description="H3 hexagonal cell index")
    resolution: int = Field(..., ge=0, le=15, description="H3 resolution level")
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    area_km2: float = Field(..., gt=0, description="Cell area in square kilometers")

    @field_validator("cell_id")
    @classmethod
    def validate_h3_format(cls, v: str) -> str:
        if not v or len(v) < 15:
            raise ValueError(f"Invalid H3 index: {v}")
        return v


class DataLayer(BaseModel):
    """
    Metadata for a collected or processed data layer.

    Every piece of data in the system is tracked as a layer with full
    provenance — what it is, where it came from, when it was collected,
    and what it covers. This is critical for reproducibility and for
    the convergence scorer to know what evidence is available.
    """

    name: str = Field(..., description="Layer identifier (e.g., 'terrain_dem', 'hydro_nhd')")
    source: str = Field(..., description="Data source (e.g., 'USGS 3DEP', 'USDA SSURGO')")
    source_url: str = Field(default="", description="API endpoint or download URL")
    license: str = Field(default="", description="Data license and attribution")
    timestamp: datetime = Field(default_factory=datetime.now, description="Collection timestamp")
    coverage_bbox: BoundingBox = Field(..., description="Spatial extent of this layer")
    local_path: Path = Field(..., description="Path to stored data file")
    format: str = Field(default="gpkg", description="File format (gpkg, tif, geojson, etc.)")
    crs: str = Field(default="EPSG:4326", description="Coordinate reference system")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional source-specific metadata")


class ScoredCell(BaseModel):
    """
    A grid cell with computed archaeological potential score.

    The composite score represents CONVERGENCE — the degree to which
    multiple independent environmental and cultural signals align to
    suggest human habitation. A score driven by 5 independent factors
    is far more meaningful than one driven by a single strong signal.
    """

    cell_id: str = Field(..., description="H3 cell index")
    layer_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Individual score per layer (0.0-1.0 each)"
    )
    composite_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Weighted composite convergence score"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence based on number and quality of contributing layers"
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Human-readable list of factors driving the score"
    )
    layer_count: int = Field(
        default=0,
        description="Number of layers that contributed to this score"
    )

    @model_validator(mode="after")
    def set_layer_count(self) -> ScoredCell:
        if self.layer_count == 0:
            self.layer_count = len(self.layer_scores)
        return self


class TimePeriod(str, Enum):
    """Major archaeological time periods in North America."""
    PRE_CLOVIS = "pre_clovis"          # >13,500 BP
    PALEOINDIAN = "paleoindian"        # 13,500-10,000 BP
    EARLY_ARCHAIC = "early_archaic"    # 10,000-8,000 BP
    MIDDLE_ARCHAIC = "middle_archaic"  # 8,000-5,000 BP
    LATE_ARCHAIC = "late_archaic"      # 5,000-3,000 BP
    EARLY_WOODLAND = "early_woodland"  # 3,000-2,000 BP
    MIDDLE_WOODLAND = "middle_woodland"  # 2,000-1,200 BP
    LATE_WOODLAND = "late_woodland"    # 1,200-1,000 BP
    MISSISSIPPIAN = "mississippian"    # 1,000-500 BP
    PROTOHISTORIC = "protohistoric"    # 500-250 BP
    HISTORIC = "historic"             # 250 BP-present


class ShelterType(str, Enum):
    """Types of natural shelters relevant to archaeology."""
    CAVE_KARST = "cave_karst"
    ROCKSHELTER_SANDSTONE = "rockshelter_sandstone"
    LAVA_TUBE = "lava_tube"
    OVERHANG = "overhang"


class AnomalyType(str, Enum):
    """Types of terrain anomalies that may indicate human activity."""
    MOUND = "mound"
    DEPRESSION = "depression"
    LINEAR_RAISED = "linear_raised"
    LINEAR_DEPRESSION = "linear_depression"
    PLATFORM_TERRACE = "platform_terrace"
    ENCLOSURE = "enclosure"


class ArtifactClass(str, Enum):
    """Preliminary artifact classification categories."""
    LITHIC_PROJECTILE = "lithic_projectile"
    LITHIC_SCRAPER = "lithic_scraper"
    LITHIC_CORE = "lithic_core"
    LITHIC_DEBITAGE = "lithic_debitage"
    LITHIC_GROUND_STONE = "lithic_ground_stone"
    CERAMIC = "ceramic"
    HISTORIC_METAL = "historic_metal"
    HISTORIC_GLASS = "historic_glass"
    HISTORIC_CERAMIC = "historic_ceramic"
    NATURAL = "natural"
    UNCERTAIN = "uncertain"


class HistoricalReference(BaseModel):
    """
    A spatial reference extracted from a historical document.

    Historical texts — expedition journals, ethnographies, early surveys —
    contain irreplaceable firsthand descriptions of sites that may since
    have been destroyed, buried, or forgotten. Geocoding these references
    creates a knowledge layer that no satellite can replicate.
    """

    source_document: str = Field(..., description="Document identifier or title")
    author: str = Field(default="", description="Document author")
    document_date: str = Field(default="", description="Date of the document or observation")
    extracted_text: str = Field(..., description="Relevant passage from the source")
    resolved_lat: float | None = Field(default=None, ge=-90, le=90)
    resolved_lon: float | None = Field(default=None, ge=-180, le=180)
    resolution_method: str = Field(
        default="",
        description="How the location was resolved (gazetteer, relative, feature-match)"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence in the geocoded location"
    )
    time_period: TimePeriod | None = Field(default=None)
    described_features: list[str] = Field(
        default_factory=list,
        description="Features mentioned: 'mound', 'village', 'stone walls', etc."
    )


class CitizenReport(BaseModel):
    """
    A field report from a citizen scientist.

    Citizen reports are noisy but invaluable — they represent ground truth
    that no remote sensing can provide. Clustering of reports indicates
    areas where erosion or disturbance is exposing material, which is
    itself archaeologically informative.
    """

    report_id: str = Field(default="", description="Unique report identifier")
    reporter_id: str = Field(..., description="Anonymous reporter identifier")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    photos: list[str] = Field(default_factory=list, description="Paths to uploaded photos")
    description: str = Field(default="", description="Reporter's description of the find")
    preliminary_classification: ArtifactClass = Field(default=ArtifactClass.UNCERTAIN)
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context: surface/eroded/plowed, nearby landmarks, etc."
    )


class CoverageReport(BaseModel):
    """Report on data availability for a region, returned by collector.check_availability()."""

    layer_name: str
    bbox: BoundingBox
    available: bool = Field(default=False, description="Whether any data exists for this area")
    coverage_fraction: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Fraction of the bbox covered by available data"
    )
    tile_count: int = Field(default=0, description="Number of data tiles available")
    estimated_size_mb: float = Field(default=0.0, description="Estimated download size in MB")
    notes: str = Field(default="", description="Coverage gaps, quality notes")


class Hotspot(BaseModel):
    """A spatial cluster of high-scoring cells or citizen reports."""

    hotspot_id: str
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(..., gt=0)
    mean_score: float = Field(..., ge=0.0, le=1.0)
    max_score: float = Field(..., ge=0.0, le=1.0)
    cell_count: int = Field(..., gt=0)
    dominant_factors: list[str] = Field(default_factory=list)
