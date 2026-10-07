"""
LiDAR-derived product generator.

Transforms raw LiDAR point clouds into archaeological analysis rasters:
hillshade, slope, Local Relief Model, and Sky-View Factor. These derived
products are what actually reveal features — the raw point cloud is just
the input.

Archaeological rationale:
    LiDAR (Light Detection And Ranging) penetrates forest canopy to reveal
    bare-earth terrain beneath. This has revolutionized archaeology since ~2010.
    Features invisible from the ground, in aerial photos, or in satellite
    imagery become starkly visible in LiDAR derivatives. The LiDAR survey of
    Caracol, Belize revealed an entire Maya city under jungle. In the eastern US,
    thousands of previously unknown mounds have been found in LiDAR data.

Key products:
    - Hillshade: simulated illumination reveals features by their shadows
    - Multi-directional hillshade: multiple light angles catch features
      oriented in any direction
    - Slope map: abrupt slope changes indicate walls, edges, terraces
    - Local Relief Model (LRM): THE key product — subtracts regional
      trend to isolate micro-topography
    - Sky-View Factor (SVF): how much sky is visible from each point —
      better than hillshade for revealing subtle features because it's
      direction-independent

All processing is tile-based and CPU-only. Windowed raster I/O
via rasterio keeps memory bounded.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

logger = logging.getLogger(__name__)

# Multi-directional hillshade angles (degrees from north)
HILLSHADE_AZIMUTHS = [315, 45, 90, 0]
DEFAULT_ALTITUDE = 45  # Sun elevation angle in degrees


class LidarProcessor:
    """
    Generate archaeological analysis products from DEM/LiDAR rasters.

    All methods accept numpy arrays and return numpy arrays — the caller
    handles raster I/O. This keeps the processor pure and testable.
    """

    def hillshade(
        self,
        dem: np.ndarray,
        azimuth: float = 315.0,
        altitude: float = DEFAULT_ALTITUDE,
        pixel_size_m: float = 1.0,
    ) -> np.ndarray:
        """
        Compute analytical hillshade.

        Simulates illumination from a given azimuth and altitude.
        Standard archaeological practice uses 315° (NW) as primary
        illumination, but multi-directional is preferred.

        Args:
            dem: Elevation array in meters.
            azimuth: Light source azimuth in degrees from north.
            altitude: Light source altitude in degrees from horizon.
            pixel_size_m: Pixel size in meters (for correct slope).

        Returns:
            Hillshade array (0-255).
        """
        az_rad = np.radians(360 - azimuth + 90)
        alt_rad = np.radians(altitude)

        # Compute slope components
        dy, dx = np.gradient(dem.astype(np.float64), pixel_size_m)
        slope = np.arctan(np.sqrt(dx ** 2 + dy ** 2))
        aspect = np.arctan2(-dy, dx)

        # Hillshade formula
        hs = (np.sin(alt_rad) * np.cos(slope) +
              np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect))

        # Scale to 0-255
        hs = np.clip(hs, 0, 1)
        return (hs * 255).astype(np.uint8)

    def multi_hillshade(
        self,
        dem: np.ndarray,
        azimuths: list[float] | None = None,
        altitude: float = DEFAULT_ALTITUDE,
        pixel_size_m: float = 1.0,
    ) -> np.ndarray:
        """
        Compute multi-directional hillshade by combining multiple illumination angles.

        Features oriented in any direction will be visible in at least one
        component. The combined product is the maximum of all components
        at each pixel — ensuring no features are hidden by unfavorable
        illumination angle.
        """
        if azimuths is None:
            azimuths = HILLSHADE_AZIMUTHS

        layers = [self.hillshade(dem, az, altitude, pixel_size_m) for az in azimuths]
        # Maximum of all hillshades catches all feature orientations
        return np.maximum.reduce(layers)

    def slope_map(self, dem: np.ndarray, pixel_size_m: float = 1.0) -> np.ndarray:
        """
        Compute slope in degrees.

        Abrupt slope changes (high second derivative) indicate artificial
        features: wall edges, terrace retaining walls, mound flanks.
        """
        dy, dx = np.gradient(dem.astype(np.float64), pixel_size_m)
        slope_rad = np.arctan(np.sqrt(dx ** 2 + dy ** 2))
        return np.degrees(slope_rad)

    def local_relief_model(
        self,
        dem: np.ndarray,
        pixel_size_m: float = 1.0,
        window_m: float = 500.0,
    ) -> np.ndarray:
        """
        Compute Local Relief Model (LRM).

        THE single most effective DEM-derived product for archaeology.
        Removes regional topographic trend to isolate micro-features.

        - Positive values = raised features (mounds, walls, causeways)
        - Negative values = depressed features (pits, ditches, quarries)
        - Near-zero = natural terrain following regional trend

        Args:
            dem: Elevation array in meters.
            pixel_size_m: Pixel size in meters.
            window_m: Smoothing window in meters. 500m for small features
                      (individual mounds), 2000m for large features
                      (mound complexes, enclosures).
        """
        kernel_pixels = max(3, int(window_m / pixel_size_m))
        if kernel_pixels % 2 == 0:
            kernel_pixels += 1

        # Low-pass filter creates the trend surface
        sigma = kernel_pixels / 3
        trend = ndimage.gaussian_filter(dem.astype(np.float64), sigma=sigma)

        return dem.astype(np.float64) - trend

    def sky_view_factor(
        self,
        dem: np.ndarray,
        pixel_size_m: float = 1.0,
        n_directions: int = 16,
        max_radius_pixels: int = 50,
    ) -> np.ndarray:
        """
        Compute Sky-View Factor (SVF).

        SVF measures the proportion of sky visible from each point.
        Depressions and enclosed features have low SVF; mounds and ridges
        have high SVF. Unlike hillshade, SVF is direction-independent,
        making it better for features of unknown orientation.

        This is an approximation using radial sampling — exact SVF would
        require horizon angle computation in all directions.
        """
        dem64 = dem.astype(np.float64)
        rows, cols = dem64.shape
        svf = np.ones((rows, cols), dtype=np.float64)

        for direction in range(n_directions):
            angle_rad = 2 * np.pi * direction / n_directions

            # Maximum horizon angle in this direction
            max_horizon = np.zeros((rows, cols), dtype=np.float64)

            for radius in range(1, max_radius_pixels + 1):
                dr = int(round(radius * np.cos(angle_rad)))
                dc = int(round(radius * np.sin(angle_rad)))

                if dr == 0 and dc == 0:
                    continue

                # Shifted DEM
                shifted = np.full_like(dem64, np.nan)
                src_r = slice(max(0, -dr), min(rows, rows - dr))
                src_c = slice(max(0, -dc), min(cols, cols - dc))
                dst_r = slice(max(0, dr), min(rows, rows + dr))
                dst_c = slice(max(0, dc), min(cols, cols + dc))
                shifted[dst_r, dst_c] = dem64[src_r, src_c]

                horizontal_dist = radius * pixel_size_m
                elevation_diff = shifted - dem64
                horizon_angle = np.arctan2(elevation_diff, horizontal_dist)

                valid = ~np.isnan(horizon_angle)
                max_horizon[valid] = np.maximum(max_horizon[valid], horizon_angle[valid])

            # SVF contribution from this direction
            svf -= np.clip(max_horizon, 0, np.pi / 2) / (n_directions * np.pi / 2)

        return np.clip(svf, 0, 1)

    def generate_all_products(
        self,
        dem: np.ndarray,
        pixel_size_m: float = 1.0,
    ) -> dict[str, np.ndarray]:
        """
        Generate all LiDAR-derived products for a DEM tile.

        Returns a dict of named raster arrays ready for storage or analysis.
        """
        products = {
            "hillshade_315": self.hillshade(dem, azimuth=315, pixel_size_m=pixel_size_m),
            "multi_hillshade": self.multi_hillshade(dem, pixel_size_m=pixel_size_m),
            "slope": self.slope_map(dem, pixel_size_m=pixel_size_m),
            "lrm_500m": self.local_relief_model(dem, pixel_size_m=pixel_size_m, window_m=500),
            "lrm_2000m": self.local_relief_model(dem, pixel_size_m=pixel_size_m, window_m=2000),
        }

        # SVF is expensive — only compute for small tiles or when requested
        if dem.size < 1_000_000:  # < 1M pixels
            products["svf"] = self.sky_view_factor(dem, pixel_size_m=pixel_size_m)

        return products
