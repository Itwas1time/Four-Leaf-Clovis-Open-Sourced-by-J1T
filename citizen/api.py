"""
FastAPI backend for the ARCHAEO-SCAN citizen science module.

Provides public endpoints for submitting field reports, querying hotzones,
and browsing reports with pagination. Two critical safety measures are
built in:

1. RATE LIMITING — prevents abuse and accidental flooding. A citizen
   reporter submitting more than a few reports per hour is unusual and
   may indicate automated submissions or GPS spoofing.

2. COORDINATE OBFUSCATION — public endpoints return fuzzy coordinates
   (~1km precision) to protect site locations from looting. Precise
   coordinates are stored internally but never exposed through the
   public API. Archaeological sites are non-renewable resources; once
   looted, their scientific context is destroyed forever.

Endpoints:
    POST /report — Submit a find (photo, GPS, description)
    GET /reports — List reports with pagination and filtering
    GET /hotzones — Current hotzone clusters
    GET /nearby/{lat}/{lon} — Hotzones near a point
"""

from __future__ import annotations

import logging
import base64
import math
import time
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.schemas import ArtifactClass, CitizenReport, Hotspot
from core.geo_utils import haversine_distance, obfuscate_point
from citizen.report_schema import (
    ReportSubmission,
    ReportStatus,
    ReportStatusEnum,
    ReporterProfile,
)
from citizen.find_classifier import FindClassifier, ClassificationResult
from citizen.hotzone_detector import HotzoneDetector, HotzonePolygon
from core.web_security import configure_local_api

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter — simple in-memory sliding window per reporter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    In-memory rate limiter using a sliding window counter.

    Each reporter_id is tracked independently. Limits are generous for
    legitimate use (a productive field day might yield 20+ finds) but
    catch obvious abuse or automated submissions.
    """

    def __init__(
        self,
        max_requests: int = 30,
        window_seconds: int = 3600,
        max_keys: int = 4096,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._requests: OrderedDict[str, list[float]] = OrderedDict()

    def check(self, key: str) -> bool:
        """
        Check if a request is allowed under the rate limit.

        Returns True if allowed, False if rate limited.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune old entries
        self._requests[key] = [
            t for t in self._requests.get(key, []) if t > cutoff
        ]
        self._requests.move_to_end(key)
        if len(self._requests) > self.max_keys:
            self._requests.popitem(last=False)

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        recent = [t for t in self._requests.get(key, []) if t > cutoff]
        return max(0, self.max_requests - len(recent))


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    """Response returned after successfully submitting a report."""
    report_id: str
    status: ReportStatusEnum
    message: str
    classification: ClassificationResult | None = None


class HotzoneResponse(BaseModel):
    """A hotzone with obfuscated coordinates for public consumption."""
    hotzone_id: str
    center_lat: float = Field(..., description="Obfuscated latitude (~1km precision)")
    center_lon: float = Field(..., description="Obfuscated longitude (~1km precision)")
    radius_km: float
    report_count: int
    mean_confidence: float
    dominant_classifications: list[str]
    temporal_trend: str


class PaginatedReports(BaseModel):
    """Paginated list of reports with obfuscated coordinates."""
    reports: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_next: bool


# ---------------------------------------------------------------------------
# Application state — in production these would be backed by DataStore / DB
# ---------------------------------------------------------------------------

