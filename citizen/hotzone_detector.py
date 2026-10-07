"""
DBSCAN spatial clustering of citizen reports to detect archaeological hotzones.

When citizen reports cluster spatially, it almost always means something real:
erosion is exposing a site, plowing is turning up material, or construction
is cutting through deposits. A single isolated find is anecdotal; a cluster
of 5+ finds within 500m is a signal that demands professional follow-up.

This module uses DBSCAN (Density-Based Spatial Clustering of Applications
with Noise) because archaeological site distributions are inherently
non-uniform — sites cluster along waterways, ridgelines, and ecotones.
DBSCAN finds clusters of arbitrary shape without requiring a predefined
number of clusters, and it naturally handles outliers (isolated finds).

Reports are weighted by classification confidence so that verified finds
pull stronger than uncertain ones. Temporal patterns are tracked to detect
emerging hotzones (e.g., a new construction project cutting through a site).
"""

from __future__ import annotations

import math
import uuid
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import fcluster, linkage

from core.schemas import CitizenReport, Hotspot
from core.geo_utils import haversine_distance, obfuscate_point


class HotzonePolygon(BaseModel):
    """
    A detected hotzone with its bounding polygon and statistics.

    The polygon is a convex hull of the contributing report locations,
    buffered slightly to account for GPS imprecision. Report density
    and confidence-weighted scores indicate how seriously to take
    the cluster.
    """
    hotzone_id: str = Field(default_factory=lambda: f"hz-{uuid.uuid4().hex[:12]}")
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    boundary_points: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Convex hull vertices as (lat, lon) tuples"
    )
    radius_km: float = Field(
        ..., gt=0,
        description="Approximate radius enclosing all reports in the cluster"
    )
    report_count: int = Field(..., ge=1)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    weighted_density: float = Field(
        default=0.0,
        description="Confidence-weighted report count per km^2"
    )
    dominant_classifications: list[str] = Field(
        default_factory=list,
        description="Most common artifact classes in this cluster"
    )
    earliest_report: datetime | None = Field(default=None)
    latest_report: datetime | None = Field(default=None)
    temporal_trend: str = Field(
        default="stable",
        description="Trend: 'increasing', 'stable', 'decreasing', 'new_burst'"
    )
    report_ids: list[str] = Field(
        default_factory=list,
        description="IDs of contributing reports"
    )


class TemporalWindow(BaseModel):
    """Tracks report frequency within a time window for trend detection."""
    window_start: datetime
    window_end: datetime
    report_count: int = 0
    mean_confidence: float = 0.0


