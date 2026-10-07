"""
Paleo-coastline and continental shelf reconstructor.

Maps now-submerged coastlines at key time periods based on sea level curves
and bathymetric data.

Archaeological rationale:
    During the Last Glacial Maximum (~20,000 BP), sea levels were 120-130m
    lower than present. The coastal migration hypothesis ("kelp highway")
    proposes that early Americans followed the Pacific coast, exploiting
    marine resources along productive kelp forests. The evidence for this
    route is now 50-130m underwater on the continental shelf.

    Submerged river mouths, embayments, and headlands would have been
    prime settlement locations — the same environmental features that
    attract settlement on modern coastlines attracted them on paleo-coastlines.

    This processor reconstructs where those features were at each time period,
    enabling targeted survey of now-submerged landscape.

Time periods modeled:
    20,000 BP: LGM maximum — sea level ~125m below present
    15,000 BP: Deglaciation begins — ~80m below
    12,000 BP: Younger Dryas — ~60m below
    10,000 BP: Early Holocene — ~40m below
    8,000 BP: Mid-Holocene — ~15m below
    6,000 BP: Near-modern levels — ~5m below
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core.schemas import BoundingBox

logger = logging.getLogger(__name__)

# Global sea level curve (simplified from Lambeck et al. 2014)
# Format: (years_BP, meters_below_present)
SEA_LEVEL_CURVE: list[tuple[int, float]] = [
    (25000, -130.0),
    (20000, -125.0),
    (18000, -110.0),
    (16000, -95.0),
    (15000, -80.0),
    (14000, -70.0),
    (13000, -60.0),
    (12000, -55.0),  # Younger Dryas
    (11000, -50.0),
    (10000, -40.0),
    (9000, -30.0),
    (8000, -15.0),
    (7000, -8.0),
    (6000, -5.0),
    (5000, -3.0),
    (4000, -2.0),
    (3000, -1.0),
    (2000, -0.5),
    (1000, -0.2),
    (0, 0.0),
]


class ShelfReconstructor:
    """
    Reconstruct paleo-coastlines from bathymetric data and sea level curves.

    Given a bathymetric DEM (negative elevations = depth below sea level),
    generates coastline polygons for each time period.
    """

    def sea_level_at(self, years_bp: int) -> float:
        """
        Interpolate sea level at a given time in the past.

        Returns meters relative to present (negative = below present).
        Uses linear interpolation between known points.
        """
        if years_bp <= 0:
            return 0.0
        if years_bp >= SEA_LEVEL_CURVE[0][0]:
            return SEA_LEVEL_CURVE[0][1]

        # Linear interpolation
        for i in range(len(SEA_LEVEL_CURVE) - 1):
            t1, sl1 = SEA_LEVEL_CURVE[i]
            t2, sl2 = SEA_LEVEL_CURVE[i + 1]
            if t2 <= years_bp <= t1:
                fraction = (years_bp - t2) / (t1 - t2)
                return sl2 + fraction * (sl1 - sl2)

        return 0.0

    def reconstruct_coastline(
        self,
        bathymetry: np.ndarray,
        years_bp: int,
        pixel_size_m: float = 100.0,
    ) -> np.ndarray:
        """
        Generate a land/water mask for a given time period.

        Args:
            bathymetry: Elevation array where negative values = depth below
                        present sea level (meters).
            years_bp: Years before present.
            pixel_size_m: Pixel size in meters.

        Returns:
            Boolean array: True = land (above sea level at that time).
        """
        sea_level = self.sea_level_at(years_bp)
        # Land exists where the surface elevation exceeds the sea level
        # bathymetry values: negative = below present sea level
        # At 20,000 BP, sea level was -125m, so anything above -125m was land
        return bathymetry > sea_level

    def identify_paleo_features(
        self,
        bathymetry: np.ndarray,
        years_bp: int,
        pixel_size_m: float = 100.0,
    ) -> dict[str, Any]:
        """
        Identify archaeologically significant features on the paleo-landscape.

        Features:
        - River channels: linear depressions in the shelf
        - Embayments: concavities in the coastline (protected harbors)
        - Headlands: convexities (strategic/defensive positions)
        - Nearshore zone: the productive strip within 1km of coast
        """
        sea_level = self.sea_level_at(years_bp)
        land_mask = bathymetry > sea_level
        water_mask = ~land_mask

        from scipy import ndimage

        # Coastline detection (boundary between land and water)
        dilated = ndimage.binary_dilation(land_mask)
        coastline = dilated & water_mask

        # Nearshore zone (within ~1km of coast)
        nearshore_pixels = max(1, int(1000 / pixel_size_m))
        nearshore = ndimage.binary_dilation(coastline, iterations=nearshore_pixels)
        nearshore = nearshore & land_mask

        # Submerged channels: linear depressions below the paleo-surface
        # These would have been rivers on the exposed shelf
        shelf_surface = np.where(land_mask, bathymetry, np.nan)
        if np.any(~np.isnan(shelf_surface)):
            from scipy.ndimage import gaussian_filter
            smoothed = gaussian_filter(np.nan_to_num(bathymetry), sigma=5)
            channels = (bathymetry < smoothed - 2.0) & land_mask  # 2m below local surface
        else:
            channels = np.zeros_like(land_mask)

        return {
            "sea_level_m": sea_level,
            "land_area_pixels": int(land_mask.sum()),
            "coastline_length_pixels": int(coastline.sum()),
            "nearshore_area_pixels": int(nearshore.sum()),
            "channel_pixels": int(channels.sum()),
            "land_mask": land_mask,
            "coastline_mask": coastline,
            "nearshore_mask": nearshore,
            "channel_mask": channels,
        }

    def score_settlement_probability(
        self,
        bathymetry: np.ndarray,
        years_bp: int,
        pixel_size_m: float = 100.0,
    ) -> np.ndarray:
        """
        Score each pixel for paleo-settlement probability.

        High probability zones:
        - Nearshore (marine resource access)
        - Near river mouths on the shelf (freshwater + marine resources)
        - Protected embayments (shelter from storms)
        - Elevated terraces above the coast (habitation preference)
        """
        features = self.identify_paleo_features(bathymetry, years_bp, pixel_size_m)
        land_mask = features["land_mask"]

        score = np.zeros_like(bathymetry, dtype=np.float64)

        # Nearshore bonus (strongest signal for coastal migration)
        score[features["nearshore_mask"]] += 0.5

        # River channel proximity on the shelf
        if features["channel_pixels"] > 0:
            from scipy.ndimage import distance_transform_edt
            channel_dist = distance_transform_edt(~features["channel_mask"]) * pixel_size_m
            channel_score = np.where(
                land_mask,
                np.clip(1.0 - channel_dist / 5000.0, 0, 0.3),  # Within 5km
                0.0,
            )
            score += channel_score

        # Coastline proximity for non-nearshore land
        score[features["coastline_mask"]] += 0.2

        # Zero out water areas
        score[~land_mask] = 0.0

        return np.clip(score, 0, 1)

    def get_time_periods(self) -> list[dict[str, Any]]:
        """Return the standard analysis time periods with sea levels."""
        key_periods = [20000, 15000, 12000, 10000, 8000, 6000]
        return [
            {"years_bp": t, "sea_level_m": self.sea_level_at(t)}
            for t in key_periods
        ]
