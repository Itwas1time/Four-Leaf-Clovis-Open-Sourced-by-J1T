"""
Cave and rockshelter probability predictor.

Estimates the likelihood of natural shelters (caves, rockshelters, lava tubes)
from geological formation data.

Archaeological rationale:
    Natural shelters have produced the oldest archaeological dates in North
    America: Meadowcroft Rockshelter (~19,000 BP), Paisley Caves (~14,500 BP),
    Bluefish Caves (~24,000 BP). Sheltered sites preserve organic materials
    that open-air sites destroy, making them disproportionately important for
    understanding early human occupation.

    Three geological processes create shelters:
    1. KARST dissolution: limestone/dolomite dissolves, forming caves (Mammoth
       Cave, Carlsbad Caverns). Predicted by: carbonate bedrock + hydrology.
    2. DIFFERENTIAL EROSION: sandstone or other resistant rock overlies weaker
       rock. The weak layer erodes, creating overhangs and rockshelters.
       Predicted by: layered sedimentary geology + cliff exposures.
    3. VOLCANIC TUBES: lava flows cool on the outside while still flowing
       inside, leaving tubes. Predicted by: basaltic volcanic formations.

    Aspect matters: south-facing shelters in cold climates receive more solar
    warming and are preferentially occupied. North-facing shelters in hot
    climates provide shade.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core.schemas import ShelterType

logger = logging.getLogger(__name__)

# Geological formations associated with shelter formation
KARST_LITHOLOGIES = [
    "limestone", "dolomite", "dolostone", "carbonate",
    "marble", "chalk", "travertine", "tufa",
]

ROCKSHELTER_LITHOLOGIES = [
    "sandstone", "conglomerate", "quartzite", "siltstone",
]

VOLCANIC_LITHOLOGIES = [
    "basalt", "andesite", "rhyolite", "tuff",
    "volcanic", "lava", "igneous",
]


class CavePredictor:
    """
    Predict cave/rockshelter probability from geological data.

    Combines bedrock lithology, slope/cliff exposure, and aspect
    to estimate shelter probability per grid cell.
    """

    def score_geology(
        self,
        lithology: str,
        formation_age: str = "",
    ) -> dict[str, Any]:
        """
        Score a geological unit for shelter-forming potential.

        Args:
            lithology: Rock type description from geologic map.
            formation_age: Geologic age (e.g., 'Mississippian', 'Cretaceous').

        Returns:
            Dict with shelter type probabilities and composite score.
        """
        lith_lower = lithology.lower()
        scores: dict[str, float] = {}

        # Karst potential
        karst_score = 0.0
        for term in KARST_LITHOLOGIES:
            if term in lith_lower:
                karst_score = 0.8
                # Older carbonates more likely to have developed karst
                if any(age in formation_age.lower() for age in
                       ["paleozoic", "mississippian", "ordovician", "cambrian", "silurian", "devonian"]):
                    karst_score = 0.9
                break
        scores["karst"] = karst_score

        # Rockshelter potential
        shelter_score = 0.0
        for term in ROCKSHELTER_LITHOLOGIES:
            if term in lith_lower:
                shelter_score = 0.7
                break
        scores["rockshelter"] = shelter_score

        # Lava tube potential
        volcanic_score = 0.0
        for term in VOLCANIC_LITHOLOGIES:
            if term in lith_lower:
                volcanic_score = 0.5
                if "basalt" in lith_lower:
                    volcanic_score = 0.7  # Basalt flows form tubes most readily
                break
        scores["lava_tube"] = volcanic_score

        # Composite: take the highest potential
        max_score = max(scores.values())
        shelter_type = None
        if max_score > 0:
            if scores["karst"] == max_score:
                shelter_type = ShelterType.CAVE_KARST
            elif scores["rockshelter"] == max_score:
                shelter_type = ShelterType.ROCKSHELTER_SANDSTONE
            else:
                shelter_type = ShelterType.LAVA_TUBE

        return {
            "karst_probability": scores["karst"],
            "rockshelter_probability": scores["rockshelter"],
            "lava_tube_probability": scores["lava_tube"],
            "shelter_probability": round(max_score, 4),
            "predicted_type": shelter_type.value if shelter_type else None,
        }

    def adjust_for_terrain(
        self,
        base_score: float,
        slope_degrees: float,
        aspect_degrees: float,
        latitude: float,
    ) -> float:
        """
        Adjust shelter probability based on terrain characteristics.

        Shelters require cliff exposures (high slope) and favorable aspect
        (south-facing in northern latitudes for solar warming). Flat terrain
        with shelter-forming geology still has SOME potential (underground
        caves), but surface shelters require steep slopes.
        """
        # Slope factor: shelters form at cliffs and steep exposures
        if slope_degrees > 45:
            slope_factor = 1.0  # Cliff face — ideal for shelters
        elif slope_degrees > 30:
            slope_factor = 0.8
        elif slope_degrees > 15:
            slope_factor = 0.5
        elif slope_degrees > 5:
            slope_factor = 0.2  # Gentle slope — underground caves possible
        else:
            slope_factor = 0.3  # Flat — karst caves still possible beneath

        # Aspect factor: south-facing preferred in temperate latitudes
        if latitude > 35:  # Northern temperate
            # South-facing (135-225°) gets solar warming bonus
            if 135 <= aspect_degrees <= 225:
                aspect_factor = 1.0
            elif 90 <= aspect_degrees <= 270:
                aspect_factor = 0.8
            else:
                aspect_factor = 0.6  # North-facing — cold, less preferred
        elif latitude < 30:  # Southern / tropical
            # North-facing provides shade in hot climates
            if aspect_degrees <= 45 or aspect_degrees >= 315:
                aspect_factor = 1.0
            else:
                aspect_factor = 0.8
        else:
            aspect_factor = 0.9  # Mild climate — aspect less critical

        adjusted = base_score * slope_factor * aspect_factor
        return round(min(adjusted, 1.0), 4)

    def score_cell(
        self,
        lithology: str,
        slope_degrees: float = 0.0,
        aspect_degrees: float = 180.0,
        latitude: float = 38.0,
        elevation_m: float = 0.0,
        distance_to_water_km: float = 0.0,
    ) -> dict[str, Any]:
        """
        Full shelter probability assessment for a grid cell.

        Combines geology, terrain, and proximity to water for a
        comprehensive shelter score. Water proximity matters because
        shelters far from water sources were rarely used for habitation
        (occasional use for storage or ritual, but not sustained living).
        """
        geo_scores = self.score_geology(lithology)
        base_score = geo_scores["shelter_probability"]

        if base_score > 0:
            # Terrain adjustment
            terrain_adjusted = self.adjust_for_terrain(
                base_score, slope_degrees, aspect_degrees, latitude
            )

            # Water proximity adjustment: shelters > 5km from water rarely habitated
            if distance_to_water_km < 1.0:
                water_factor = 1.0
            elif distance_to_water_km < 3.0:
                water_factor = 0.8
            elif distance_to_water_km < 5.0:
                water_factor = 0.5
            else:
                water_factor = 0.2

            final_score = terrain_adjusted * water_factor
        else:
            final_score = 0.0

        geo_scores["shelter_probability"] = round(final_score, 4)
        return geo_scores
