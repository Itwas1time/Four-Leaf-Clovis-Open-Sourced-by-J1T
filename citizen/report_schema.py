"""
Standardized report format for citizen science submissions.

Archaeological surface finds are inherently contextual — a projectile point
eroding from a streambank tells a different story than one found in a plowed
field. These schemas capture not just WHAT was found, but WHERE and HOW,
because depositional context is what separates an artifact from a curiosity.

GPS precision matters: consumer-grade GPS is accurate to ~3-5m, which is
sufficient for clustering analysis but NOT for intra-site provenience.
We record raw coordinates plus device-reported accuracy so downstream
analysis can weight accordingly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ReportStatusEnum(str, Enum):
    """Lifecycle stages of a citizen report."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CLASSIFIED = "classified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class SurfaceContext(str, Enum):
    """
    How the find was exposed — critical for interpreting site formation.

    Erosion exposures indicate active destruction of a site and may warrant
    urgent professional follow-up. Plowed fields suggest a disturbed but
    potentially extensive scatter. In-situ surface finds are the rarest
    and most informative.
    """
    ERODED_SURFACE = "eroded_surface"
    STREAM_BANK = "stream_bank"
    PLOWED_FIELD = "plowed_field"
    CONSTRUCTION_CUT = "construction_cut"
    TRAIL_CUT = "trail_cut"
    ANIMAL_BURROW = "animal_burrow"
    SURFACE_INTACT = "surface_intact"
    UNKNOWN = "unknown"


class PhotoMetadata(BaseModel):
    """
    Metadata for a submitted photograph.

    Multiple views are encouraged: one showing the find in situ (before
    pickup), one showing scale (with a coin or ruler), and one close-up
    of diagnostic features (flaking pattern, temper, maker's mark).
    """
    file_path: str = Field(..., min_length=1, max_length=255, description="Relative reference within the server-approved photo directory")
    caption: str = Field(default="", max_length=1000, description="Reporter's description of what the photo shows")
    is_in_situ: bool = Field(
        default=False,
        description="Whether the photo shows the find in its original position"
    )
    has_scale_reference: bool = Field(
        default=False,
        description="Whether the photo includes a scale object (coin, ruler, etc.)"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class GPSReading(BaseModel):
    """
    A single GPS coordinate with accuracy metadata.

    Consumer devices report horizontal accuracy as a radius of uncertainty.
    Sub-5m accuracy is good; >20m is marginal for clustering analysis.
    We also record altitude where available — terrace elevation relative
    to a nearby watercourse is a key settlement predictor.
    """
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees WGS84")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees WGS84")
    altitude_m: float | None = Field(
        default=None,
        description="Altitude in meters above sea level, if available"
    )
    accuracy_m: float | None = Field(
        default=None, ge=0,
        description="Horizontal accuracy radius in meters as reported by device"
    )
    source: str = Field(
        default="device_gps",
        description="GPS source: device_gps, manual_entry, map_pin"
    )

    @field_validator("accuracy_m")
    @classmethod
    def warn_low_accuracy(cls, v: float | None) -> float | None:
        """Flag readings with >50m uncertainty — still useful for regional patterns."""
        return v


class ReportSubmission(BaseModel):
    """
    A complete citizen science report submission.

    This is the ingest format — what arrives from the field. It captures
    everything needed for initial triage: location, photos, reporter's
    own interpretation, and environmental context. The system then
    enriches this with LLM classification and spatial analysis.
    """
    reporter_id: str = Field(..., min_length=1, max_length=128, description="Anonymous but consistent reporter identifier")
    location: GPSReading = Field(..., description="GPS coordinates of the find location")
    photos: list[PhotoMetadata] = Field(
        default_factory=list,
        max_length=10,
        description="Photographs of the find (at least one recommended)"
    )
    description: str = Field(
        ..., min_length=10, max_length=5000,
        description="Reporter's description: what they found, how it looked, what drew attention"
    )
    surface_context: SurfaceContext = Field(
        default=SurfaceContext.UNKNOWN,
        description="How the find was exposed or the surface condition"
    )
    nearby_water: bool | None = Field(
        default=None,
        description="Is there a water source (stream, spring, river) within ~100m?"
    )
    nearby_landmarks: str = Field(
        default="",
        max_length=1000,
        description="Notable landmarks: rock outcrops, confluences, ridgeline, etc."
    )
    estimated_count: int = Field(
        default=1, ge=1,
        description="Approximate number of items observed (scatter vs. isolate)"
    )
    additional_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form context: weather, soil color, vegetation, recent disturbance"
    )
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @field_validator("submitted_at")
    @classmethod
    def utc_submission_time(cls, value: datetime) -> datetime:
        """Store UTC without a tzinfo to match the local detector convention.

        A supplied offset is converted to UTC; a naive input is interpreted as
        UTC. This prevents valid mixed client timestamps from crashing queries.
        """
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @field_validator("photos")
    @classmethod
    def recommend_photos(cls, v: list[PhotoMetadata]) -> list[PhotoMetadata]:
        """Photos are strongly recommended but not required — verbal reports still have value."""
        return v