class HotzoneDetector:
    """
    Detects and maintains archaeological hotzones from citizen reports.

    Uses a distance-based density clustering approach (DBSCAN-like) built
    on scipy's hierarchical clustering with a haversine distance matrix.
    This avoids sklearn as a dependency while achieving the same result.

    The detector maintains state across updates so hotzones can be tracked
    over time — a cluster that receives 3 new reports this week after months
    of silence may indicate fresh disturbance (construction, flooding).

    Args:
        eps_km: Maximum distance between reports in a cluster (km).
            Default 0.5km covers a typical archaeological site extent.
        min_samples: Minimum reports to form a cluster. Default 3 balances
            sensitivity against false positives.
        temporal_window_days: Days per window for trend analysis.
    """

    def __init__(
        self,
        eps_km: float = 0.5,
        min_samples: int = 3,
        temporal_window_days: int = 30,
    ) -> None:
        self.eps_km = eps_km
        self.min_samples = min_samples
        self.temporal_window_days = temporal_window_days

        self._reports: list[CitizenReport] = []
        self._hotzones: list[HotzonePolygon] = []
        self._last_computed: datetime | None = None

    @property
    def report_count(self) -> int:
        """Total reports currently tracked."""
        return len(self._reports)

    @property
    def hotzone_count(self) -> int:
        """Number of detected hotzones."""
        return len(self._hotzones)

    def add_report(self, report: CitizenReport) -> None:
        """Add a single report to the dataset without re-clustering."""
        self._reports.append(report)

    def add_reports(self, reports: list[CitizenReport]) -> None:
        """Add multiple reports to the dataset without re-clustering."""
        self._reports.extend(reports)

    def update_with_report(self, report: CitizenReport) -> list[HotzonePolygon]:
        """
        Add a report and re-detect hotzones.

        This is the primary incremental update method. After adding the
        report, it re-runs clustering on all reports. For large datasets,
        consider batching with add_reports() then calling detect_hotzones().

        Args:
            report: A new citizen report to incorporate.

        Returns:
            Updated list of all detected hotzones.
        """
        self._reports.append(report)
        return self.detect_hotzones()

    def detect_hotzones(self) -> list[HotzonePolygon]:
        """
        Run DBSCAN-style clustering on all reports.

        Uses scipy's hierarchical clustering with a precomputed haversine
        distance matrix, then cuts the dendrogram at eps_km to form flat
        clusters. Clusters smaller than min_samples are discarded as noise.

        Reports are weighted by classification_confidence: a verified
        projectile point counts more than an uncertain rock.

        Returns:
            List of detected HotzonePolygon objects.
        """
        if len(self._reports) < self.min_samples:
            self._hotzones = []
            self._last_computed = datetime.now()
            return []

        # Build coordinate array
        coords = np.array([[r.lat, r.lon] for r in self._reports])
        weights = np.array([
            max(0.1, r.classification_confidence) for r in self._reports
        ])

        # Compute pairwise haversine distances
        n = len(coords)
        if n == 1:
            self._hotzones = []
            self._last_computed = datetime.now()
            return []

        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = haversine_distance(
                    coords[i, 0], coords[i, 1],
                    coords[j, 0], coords[j, 1],
                )
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        # Convert to condensed form for scipy
        condensed = squareform(dist_matrix)

        # Hierarchical clustering, cut at eps_km
        Z = linkage(condensed, method="single")
        labels = fcluster(Z, t=self.eps_km, criterion="distance")

        # Group reports by cluster label
        clusters: dict[int, list[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[label].append(idx)

        # Build hotzones from clusters meeting min_samples threshold
        hotzones: list[HotzonePolygon] = []
        for cluster_id, indices in clusters.items():
            if len(indices) < self.min_samples:
                continue

            cluster_reports = [self._reports[i] for i in indices]
            cluster_coords = coords[indices]
            cluster_weights = weights[indices]

            hz = self._build_hotzone(cluster_reports, cluster_coords, cluster_weights)
            hotzones.append(hz)

        # Sort by weighted density (most significant first)
        hotzones.sort(key=lambda h: h.weighted_density, reverse=True)

        self._hotzones = hotzones
        self._last_computed = datetime.now()
        return hotzones

    def get_hotzones_near(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
    ) -> list[HotzonePolygon]:
        """
        Return hotzones within a given radius of a point.

        Useful for checking whether a new find falls near an existing
        hotzone, or for the API to serve location-based queries.

        Args:
            lat: Query latitude.
            lon: Query longitude.
            radius_km: Search radius in kilometers.

        Returns:
            List of HotzonePolygon objects within the search radius.
        """
        results: list[HotzonePolygon] = []
        for hz in self._hotzones:
            dist = haversine_distance(lat, lon, hz.center_lat, hz.center_lon)
            if dist <= radius_km + hz.radius_km:
                results.append(hz)
        return results

    def get_all_hotzones(self) -> list[HotzonePolygon]:
        """Return all currently detected hotzones."""
        return list(self._hotzones)

    def _build_hotzone(
        self,
        reports: list[CitizenReport],
        coords: np.ndarray,
        weights: np.ndarray,
    ) -> HotzonePolygon:
        """Construct a HotzonePolygon from a cluster of reports."""
        # Center: confidence-weighted centroid
        total_weight = weights.sum()
        center_lat = float(np.average(coords[:, 0], weights=weights))
        center_lon = float(np.average(coords[:, 1], weights=weights))

        # Radius: max distance from center to any report in cluster
        max_dist = 0.0
        for i in range(len(coords)):
            d = haversine_distance(center_lat, center_lon, coords[i, 0], coords[i, 1])
            max_dist = max(max_dist, d)
        radius_km = max(max_dist, 0.05)  # Minimum 50m radius

        # Convex hull (simple approach: sorted by angle from center)
        boundary = self._convex_hull_points(coords)

        # Dominant classifications
        class_counts: dict[str, float] = defaultdict(float)
        for r, w in zip(reports, weights):
            class_counts[r.preliminary_classification.value] += w
        dominant = sorted(class_counts.keys(), key=lambda c: class_counts[c], reverse=True)

        # Temporal analysis
        timestamps = [r.timestamp for r in reports]
        earliest = min(timestamps)
        latest = max(timestamps)
        trend = self._detect_temporal_trend(timestamps)

        # Weighted density: sum of weights / area
        area_km2 = math.pi * radius_km ** 2
        weighted_density = float(total_weight / max(area_km2, 0.01))

        mean_conf = float(weights.mean())

        report_ids = [r.report_id for r in reports if r.report_id]

        return HotzonePolygon(
            hotzone_id="hz-" + hashlib.sha256("|".join(sorted(report_ids)).encode()).hexdigest()[:12],
            center_lat=round(center_lat, 6),
            center_lon=round(center_lon, 6),
            boundary_points=boundary,
            radius_km=round(radius_km, 3),
            report_count=len(reports),
            mean_confidence=round(mean_conf, 3),
            weighted_density=round(weighted_density, 2),
            dominant_classifications=dominant[:3],
            earliest_report=earliest,
            latest_report=latest,
            temporal_trend=trend,
            report_ids=report_ids,
        )

    def _convex_hull_points(self, coords: np.ndarray) -> list[tuple[float, float]]:
        """
        Compute convex hull vertices from a set of 2D coordinates.

        Uses a simple Graham scan. Returns (lat, lon) tuples ordered
        counter-clockwise.
        """
        if len(coords) < 3:
            return [(float(c[0]), float(c[1])) for c in coords]

        points = [(float(c[0]), float(c[1])) for c in coords]

        # Find lowest-leftmost point as anchor
        anchor = min(points, key=lambda p: (p[0], p[1]))

        def polar_angle(p: tuple[float, float]) -> float:
            return math.atan2(p[1] - anchor[1], p[0] - anchor[0])

        def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        sorted_pts = sorted(
            [p for p in points if p != anchor],
            key=lambda p: (polar_angle(p), -((p[0] - anchor[0])**2 + (p[1] - anchor[1])**2)),
        )

        hull: list[tuple[float, float]] = [anchor]
        for pt in sorted_pts:
            while len(hull) > 1 and cross(hull[-2], hull[-1], pt) <= 0:
                hull.pop()
            hull.append(pt)

        return hull

    def _detect_temporal_trend(self, timestamps: list[datetime]) -> str:
        """
        Detect the temporal trend of reports in a cluster.

        Compares report frequency in recent windows vs. older windows
        to identify emerging hotzones (new construction/erosion exposing
        material) vs. established ones.
        """
        if len(timestamps) < 2:
            return "stable"

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        window = timedelta(days=self.temporal_window_days)

        recent_cutoff = now - window
        older_cutoff = recent_cutoff - window

        recent_count = sum(1 for t in timestamps if t >= recent_cutoff)
        older_count = sum(1 for t in timestamps if older_cutoff <= t < recent_cutoff)

        # All reports are within the most recent window
        if older_count == 0 and recent_count >= self.min_samples:
            return "new_burst"

        if older_count == 0:
            return "stable"

        ratio = recent_count / older_count
        if ratio > 2.0:
            return "increasing"
        elif ratio < 0.5:
            return "decreasing"
        return "stable"