class AppState:
    """Mutable application state shared across endpoints."""

    def __init__(self) -> None:
        self.reports: dict[str, CitizenReport] = {}
        self.report_statuses: dict[str, ReportStatus] = {}
        self.reporter_profiles: dict[str, ReporterProfile] = {}
        self.detector: HotzoneDetector = HotzoneDetector()
        self.rate_limiter: RateLimiter = RateLimiter()
        self.classifier: FindClassifier | None = None

    def get_or_create_profile(self, reporter_id: str) -> ReporterProfile:
        """Get existing profile or create a new one."""
        if reporter_id not in self.reporter_profiles:
            self.reporter_profiles[reporter_id] = ReporterProfile(
                reporter_id=reporter_id,
            )
        return self.reporter_profiles[reporter_id]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    enable_classifier: bool = False,
    classifier_model: str = "claude-sonnet-4-20250514",
    rate_limit_requests: int = 30,
    rate_limit_window: int = 3600,
    obfuscation_km: float = 1.0,
    photo_root: str | Path | None = None,
    max_reports: int = 500,
) -> FastAPI:
    """
    Create and configure the citizen science FastAPI application.

    Args:
        enable_classifier: Whether to enable LLM-based photo classification
            on submission. Requires an Anthropic API key in the environment.
        classifier_model: Model to use for classification.
        rate_limit_requests: Max requests per reporter per window.
        rate_limit_window: Rate limit window in seconds.
        obfuscation_km: Coordinate obfuscation precision for public endpoints.

    Returns:
        Configured FastAPI application instance.
    """
    if not math.isfinite(obfuscation_km) or not 1 <= obfuscation_km <= 100:
        raise ValueError("Public coordinate rounding must be between 1 and 100 km.")
    if not 1 <= max_reports <= 500:
        raise ValueError("The local in-memory API supports at most 500 reports.")
    if rate_limit_requests < 1 or rate_limit_window < 1:
        raise ValueError("Rate limit settings must be positive.")
    approved_photos = Path(photo_root).resolve() if photo_root is not None else None
    if enable_classifier and (approved_photos is None or not approved_photos.is_dir()):
        raise ValueError("Classification requires a server-configured approved photo directory.")
    app = FastAPI(
        title="ARCHAEO-SCAN Citizen Science API",
        description=(
            "Submit archaeological surface finds, query hotzones, and browse "
            "reports. Coordinates in public responses are obfuscated to ~1km "
            "to protect site locations from unauthorized collection."
        ),
        version="0.1.0",
    )
    configure_local_api(app)

    state = AppState()
    state.rate_limiter = RateLimiter(
        max_requests=rate_limit_requests,
        window_seconds=rate_limit_window,
    )
    client_limiter = RateLimiter(max_requests=rate_limit_requests, window_seconds=rate_limit_window)

    if enable_classifier:
        state.classifier = FindClassifier(model=classifier_model)

    # -------------------------------------------------------------------
    # POST /report — submit a field report
    # -------------------------------------------------------------------
    @app.post("/report", response_model=ReportResponse)
    async def submit_report(submission: ReportSubmission, request: Request) -> ReportResponse:
        """
        Submit a citizen science field report.

        Accepts GPS coordinates, photos, description, and depositional
        context. The report is assigned a unique ID, optionally classified
        by the LLM, and added to the hotzone clustering pipeline.

        Rate limited to prevent abuse (default: 30 reports/hour per reporter).
        """
        # Rate limit check
        client_key = request.client.host if request.client else "unknown"
        if not client_limiter.check(client_key) or not state.rate_limiter.check(submission.reporter_id):
            remaining = state.rate_limiter.remaining(submission.reporter_id)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. {remaining} requests remaining. "
                    "Please wait before submitting more reports."
                ),
            )

        if len(state.reports) >= max_reports:
            raise HTTPException(status_code=503, detail="Local report capacity reached; archive reports before accepting more.")

        # A client-provided path must never select arbitrary files on the host.
        image_data = None
        media_type = None
        if state.classifier and submission.photos:
            reference = Path(submission.photos[0].file_path)
            if reference.is_absolute() or ".." in reference.parts:
                raise HTTPException(status_code=422, detail="Use an approved relative photo reference.")
            image_path = (approved_photos / reference).resolve()
            if not image_path.is_relative_to(approved_photos) or not image_path.is_file():
                raise HTTPException(status_code=422, detail="Photo reference is outside the approved directory or unavailable.")
            if image_path.stat().st_size > 5_000_000:
                raise HTTPException(status_code=413, detail="Photo is too large; maximum 5 MB.")
            image_data = image_path.read_bytes()
            if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                media_type = "image/png"
            elif image_data.startswith(b"\xff\xd8\xff"):
                media_type = "image/jpeg"
            else:
                raise HTTPException(status_code=422, detail="Approved photos must contain PNG or JPEG image data.")

        # Generate report ID
        report_id = f"cr-{uuid.uuid4().hex[:12]}"

        # Build CitizenReport from submission
        citizen_report = CitizenReport(
            report_id=report_id,
            reporter_id=submission.reporter_id,
            lat=submission.location.lat,
            lon=submission.location.lon,
            photos=[p.file_path for p in submission.photos],
            description=submission.description,
            preliminary_classification=ArtifactClass.UNCERTAIN,
            classification_confidence=0.0,
            timestamp=submission.submitted_at,
            context={
                "surface_context": submission.surface_context.value,
                "nearby_water": submission.nearby_water,
                "nearby_landmarks": submission.nearby_landmarks,
                "estimated_count": submission.estimated_count,
                "gps_accuracy_m": submission.location.accuracy_m,
                **submission.additional_context,
            },
        )

        # Optional LLM classification
        classification_result: ClassificationResult | None = None
        if state.classifier and submission.photos:
            try:
                classification_result = state.classifier.classify_from_base64(
                    base64.standard_b64encode(image_data).decode("ascii"), media_type,
                    reporter_description=submission.description,
                )
                citizen_report.preliminary_classification = classification_result.classification
                citizen_report.classification_confidence = classification_result.confidence
            except Exception:
                # Classification failure must not block report submission
                logger.warning("Auto-classification failed for report %s", report_id)

        # Store report
        state.reports[report_id] = citizen_report

        # Create status tracking
        report_status = ReportStatus(report_id=report_id)
        if classification_result:
            report_status.classification_result = classification_result.classification.value
            report_status.classification_confidence = classification_result.confidence
            report_status.transition(ReportStatusEnum.CLASSIFIED, "Auto-classified by LLM")
        state.report_statuses[report_id] = report_status

        # Update reporter profile
        profile = state.get_or_create_profile(submission.reporter_id)
        profile.total_reports += 1

        # Add to hotzone detector
        state.detector.add_report(citizen_report)

        # Re-cluster periodically (every 5 reports) rather than on every submission
        if state.detector.report_count % 5 == 0:
            state.detector.detect_hotzones()

        status = (
            ReportStatusEnum.CLASSIFIED if classification_result
            else ReportStatusEnum.SUBMITTED
        )
        message = "Report submitted successfully."
        if classification_result:
            message += (
                f" Preliminary classification: {classification_result.classification.value}"
                f" (confidence: {classification_result.confidence:.0%})."
                " This is a preliminary assessment — professional review pending."
            )

        return ReportResponse(
            report_id=report_id,
            status=status,
            message=message,
            classification=classification_result,
        )

    # -------------------------------------------------------------------
    # GET /hotzones — list all detected hotzones
    # -------------------------------------------------------------------
    @app.get("/hotzones", response_model=list[HotzoneResponse])
    async def get_hotzones(
        min_reports: int = Query(
            default=3, ge=1,
            description="Minimum reports in a hotzone to include"
        ),
        min_confidence: float = Query(
            default=0.0, ge=0.0, le=1.0,
            description="Minimum mean confidence to include"
        ),
    ) -> list[HotzoneResponse]:
        """
        List all detected archaeological hotzones.

        Coordinates are obfuscated to ~1km precision to protect site
        locations. Filter by minimum report count and confidence threshold.
        Hotzones are sorted by weighted density (most significant first).
        """
        # Re-detect to ensure fresh results
        state.detector.detect_hotzones()

        results: list[HotzoneResponse] = []
        for hz in state.detector.get_all_hotzones():
            if hz.report_count < min_reports:
                continue
            if hz.mean_confidence < min_confidence:
                continue

            obf_lat, obf_lon = obfuscate_point(
                hz.center_lat, hz.center_lon, precision_km=obfuscation_km
            )
            results.append(HotzoneResponse(
                hotzone_id=hz.hotzone_id,
                center_lat=obf_lat,
                center_lon=obf_lon,
                radius_km=hz.radius_km,
                report_count=hz.report_count,
                mean_confidence=hz.mean_confidence,
                dominant_classifications=hz.dominant_classifications,
                temporal_trend=hz.temporal_trend,
            ))

        return results

    # -------------------------------------------------------------------
    # GET /nearby/{lat}/{lon} — hotzones near a point
    # -------------------------------------------------------------------
    @app.get("/nearby/{lat}/{lon}", response_model=list[HotzoneResponse])
    async def get_nearby_hotzones(
        lat: float,
        lon: float,
        radius_km: float = Query(
            default=10.0, gt=0, le=100,
            description="Search radius in kilometers"
        ),
    ) -> list[HotzoneResponse]:
        """
        Find hotzones near a given GPS coordinate.

        Useful for field workers checking if their current location is
        near a known cluster, or for the public to explore their area.
        Coordinates in the response are obfuscated.

        Args:
            lat: Query latitude in decimal degrees.
            lon: Query longitude in decimal degrees.
            radius_km: Search radius (max 100km).
        """
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise HTTPException(
                status_code=400,
                detail="Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180."
            )

        # Membership must use the public center too. A tiny-radius query
        # against the private center otherwise becomes a location oracle.
        state.detector.detect_hotzones()

        results: list[HotzoneResponse] = []
        for hz in state.detector.get_all_hotzones():
            obf_lat, obf_lon = obfuscate_point(
                hz.center_lat, hz.center_lon, precision_km=obfuscation_km
            )
            if haversine_distance(lat, lon, obf_lat, obf_lon) > radius_km + hz.radius_km:
                continue
            results.append(HotzoneResponse(
                hotzone_id=hz.hotzone_id,
                center_lat=obf_lat,
                center_lon=obf_lon,
                radius_km=hz.radius_km,
                report_count=hz.report_count,
                mean_confidence=hz.mean_confidence,
                dominant_classifications=hz.dominant_classifications,
                temporal_trend=hz.temporal_trend,
            ))

        return results

    # -------------------------------------------------------------------
    # GET /reports — paginated report listing
    # -------------------------------------------------------------------
    @app.get("/reports", response_model=PaginatedReports)
    async def list_reports(
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
        classification: str | None = Query(
            default=None,
            description="Filter by artifact class (e.g., 'lithic_projectile')"
        ),
        reporter_id: str | None = Query(
            default=None,
            description="Filter by reporter ID"
        ),
        min_confidence: float = Query(
            default=0.0, ge=0.0, le=1.0,
            description="Minimum classification confidence"
        ),
    ) -> PaginatedReports:
        """
        List submitted reports with pagination and filtering.

        All coordinates in the response are obfuscated to protect site
        locations. Use filters to narrow results by classification type,
        reporter, or confidence threshold.
        """
        # Build filtered report list
        all_reports = list(state.reports.values())

        if classification:
            try:
                target_class = ArtifactClass(classification)
                all_reports = [
                    r for r in all_reports
                    if r.preliminary_classification == target_class
                ]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown classification '{classification}'. "
                           f"Valid values: {[c.value for c in ArtifactClass]}"
                )

        if reporter_id:
            all_reports = [r for r in all_reports if r.reporter_id == reporter_id]

        if min_confidence > 0:
            all_reports = [
                r for r in all_reports
                if r.classification_confidence >= min_confidence
            ]

        # Sort by timestamp descending (newest first)
        all_reports.sort(key=lambda r: r.timestamp, reverse=True)

        total = len(all_reports)
        start = (page - 1) * page_size
        end = start + page_size
        page_reports = all_reports[start:end]

        # Build response with obfuscated coordinates
        report_dicts: list[dict[str, Any]] = []
        for r in page_reports:
            obf_lat, obf_lon = obfuscate_point(r.lat, r.lon, precision_km=obfuscation_km)
            report_dicts.append({
                "report_id": r.report_id,
                "reporter_id": r.reporter_id,
                "lat": obf_lat,
                "lon": obf_lon,
                "description": r.description,
                "classification": r.preliminary_classification.value,
                "confidence": r.classification_confidence,
                "timestamp": r.timestamp.isoformat(),
                "photo_count": len(r.photos),
                "status": (
                    state.report_statuses[r.report_id].status.value
                    if r.report_id in state.report_statuses
                    else "submitted"
                ),
            })

        return PaginatedReports(
            reports=report_dicts,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end < total,
        )

    # -------------------------------------------------------------------
    # GET /health — service health check
    # -------------------------------------------------------------------
    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Service health check with basic stats."""
        return {
            "status": "ok",
            "service": "archaeo-scan-citizen",
            "total_reports": len(state.reports),
            "total_hotzones": state.detector.hotzone_count,
            "classifier_enabled": state.classifier is not None,
        }

    return app