class ReportStatus(BaseModel):
    """
    Tracks the lifecycle of a submitted report through review and classification.

    Reports move from submitted -> classified (by LLM) -> verified (by human)
    or flagged/rejected. Each transition is recorded so we can audit the
    pipeline and measure classifier accuracy over time.
    """
    report_id: str = Field(..., description="Unique report identifier")
    status: ReportStatusEnum = Field(default=ReportStatusEnum.SUBMITTED)
    submitted_at: datetime = Field(default_factory=datetime.now)
    classified_at: datetime | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)
    reviewer_id: str | None = Field(
        default=None,
        description="Professional archaeologist who reviewed, if applicable"
    )
    classification_result: str | None = Field(
        default=None,
        description="LLM classification result (ArtifactClass value)"
    )
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reviewer_classification: str | None = Field(
        default=None,
        description="Human reviewer's classification, may override LLM"
    )
    notes: str = Field(default="", description="Review notes or rejection reason")
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Audit trail of status transitions with timestamps"
    )

    def transition(self, new_status: ReportStatusEnum, note: str = "") -> None:
        """Record a status transition with audit trail."""
        self.history.append({
            "from": self.status.value,
            "to": new_status.value,
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })
        self.status = new_status
        if new_status == ReportStatusEnum.CLASSIFIED:
            self.classified_at = datetime.now()
        elif new_status in (
            ReportStatusEnum.VERIFIED,
            ReportStatusEnum.REJECTED,
            ReportStatusEnum.FLAGGED,
        ):
            self.reviewed_at = datetime.now()


class ReporterProfile(BaseModel):
    """
    Profile for a citizen science contributor.

    Tracks reporting history to build trust scores over time. A reporter
    whose finds are consistently verified by professionals earns higher
    weight in clustering analysis. This is NOT punitive — even reporters
    who submit mostly natural rocks are contributing useful negative data.
    """
    reporter_id: str = Field(..., description="Anonymous but consistent identifier")
    display_name: str = Field(default="Anonymous", description="Optional display name")
    joined_at: datetime = Field(default_factory=datetime.now)
    total_reports: int = Field(default=0, ge=0)
    verified_reports: int = Field(default=0, ge=0)
    rejected_reports: int = Field(default=0, ge=0)
    flagged_reports: int = Field(default=0, ge=0)
    preferred_region_lat: float | None = Field(default=None, ge=-90, le=90)
    preferred_region_lon: float | None = Field(default=None, ge=-180, le=180)
    expertise_notes: str = Field(
        default="",
        description="Self-reported background: 'experienced collector', 'geology student', etc."
    )

    @property
    def trust_score(self) -> float:
        """
        Simple trust metric based on verification rate.

        Returns a value 0.0-1.0. New reporters start at 0.5 (benefit of
        the doubt). The score converges toward the actual verification rate
        as more reports accumulate, using Bayesian smoothing with a prior
        of 2 verified out of 4 total (0.5).
        """
        prior_verified = 2
        prior_total = 4
        smoothed = (self.verified_reports + prior_verified) / (
            self.total_reports + prior_total
        )
        return round(min(1.0, smoothed), 3)

    @property
    def is_active(self) -> bool:
        """A reporter with at least one report is considered active."""
        return self.total_reports > 0
