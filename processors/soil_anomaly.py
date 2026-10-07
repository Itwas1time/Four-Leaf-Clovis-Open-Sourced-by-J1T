"""
Soil anomaly detection processor.

Identifies grid cells where soil properties deviate from natural baselines
in ways consistent with sustained human habitation (anthrosols).

Archaeological rationale:
    Human habitation modifies soil chemistry in persistent, detectable ways:
    - Elevated phosphorus from bone, food waste, excrement
    - Higher organic matter from charcoal, refuse, and cultural deposits
    - Darker color (melanization from charcoal and organic materials)
    - Altered pH (wood ash raises pH; organic decomposition lowers it)
    - Different texture (compaction from foot traffic, fill material)
    - Anomalous drainage (compacted floors, stone foundations)

    These modifications persist for millennia. The "terra preta" soils of
    Amazonia — created by Pre-Columbian populations — are still detectably
    different 2,000+ years later. In North America, similar anthrosols
    are found at Cahokia, Poverty Point, and thousands of smaller sites.

Method:
    Compare each soil map unit's properties against its local neighborhood.
    Deviations from the regional baseline suggest human modification.
    The USDA soil taxonomy system itself flags some: "Anthropic" and
    "Plaggen" classifications indicate recognized human-modified soils.
"""

from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from core.schemas import GridCell

logger = logging.getLogger(__name__)

# Anthropogenic indicator keywords in USDA soil taxonomy
ANTHROPIC_TAXONOMY_TERMS = [
    "anthropic", "plaggen", "anthro", "human",
    "urban", "fill", "dredge",
]

# Thresholds for anomaly detection
ORGANIC_MATTER_ZSCORE_THRESHOLD = 1.5
PH_ANOMALY_THRESHOLD = 0.8  # pH units deviation from neighborhood


class SoilAnomalyProcessor:
    """
    Detect anthropogenic soil signatures from SSURGO data.

    Each scoring method returns a component score (0-1). The composite
    soil_anomaly score combines these, with higher weight given to
    direct anthropogenic indicators (taxonomy classification, extreme
    organic matter anomalies) over indirect ones (drainage, pH).
    """

    def score_soil_unit(self, properties: dict[str, Any]) -> dict[str, Any]:
        """
        Score a single soil map unit for anthropogenic indicators.

        Args:
            properties: Dict of soil properties (from SSURGO).
                Expected keys: taxonomy_subgroup, organic_matter_pct,
                drainage_class, ph_value, parent_material.

        Returns:
            Dict with component scores and composite soil_anomaly score.
        """
        scores = {}

        # 1. Taxonomy classification check
        taxonomy = str(properties.get("taxonomy_subgroup", "")).lower()
        scores["taxonomy_score"] = self._taxonomy_score(taxonomy)

        # 2. Organic matter anomaly
        om_pct = properties.get("organic_matter_pct")
        om_regional_mean = properties.get("regional_om_mean")
        om_regional_std = properties.get("regional_om_std")
        scores["organic_matter_score"] = self._organic_matter_score(
            om_pct, om_regional_mean, om_regional_std
        )

        # 3. Drainage favorability (well-drained = preferred habitation)
        drainage = str(properties.get("drainage_class", "")).lower()
        scores["drainage_score"] = self._drainage_score(drainage)

        # 4. pH anomaly
        ph = properties.get("ph_value")
        ph_regional_mean = properties.get("regional_ph_mean")
        scores["ph_score"] = self._ph_score(ph, ph_regional_mean)

        # Composite: taxonomy is strongest (direct evidence), then OM, then others
        weighted = (
            scores["taxonomy_score"] * 0.35 +
            scores["organic_matter_score"] * 0.30 +
            scores["drainage_score"] * 0.20 +
            scores["ph_score"] * 0.15
        )
        scores["soil_anomaly"] = round(min(weighted, 1.0), 4)

        return scores

    def compute_regional_baselines(self, soil_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Add regional baseline statistics to a soil GeoDataFrame.

        Computes mean and std of key properties within each soil unit's
        neighborhood, enabling z-score anomaly detection.
        """
        if "organic_matter_pct" in soil_gdf.columns:
            vals = pd.to_numeric(soil_gdf["organic_matter_pct"], errors="coerce")
            soil_gdf["regional_om_mean"] = vals.mean()
            soil_gdf["regional_om_std"] = max(vals.std(), 0.1)

        if "ph_value" in soil_gdf.columns:
            vals = pd.to_numeric(soil_gdf["ph_value"], errors="coerce")
            soil_gdf["regional_ph_mean"] = vals.mean()

        return soil_gdf

    def _taxonomy_score(self, taxonomy: str) -> float:
        """
        Score based on soil taxonomy classification.

        USDA taxonomy flags human-modified soils explicitly. Finding an
        "Anthropic" or "Plaggen" classification is near-definitive evidence
        of sustained human land use.
        """
        if not taxonomy:
            return 0.0

        for term in ANTHROPIC_TAXONOMY_TERMS:
            if term in taxonomy:
                return 1.0

        # Some subgroups correlate with habitation without explicit anthropic label
        if "mollic" in taxonomy:
            return 0.3  # Dark, organic-rich — could be natural or cultural
        if "aquic" in taxonomy:
            return 0.1  # Wetland soils — less likely habitation

        return 0.0

    def _organic_matter_score(
        self,
        om_pct: float | None,
        regional_mean: float | None,
        regional_std: float | None,
    ) -> float:
        """
        Score organic matter content relative to regional baseline.

        Elevated OM in a localized area surrounded by lower OM strongly
        suggests cultural deposits (middens, occupation layers, garden beds).
        """
        if om_pct is None or regional_mean is None or regional_std is None:
            return 0.0

        try:
            om = float(om_pct)
            mean = float(regional_mean)
            std = float(regional_std)
        except (ValueError, TypeError):
            return 0.0

        if std < 0.01:
            return 0.0

        z_score = (om - mean) / std

        if z_score > 3.0:
            return 1.0  # Extreme anomaly
        elif z_score > ORGANIC_MATTER_ZSCORE_THRESHOLD:
            return 0.5 + (z_score - ORGANIC_MATTER_ZSCORE_THRESHOLD) / 3.0
        elif z_score > 0.5:
            return z_score * 0.3
        else:
            return 0.0

    def _drainage_score(self, drainage_class: str) -> float:
        """
        Score drainage class for habitation favorability.

        Well-drained soils on terraces above floodplains are the
        preferred habitation surface across most North American cultures.
        Poorly drained soils indicate floodplains or wetlands — used
        for resource extraction but not permanent settlement.
        """
        drainage_scores = {
            "excessively drained": 0.6,
            "somewhat excessively drained": 0.7,
            "well drained": 0.9,
            "moderately well drained": 0.7,
            "somewhat poorly drained": 0.3,
            "poorly drained": 0.1,
            "very poorly drained": 0.05,
        }
        return drainage_scores.get(drainage_class, 0.3)

    def _ph_score(self, ph: float | None, regional_mean: float | None) -> float:
        """
        Score pH deviation from regional baseline.

        Wood ash raises pH; organic decomposition lowers it. Both are
        signals of human activity when they deviate from the local norm.
        """
        if ph is None or regional_mean is None:
            return 0.0

        try:
            deviation = abs(float(ph) - float(regional_mean))
        except (ValueError, TypeError):
            return 0.0

        if deviation > PH_ANOMALY_THRESHOLD:
            return min(deviation / 2.0, 1.0)
        else:
            return deviation * 0.5
