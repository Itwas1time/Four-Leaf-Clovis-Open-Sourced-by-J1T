"""
Geocode spatial references extracted from historical documents.

The hardest problem in historical text geocoding is that the same place
has different names across centuries, languages, and cultural contexts.
"Chillicothe" alone refers to at least 6 different settlements. "The
great mound" could be Cahokia, Grave Creek, Miamisburg, or dozens of
others. And relative references like "three days' march north" require
knowing the starting point, the travel mode, terrain, and historical
road/trail networks.

This resolver uses a layered strategy:
    1. Named places  -> GeoNames/GNIS gazetteer lookup
    2. Historical names -> period-appropriate name mapping
    3. Relative refs  -> anchor + direction + estimated travel distance
    4. Feature refs   -> spatial query against known landscape features

Each resolved location gets a confidence score (0-1) reflecting the
certainty of the geocoding.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from core.geo_utils import estimate_travel_distance_km, haversine_distance, EARTH_RADIUS_KM
from core.schemas import HistoricalReference, TimePeriod
from nlp.spatial_extractor import SpatialReferenceRaw

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

GEONAMES_API_URL = "http://api.geonames.org/searchJSON"
GEONAMES_USERNAME = "demo"  # Override with set_geonames_username()

GNIS_API_URL = "https://geonames.usgs.gov/api/search"

# Direction vectors (unit circle, geographic convention: N=0, E=90)
DIRECTION_BEARINGS: dict[str, float] = {
    "n": 0.0, "north": 0.0,
    "ne": 45.0, "northeast": 45.0,
    "e": 90.0, "east": 90.0,
    "se": 135.0, "southeast": 135.0,
    "s": 180.0, "south": 180.0,
    "sw": 225.0, "southwest": 225.0,
    "w": 270.0, "west": 270.0,
    "nw": 315.0, "northwest": 315.0,
    "upstream": None,   # Requires river flow data — resolved separately
    "downstream": None,
}


@dataclass
class ResolvedLocation:
    """A geocoded result for a spatial reference."""

    lat: float | None = None
    lon: float | None = None
    confidence: float = 0.0
    method: str = ""
    source: str = ""
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


# ------------------------------------------------------------------
# Distance parsing
# ------------------------------------------------------------------

def parse_distance_text(text: str) -> tuple[float | None, str, str]:
    """
    Parse a distance expression into (days_or_miles, unit, terrain).

    Handles expressions like:
        "three days march"      -> (3.0, "days", "mixed")
        "20 miles"              -> (20.0, "miles", "")
        "half a league"         -> (0.5, "leagues", "")
        "two days by canoe"     -> (2.0, "days", "canoe")

    Returns:
        (quantity, unit, modifier) or (None, "", "") if unparseable.
    """
    if not text:
        return None, "", ""

    text_lower = text.lower().strip()

    # Word-to-number mapping for common text quantities
    word_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "half": 0.5, "a": 1, "an": 1,
        "half a": 0.5, "quarter": 0.25,
    }

    # Try numeric pattern first
    numeric_match = re.search(r"(\d+(?:\.\d+)?)", text_lower)
    quantity: float | None = None

    if numeric_match:
        quantity = float(numeric_match.group(1))
    else:
        for word, val in sorted(word_numbers.items(), key=lambda x: -len(x[0])):
            if word in text_lower:
                quantity = val
                break

    if quantity is None:
        return None, "", ""

    # Determine unit
    unit = ""
    if "day" in text_lower:
        unit = "days"
    elif "mile" in text_lower:
        unit = "miles"
    elif "league" in text_lower:
        unit = "leagues"
    elif "hour" in text_lower:
        unit = "hours"
    elif "km" in text_lower or "kilometer" in text_lower:
        unit = "km"
    else:
        unit = "days"  # Default for ambiguous "three march" etc.

    # Determine terrain/mode modifier
    modifier = ""
    if "canoe" in text_lower or "boat" in text_lower:
        modifier = "canoe"
    elif "horse" in text_lower or "ride" in text_lower or "rode" in text_lower:
        modifier = "horse"
    elif "mountain" in text_lower or "steep" in text_lower:
        modifier = "mountain"
    elif "forest" in text_lower or "wood" in text_lower:
        modifier = "forest"
    else:
        modifier = "mixed"

    return quantity, unit, modifier


def distance_text_to_km(text: str) -> float | None:
    """
    Convert a textual distance expression to kilometers.

    Uses ethnographic travel rate estimates from geo_utils for
    time-based distances (days' march, etc.).
    """
    quantity, unit, modifier = parse_distance_text(text)
    if quantity is None:
        return None

    if unit == "km":
        return quantity
    elif unit == "miles":
        return quantity * 1.60934
    elif unit == "leagues":
        # Spanish league ~4.2 km, French league ~4.0 km; use ~4.2
        return quantity * 4.2
    elif unit == "hours":
        # Assume ~4 km/h walking speed
        return quantity * 4.0
    elif unit == "days":
        mode = "foot"
        terrain = modifier
        if modifier in ("canoe",):
            mode = "canoe"
            terrain = "downstream"  # Conservative default
        elif modifier in ("horse",):
            mode = "horse"
            terrain = "mixed"
        return estimate_travel_distance_km(quantity, mode=mode, terrain=terrain)

    return None


# ------------------------------------------------------------------
# Gazetteer lookup
# ------------------------------------------------------------------

class GazetteerClient:
    """
    Query GeoNames and GNIS for place name resolution.

    Archaeological rationale: Many historical place names persist in
    modern gazetteers (GNIS has >2 million US feature names). Even
    when the original site is gone, nearby geographic features often
    retain the historical name ("Mound City", "Indian Creek",
    "Serpent Mound Road"), providing approximate geocoding.
    """

    def __init__(
        self,
        geonames_username: str = GEONAMES_USERNAME,
        timeout: float = 15.0,
    ) -> None:
        self.geonames_username = geonames_username
        self.timeout = timeout

    def search_geonames(
        self,
        name: str,
        *,
        country: str = "US",
        max_rows: int = 5,
        feature_class: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search GeoNames gazetteer for a place name.

        Returns list of dicts with keys: name, lat, lon, feature_class,
        feature_code, country_code, admin_name, population.
        """
        params: dict[str, Any] = {
            "q": name,
            "country": country,
            "maxRows": max_rows,
            "username": self.geonames_username,
            "type": "json",
        }
        if feature_class:
            params["featureClass"] = feature_class

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(GEONAMES_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.warning("GeoNames lookup failed for '%s'", name)
            return []

        results: list[dict[str, Any]] = []
        for entry in data.get("geonames", []):
            results.append({
                "name": entry.get("name", ""),
                "lat": float(entry.get("lat", 0)),
                "lon": float(entry.get("lng", 0)),
                "feature_class": entry.get("fcl", ""),
                "feature_code": entry.get("fcode", ""),
                "country_code": entry.get("countryCode", ""),
                "admin_name": entry.get("adminName1", ""),
                "population": int(entry.get("population", 0)),
            })
        return results

    def search_gnis(
        self,
        name: str,
        *,
        state: str = "",
        feature_type: str = "",
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search USGS GNIS for US geographic feature names.

        GNIS is particularly valuable for archaeological geocoding because
        it includes historical names, locale names, and minor features
        (springs, summits, bends) that don't appear in GeoNames.
        """
        params: dict[str, Any] = {
            "term": name,
            "maxResults": max_results,
        }
        if state:
            params["state"] = state
        if feature_type:
            params["featureType"] = feature_type

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(GNIS_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.warning("GNIS lookup failed for '%s'", name)
            return []

        results: list[dict[str, Any]] = []
        features = data if isinstance(data, list) else data.get("features", [])
        for entry in features:
            coords = entry.get("geometry", {}).get("coordinates", [None, None])
            props = entry.get("properties", entry)
            results.append({
                "name": props.get("name", props.get("feature_name", "")),
                "lat": float(coords[1]) if coords[1] is not None else 0.0,
                "lon": float(coords[0]) if coords[0] is not None else 0.0,
                "feature_type": props.get("feature_type", ""),
                "state": props.get("state_name", props.get("state", "")),
                "county": props.get("county_name", props.get("county", "")),
            })
        return results


# ------------------------------------------------------------------
# Relative location computation
# ------------------------------------------------------------------

def compute_destination(
    lat: float,
    lon: float,
    bearing_deg: float,
    distance_km: float,
) -> tuple[float, float]:
    """
    Compute destination point given start, bearing, and distance.

    Uses the spherical law of cosines — accurate enough for the
    inherently imprecise distances we're working with (travel-time
    estimates have error bars of 30-50%).
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    bearing_r = math.radians(bearing_deg)
    d_ratio = distance_km / EARTH_RADIUS_KM

    dest_lat = math.asin(
        math.sin(lat_r) * math.cos(d_ratio)
        + math.cos(lat_r) * math.sin(d_ratio) * math.cos(bearing_r)
    )
    dest_lon = lon_r + math.atan2(
        math.sin(bearing_r) * math.sin(d_ratio) * math.cos(lat_r),
        math.cos(d_ratio) - math.sin(lat_r) * math.sin(dest_lat),
    )

    return (math.degrees(dest_lat), math.degrees(dest_lon))


# ------------------------------------------------------------------
# Main resolver
# ------------------------------------------------------------------

class ReferenceResolver:
    """
    Geocode spatial references extracted from historical documents.

    Takes SpatialReferenceRaw objects from the extractor and resolves
    them to latitude/longitude coordinates with confidence scores.
    Uses a layered strategy: gazetteer lookup -> historical name mapping
    -> relative reference computation -> feature-based spatial query.
    """

    def __init__(
        self,
        geonames_username: str = GEONAMES_USERNAME,
        timeout: float = 15.0,
    ) -> None:
        self.gazetteer = GazetteerClient(
            geonames_username=geonames_username,
            timeout=timeout,
        )
        # Cache of resolved place names to avoid redundant lookups
        self._place_cache: dict[str, ResolvedLocation] = {}

    def resolve(
        self,
        raw_ref: SpatialReferenceRaw,
        *,
        source_document: str = "",
        author: str = "",
        document_date: str = "",
    ) -> HistoricalReference:
        """
        Resolve a single spatial reference to a HistoricalReference.

        Tries resolution strategies in order of expected confidence:
            1. Named place gazetteer lookup
            2. Relative reference (anchor + direction + distance)
            3. Feature-based description matching

        Args:
            raw_ref: Extracted spatial reference from the LLM.
            source_document: Document title for the output record.
            author: Document author.
            document_date: Document date.

        Returns:
            HistoricalReference with coordinates and confidence filled in.
        """
        resolved = ResolvedLocation()

        # Strategy 1: Named place lookup
        if raw_ref.place_name:
            resolved = self._resolve_named_place(raw_ref.place_name, raw_ref.place_type)

        # Strategy 2: Relative reference
        if resolved.confidence < 0.5 and raw_ref.relative_anchor:
            relative_result = self._resolve_relative(
                anchor_name=raw_ref.relative_anchor,
                direction=raw_ref.relative_direction,
                distance_text=raw_ref.relative_distance_text,
            )
            if relative_result.confidence > resolved.confidence:
                resolved = relative_result

        # Strategy 3: Feature description (use as name search fallback)
        if resolved.confidence < 0.3 and raw_ref.feature_description:
            feature_result = self._resolve_feature_description(
                raw_ref.feature_description
            )
            if feature_result.confidence > resolved.confidence:
                resolved = feature_result

        # Build HistoricalReference
        time_period: TimePeriod | None = None
        if raw_ref.time_period:
            try:
                time_period = TimePeriod(raw_ref.time_period)
            except ValueError:
                pass

        described_features: list[str] = []
        if raw_ref.structure_description:
            described_features.append(raw_ref.structure_description)
        if raw_ref.feature_description:
            described_features.append(raw_ref.feature_description)
        if raw_ref.place_type:
            described_features.append(raw_ref.place_type)

        return HistoricalReference(
            source_document=source_document,
            author=author,
            document_date=document_date,
            extracted_text=raw_ref.extracted_passage,
            resolved_lat=resolved.lat,
            resolved_lon=resolved.lon,
            resolution_method=resolved.method,
            confidence=min(resolved.confidence, raw_ref.extraction_confidence),
            time_period=time_period,
            described_features=described_features,
        )

    def resolve_batch(
        self,
        raw_refs: list[SpatialReferenceRaw],
        *,
        source_document: str = "",
        author: str = "",
        document_date: str = "",
    ) -> list[HistoricalReference]:
        """Resolve a list of spatial references."""
        return [
            self.resolve(
                ref,
                source_document=source_document,
                author=author,
                document_date=document_date,
            )
            for ref in raw_refs
        ]

    # ------------------------------------------------------------------
    # Resolution strategies
    # ------------------------------------------------------------------

    def _resolve_named_place(
        self, name: str, place_type: str = ""
    ) -> ResolvedLocation:
        """
        Resolve a named place via gazetteer lookup.

        Checks cache first, then tries GeoNames and GNIS. Assigns higher
        confidence when the returned feature type matches the expected
        place_type from the extraction.
        """
        cache_key = f"{name.lower()}:{place_type.lower()}"
        if cache_key in self._place_cache:
            return self._place_cache[cache_key]

        # Try GeoNames first (global coverage)
        geonames_results = self.gazetteer.search_geonames(name)

        # Also try GNIS (better for minor US features)
        gnis_results = self.gazetteer.search_gnis(name)

        best = ResolvedLocation(method="gazetteer")

        # Score GeoNames results
        for entry in geonames_results:
            conf = self._score_gazetteer_match(name, place_type, entry, source="geonames")
            if conf > best.confidence:
                best = ResolvedLocation(
                    lat=entry["lat"],
                    lon=entry["lon"],
                    confidence=conf,
                    method="gazetteer",
                    source=f"geonames:{entry.get('name', '')}",
                    alternatives=[e for e in geonames_results if e != entry],
                )

        # Score GNIS results
        for entry in gnis_results:
            conf = self._score_gazetteer_match(name, place_type, entry, source="gnis")
            if conf > best.confidence:
                best = ResolvedLocation(
                    lat=entry["lat"],
                    lon=entry["lon"],
                    confidence=conf,
                    method="gazetteer",
                    source=f"gnis:{entry.get('name', '')}",
                    alternatives=[e for e in gnis_results if e != entry],
                )

        self._place_cache[cache_key] = best
        return best

    def _resolve_relative(
        self,
        anchor_name: str,
        direction: str,
        distance_text: str,
    ) -> ResolvedLocation:
        """
        Resolve a relative reference: anchor + direction + distance.

        First resolves the anchor to coordinates, then computes the
        destination point using the stated direction and estimated
        travel distance. Confidence is reduced because of the
        compounding uncertainty (anchor location + distance estimate).
        """
        # Resolve the anchor place
        anchor = self._resolve_named_place(anchor_name)
        if anchor.lat is None or anchor.lon is None or anchor.confidence < 0.3:
            return ResolvedLocation(
                method="relative",
                notes=f"Could not resolve anchor '{anchor_name}'",
            )

        # Parse direction
        direction_lower = direction.lower().strip()
        bearing = DIRECTION_BEARINGS.get(direction_lower)
        if bearing is None:
            return ResolvedLocation(
                lat=anchor.lat,
                lon=anchor.lon,
                confidence=anchor.confidence * 0.3,
                method="relative",
                notes=f"Unknown direction '{direction}'; using anchor location",
            )

        # Parse distance
        distance_km = distance_text_to_km(distance_text)
        if distance_km is None:
            # Use anchor with reduced confidence if distance is unparseable
            return ResolvedLocation(
                lat=anchor.lat,
                lon=anchor.lon,
                confidence=anchor.confidence * 0.3,
                method="relative",
                notes=f"Could not parse distance '{distance_text}'; using anchor",
            )

        # Compute destination
        dest_lat, dest_lon = compute_destination(
            anchor.lat, anchor.lon, bearing, distance_km
        )

        # Confidence: anchor confidence * 0.6 (distance uncertainty is large)
        return ResolvedLocation(
            lat=dest_lat,
            lon=dest_lon,
            confidence=anchor.confidence * 0.6,
            method="relative",
            source=f"relative to {anchor_name} ({direction}, ~{distance_km:.0f}km)",
            notes=f"Bearing {bearing}deg, distance {distance_km:.1f}km from anchor",
        )

    def _resolve_feature_description(
        self, description: str
    ) -> ResolvedLocation:
        """
        Attempt to resolve a location from a landscape description.

        Extracts keywords from the description (confluence, bluff, mound,
        spring, etc.) and searches gazetteers for matching features.
        This is the lowest-confidence strategy — it's a last resort.
        """
        # Extract searchable keywords from the description
        keywords = self._extract_feature_keywords(description)
        if not keywords:
            return ResolvedLocation(method="feature-match")

        # Search for the most specific keyword combination
        search_term = " ".join(keywords[:3])
        results = self.gazetteer.search_geonames(search_term)

        if not results:
            results = self.gazetteer.search_gnis(search_term)

        if not results:
            return ResolvedLocation(method="feature-match")

        # Take the first result with low confidence
        entry = results[0]
        return ResolvedLocation(
            lat=entry.get("lat", 0.0),
            lon=entry.get("lon", 0.0),
            confidence=0.25,  # Low — feature matching is inherently uncertain
            method="feature-match",
            source=f"feature search: '{search_term}'",
            alternatives=results[1:],
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_gazetteer_match(
        query_name: str,
        expected_type: str,
        entry: dict[str, Any],
        source: str = "",
    ) -> float:
        """
        Score a gazetteer match based on name similarity and type match.

        Higher scores for exact name matches and matching feature types.
        """
        entry_name = entry.get("name", "").lower()
        query_lower = query_name.lower()

        # Base confidence from name match quality
        if entry_name == query_lower:
            confidence = 0.85
        elif query_lower in entry_name or entry_name in query_lower:
            confidence = 0.65
        else:
            confidence = 0.40

        # Boost for matching feature type
        if expected_type:
            feature_type = entry.get("feature_type", entry.get("feature_code", "")).lower()
            if expected_type.lower() in feature_type or feature_type in expected_type.lower():
                confidence = min(confidence + 0.10, 1.0)

        # Small boost for populated places (more likely to be the "famous" one)
        population = entry.get("population", 0)
        if population > 10000:
            confidence = min(confidence + 0.05, 1.0)

        return confidence

    @staticmethod
    def _extract_feature_keywords(description: str) -> list[str]:
        """
        Pull searchable geographic keywords from a feature description.

        Prioritizes terms that appear in gazetteers: confluence, fork,
        bluff, mound, spring, falls, rapids, gap, pass, etc.
        """
        gazetteer_terms = {
            "confluence", "fork", "forks", "junction", "mouth",
            "bluff", "bluffs", "cliff", "cliffs", "ridge",
            "mound", "mounds", "earthwork", "earthworks",
            "spring", "springs", "falls", "rapids",
            "gap", "pass", "narrows", "bend",
            "island", "creek", "river", "lake", "pond",
            "terrace", "floodplain", "valley", "hollow",
            "cave", "shelter", "overhang",
        }

        words = re.findall(r"\b\w+\b", description.lower())
        keywords = [w for w in words if w in gazetteer_terms]

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique
