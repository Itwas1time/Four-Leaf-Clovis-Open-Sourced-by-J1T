"""
NDVI time-series processor for crop mark detection.

Computes Normalized Difference Vegetation Index from Sentinel-2 imagery
and detects persistent geometric anomalies that indicate buried features.

Archaeological rationale:
    Buried stone walls, ditches, and foundations cause differential plant
    growth visible in multispectral imagery. Over a stone wall, roots hit
    rock and plants are stunted (negative crop mark). Over a filled ditch,
    deeper soil retains more moisture and plants grow taller (positive
    crop mark). These "crop marks" and "soil marks" have been used in
    European aerial archaeology since the 1920s.

    The key insight for automated detection: archaeological crop marks are
    PERSISTENT across seasons and years, while agricultural patterns change
    annually. A geometric anomaly visible in spring 2022, summer 2023,
    and fall 2024 is far more likely archaeological than natural.

Bands used:
    - B04 (Red): vegetation absorption
    - B08 (NIR): vegetation reflection
    - B12 (SWIR): soil moisture — buried features retain moisture differently
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class NDVIProcessor:
    """
    Compute NDVI and detect crop mark anomalies from Sentinel-2 data.

    Works with multi-temporal image stacks: more scenes = better
    discrimination between archaeological and natural features.
    """

    def compute_ndvi(self, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Compute NDVI from red (B04) and NIR (B08) bands.

        NDVI = (NIR - Red) / (NIR + Red)
        Range: -1.0 to 1.0
        Typical vegetation: 0.2-0.8
        Bare soil: 0.0-0.2
        Water: negative
        """
        red = red.astype(np.float64)
        nir = nir.astype(np.float64)
        denominator = nir + red
        # Avoid division by zero
        ndvi = np.where(denominator > 0, (nir - red) / denominator, 0.0)
        return np.clip(ndvi, -1.0, 1.0)

    def compute_moisture_index(self, nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
        """
        Compute Normalized Difference Moisture Index from NIR (B08) and SWIR (B12).

        NDMI = (NIR - SWIR) / (NIR + SWIR)
        Buried features retain moisture differently than surrounding soil,
        creating detectable NDMI anomalies even when NDVI differences are subtle.
        """
        nir = nir.astype(np.float64)
        swir = swir.astype(np.float64)
        denominator = nir + swir
        ndmi = np.where(denominator > 0, (nir - swir) / denominator, 0.0)
        return np.clip(ndmi, -1.0, 1.0)

    def temporal_composite(self, ndvi_stack: list[np.ndarray]) -> dict[str, np.ndarray]:
        """
        Build temporal statistics from a multi-date NDVI stack.

        Returns mean, std, min, and max NDVI across all dates.
        High temporal standard deviation in a geometric pattern is
        a strong indicator of buried features.
        """
        if not ndvi_stack:
            raise ValueError("NDVI stack is empty")

        stack = np.array(ndvi_stack)
        return {
            "mean": np.nanmean(stack, axis=0),
            "std": np.nanstd(stack, axis=0),
            "min": np.nanmin(stack, axis=0),
            "max": np.nanmax(stack, axis=0),
            "range": np.nanmax(stack, axis=0) - np.nanmin(stack, axis=0),
        }

    def detect_anomalies(
        self,
        ndvi_composite: dict[str, np.ndarray],
        z_threshold: float = 2.0,
    ) -> np.ndarray:
        """
        Detect spatial anomalies in the NDVI composite.

        An anomaly is a pixel where the NDVI mean deviates significantly
        from its local neighborhood. The z-score approach normalizes for
        regional vegetation differences (forest vs grassland vs agriculture).

        Returns a binary anomaly mask.
        """
        from scipy import ndimage as ndi

        mean_ndvi = ndvi_composite["mean"]

        # Local statistics (200m neighborhood at 10m resolution)
        kernel_size = 21
        local_mean = ndi.uniform_filter(mean_ndvi, size=kernel_size)
        local_sq_mean = ndi.uniform_filter(mean_ndvi ** 2, size=kernel_size)
        local_std = np.sqrt(np.maximum(local_sq_mean - local_mean ** 2, 0))

        # Z-score
        z_scores = np.where(local_std > 0.01, (mean_ndvi - local_mean) / local_std, 0.0)

        # Both positive and negative anomalies are interesting
        return np.abs(z_scores) > z_threshold

    def score_cell_crop_marks(
        self,
        anomaly_fraction: float,
        temporal_persistence: float = 0.0,
    ) -> float:
        """
        Score a grid cell for crop mark evidence.

        Args:
            anomaly_fraction: Fraction of cell area showing NDVI anomalies (0-1).
            temporal_persistence: Fraction of dates where anomaly is visible (0-1).

        Returns:
            Crop mark score (0-1).
        """
        # Anomaly fraction scoring (diminishing returns — very high fraction
        # is more likely agricultural than archaeological)
        if anomaly_fraction < 0.01:
            spatial_score = 0.0
        elif anomaly_fraction < 0.1:
            spatial_score = anomaly_fraction * 8  # Linear up to 0.8
        elif anomaly_fraction < 0.3:
            spatial_score = 0.8  # Peak zone
        else:
            spatial_score = max(0.8 - (anomaly_fraction - 0.3) * 2, 0.2)

        # Temporal persistence bonus: visible across seasons = more likely archaeological
        persistence_bonus = temporal_persistence * 0.2

        return round(min(spatial_score + persistence_bonus, 1.0), 4)
