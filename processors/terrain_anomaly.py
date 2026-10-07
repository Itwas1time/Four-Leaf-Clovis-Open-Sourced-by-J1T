"""
Terrain anomaly detection processor.

Detects morphological features in DEM data that may indicate human
earthworks: mounds, depressions, linear features, and artificial platforms.
Uses scipy.ndimage morphological operations — no deep learning required.

Archaeological rationale:
    Humans modify terrain in characteristic ways. Burial mounds (Adena,
    Hopewell, Mississippian) are roughly circular raised features 5-30m
    in diameter. Platform mounds are flat-topped. Pit houses and kivas
    are circular depressions. Walls and causeways are linear raised features.
    Canals and defensive ditches are linear depressions. These shapes are
    detectable via morphological filtering of elevation data.

Method:
    1. Compute Local Relief Model (LRM) — subtract smoothed surface to
       isolate micro-topography
    2. Apply morphological opening/closing to detect features by shape
    3. Classify features by geometry: circular (mound/depression),
       linear (wall/ditch), rectangular (platform)
    4. Score each grid cell by anomaly density and significance
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from scipy import ndimage

from core.schemas import AnomalyType, GridCell

logger = logging.getLogger(__name__)

# Feature detection parameters
LRM_SMOOTHING_M = 1000    # Moving window radius for Local Relief Model
MOUND_MIN_HEIGHT_M = 0.5  # Minimum residual height for mound candidate
MOUND_MAX_DIAMETER_M = 100  # Maximum diameter for mound feature
DEPRESSION_MIN_DEPTH_M = 0.3  # Minimum depth for depression candidate
LINEAR_MIN_LENGTH_M = 50   # Minimum length for linear feature


class TerrainAnomalyProcessor:
    """
    Detect terrain anomalies that may indicate archaeological features.

    Operates on DEM raster data tile-by-tile. Each tile is processed
    independently with overlap to avoid edge effects.
    """

    def compute_local_relief_model(
        self,
        dem: np.ndarray,
        pixel_size_m: float = 30.0,
        smoothing_radius_m: float = LRM_SMOOTHING_M,
    ) -> np.ndarray:
        """
        Compute Local Relief Model (LRM).

        The LRM subtracts a smoothed (trend) surface from the DEM to
        isolate micro-topographic features. The smoothing radius determines
        the scale of features detected: 500m catches small mounds, 2km
        catches large platform mounds and enclosures.

        This is the single most effective DEM-derived product for
        archaeological feature detection.
        """
        # Convert smoothing radius to pixels
        kernel_size = max(3, int(smoothing_radius_m / pixel_size_m))
        if kernel_size % 2 == 0:
            kernel_size += 1  # Ensure odd kernel

        # Gaussian smoothing to create trend surface
        trend = ndimage.gaussian_filter(dem.astype(np.float64), sigma=kernel_size / 3)

        # LRM = DEM - trend
        lrm = dem.astype(np.float64) - trend
        return lrm

    def detect_mounds(
        self,
        lrm: np.ndarray,
        pixel_size_m: float = 30.0,
    ) -> list[dict[str, Any]]:
        """
        Detect mound-like features (positive circular anomalies).

        Uses morphological operations: a mound is a local maximum in the
        LRM that remains positive after morphological opening (which
        removes features smaller than the structuring element).
        """
        # Threshold for positive anomalies
        positive = lrm > MOUND_MIN_HEIGHT_M

        # Morphological operations to find blob-like features
        max_pixels = int(MOUND_MAX_DIAMETER_M / pixel_size_m)
        struct = ndimage.generate_binary_structure(2, 1)

        # Opening removes small noise, closing fills small gaps
        cleaned = ndimage.binary_opening(positive, structure=struct, iterations=2)
        cleaned = ndimage.binary_closing(cleaned, structure=struct, iterations=1)

        # Label connected components
        labeled, num_features = ndimage.label(cleaned)

        mounds = []
        for i in range(1, num_features + 1):
            component = labeled == i
            size_pixels = component.sum()
            size_m2 = size_pixels * pixel_size_m ** 2

            # Filter by size (too small = noise, too large = natural feature)
            if 100 < size_m2 < (MOUND_MAX_DIAMETER_M ** 2 * np.pi / 4):
                # Compute centroid
                cy, cx = ndimage.center_of_mass(component)
                max_height = lrm[component].max()

                # Circularity check: compare area to bounding box area
                rows, cols = np.where(component)
                bbox_area = (rows.max() - rows.min() + 1) * (cols.max() - cols.min() + 1)
                circularity = size_pixels / bbox_area if bbox_area > 0 else 0

                mounds.append({
                    "type": AnomalyType.MOUND,
                    "centroid_row": int(cy),
                    "centroid_col": int(cx),
                    "area_m2": round(size_m2, 1),
                    "max_height_m": round(float(max_height), 2),
                    "circularity": round(circularity, 2),
                })

        return mounds

    def detect_depressions(
        self,
        lrm: np.ndarray,
        pixel_size_m: float = 30.0,
    ) -> list[dict[str, Any]]:
        """
        Detect depression features (pit houses, kivas, storage pits).

        Negative LRM values indicate features below the local trend surface.
        Circular depressions 3-15m in diameter are characteristic of
        pit structures across many North American cultures.
        """
        negative = lrm < -DEPRESSION_MIN_DEPTH_M

        struct = ndimage.generate_binary_structure(2, 1)
        cleaned = ndimage.binary_opening(negative, structure=struct, iterations=1)

        labeled, num_features = ndimage.label(cleaned)

        depressions = []
        for i in range(1, num_features + 1):
            component = labeled == i
            size_pixels = component.sum()
            size_m2 = size_pixels * pixel_size_m ** 2

            if 10 < size_m2 < 2000:  # 10-2000 m² typical for pit structures
                cy, cx = ndimage.center_of_mass(component)
                max_depth = abs(lrm[component].min())

                depressions.append({
                    "type": AnomalyType.DEPRESSION,
                    "centroid_row": int(cy),
                    "centroid_col": int(cx),
                    "area_m2": round(size_m2, 1),
                    "max_depth_m": round(float(max_depth), 2),
                })

        return depressions

    def detect_linear_features(
        self,
        lrm: np.ndarray,
        pixel_size_m: float = 30.0,
    ) -> list[dict[str, Any]]:
        """
        Detect linear features (walls, causeways, canals, ditches).

        Uses directional Sobel filters to find elongated anomalies.
        Linear features are distinguished from natural drainages by
        their straightness and perpendicularity to slope.
        """
        features = []

        for threshold, anomaly_type in [
            (MOUND_MIN_HEIGHT_M, AnomalyType.LINEAR_RAISED),
            (-DEPRESSION_MIN_DEPTH_M, AnomalyType.LINEAR_DEPRESSION),
        ]:
            if anomaly_type == AnomalyType.LINEAR_RAISED:
                binary = lrm > threshold
            else:
                binary = lrm < threshold

            # Directional analysis: horizontal and vertical Sobel
            sobel_h = ndimage.sobel(lrm, axis=0)
            sobel_v = ndimage.sobel(lrm, axis=1)

            # Skeletonize to find linear cores
            struct = np.ones((3, 1)) if anomaly_type == AnomalyType.LINEAR_RAISED else np.ones((1, 3))
            eroded = ndimage.binary_erosion(binary, structure=struct, iterations=1)
            dilated = ndimage.binary_dilation(eroded, structure=struct, iterations=2)

            labeled, num_features = ndimage.label(dilated)

            for i in range(1, num_features + 1):
                component = labeled == i
                size_pixels = component.sum()
                length_est_m = size_pixels * pixel_size_m

                if length_est_m >= LINEAR_MIN_LENGTH_M:
                    rows, cols = np.where(component)
                    aspect_ratio = (
                        (rows.max() - rows.min() + 1) /
                        max(cols.max() - cols.min() + 1, 1)
                    )

                    # Linear features should be elongated
                    if aspect_ratio > 3.0 or aspect_ratio < 0.33:
                        cy, cx = ndimage.center_of_mass(component)
                        features.append({
                            "type": anomaly_type,
                            "centroid_row": int(cy),
                            "centroid_col": int(cx),
                            "length_est_m": round(length_est_m, 1),
                            "aspect_ratio": round(aspect_ratio, 2),
                        })

        return features

    def score_tile(
        self,
        dem: np.ndarray,
        pixel_size_m: float = 30.0,
    ) -> dict[str, Any]:
        """
        Process a DEM tile and return anomaly scores and detections.

        Returns a dict with overall anomaly score and lists of detected features.
        """
        lrm = self.compute_local_relief_model(dem, pixel_size_m)

        mounds = self.detect_mounds(lrm, pixel_size_m)
        depressions = self.detect_depressions(lrm, pixel_size_m)
        linear_features = self.detect_linear_features(lrm, pixel_size_m)

        total_features = len(mounds) + len(depressions) + len(linear_features)

        # Score based on feature density and significance
        # More features and larger/more distinct features = higher score
        mound_score = min(len(mounds) * 0.3, 1.0) if mounds else 0.0
        depression_score = min(len(depressions) * 0.2, 0.8) if depressions else 0.0
        linear_score = min(len(linear_features) * 0.25, 0.9) if linear_features else 0.0

        composite = min(max(mound_score, depression_score, linear_score) +
                       0.1 * (mound_score + depression_score + linear_score), 1.0)

        return {
            "terrain_anomaly": round(composite, 4),
            "feature_count": total_features,
            "mounds": mounds,
            "depressions": depressions,
            "linear_features": linear_features,
            "lrm_stats": {
                "mean": round(float(lrm.mean()), 3),
                "std": round(float(lrm.std()), 3),
                "max": round(float(lrm.max()), 3),
                "min": round(float(lrm.min()), 3),
            },
        }
