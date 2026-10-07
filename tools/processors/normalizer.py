"""Step 2: Normalize scraped records to a common format."""

import logging
import math

logger = logging.getLogger("scraper")

# US bounding box (including Alaska)
US_MIN_LAT, US_MAX_LAT = 24.0, 72.0
US_MIN_LON, US_MAX_LON = -180.0, -66.0  # Alaska extends past -180

# Continental US bbox for state derivation
CONUS_MIN_LAT, CONUS_MAX_LAT = 24.0, 50.0
CONUS_MIN_LON, CONUS_MAX_LON = -125.0, -66.0

# State centroids for rough state assignment when coordinates are known but state is missing
STATE_CENTROIDS = {
    "AL": (32.8, -86.8), "AK": (64.2, -152.5), "AZ": (34.3, -111.7),
    "AR": (34.8, -92.2), "CA": (36.8, -119.4), "CO": (39.0, -105.5),
    "CT": (41.6, -72.7), "DE": (39.0, -75.5), "FL": (27.8, -81.7),
    "GA": (32.7, -83.5), "HI": (19.9, -155.6), "ID": (44.1, -114.7),
    "IL": (40.0, -89.2), "IN": (39.8, -86.1), "IA": (42.0, -93.5),
    "KS": (38.5, -98.3), "KY": (37.8, -84.3), "LA": (30.9, -91.9),
    "ME": (45.3, -69.4), "MD": (39.0, -76.6), "MA": (42.4, -71.4),
    "MI": (44.3, -84.5), "MN": (46.3, -94.3), "MS": (32.7, -89.7),
    "MO": (38.5, -92.3), "MT": (47.0, -109.6), "NE": (41.5, -99.8),
    "NV": (38.8, -116.4), "NH": (43.5, -71.5), "NJ": (40.1, -74.7),
    "NM": (34.5, -106.0), "NY": (43.0, -75.5), "NC": (35.6, -79.8),
    "ND": (47.5, -100.5), "OH": (40.4, -82.7), "OK": (35.5, -97.5),
    "OR": (43.8, -120.6), "PA": (41.0, -77.5), "RI": (41.6, -71.5),
    "SC": (33.8, -81.2), "SD": (44.5, -100.2), "TN": (35.9, -86.3),
    "TX": (31.5, -99.0), "UT": (39.3, -111.7), "VT": (44.0, -72.7),
    "VA": (37.5, -78.9), "WA": (47.5, -120.7), "WV": (38.5, -80.5),
    "WI": (43.8, -89.5), "WY": (43.0, -107.6),
}


def _derive_state(lat: float, lon: float) -> str:
    """Derive 2-letter state code from coordinates using nearest centroid."""
    best_state = ""
    best_dist = float("inf")
    for state, (slat, slon) in STATE_CENTROIDS.items():
        dist = math.sqrt((lat - slat) ** 2 + (lon - slon) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_state = state
    return best_state


def _is_valid_coord(lat: float, lon: float) -> bool:
    """Check if coordinates are valid US coordinates."""
    if lat is None or lon is None:
        return False
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if math.isnan(lat) or math.isnan(lon):
        return False
    if not (US_MIN_LAT <= lat <= US_MAX_LAT):
        return False
    if not (US_MIN_LON <= lon <= US_MAX_LON):
        return False
    return True


def _check_swapped(lat: float, lon: float) -> tuple[float, float] | None:
    """Check if lat/lon might be swapped and return corrected values."""
    if abs(lon) <= 90 and abs(lat) > 90:
        # Likely swapped
        if _is_valid_coord(lon, lat):
            return lon, lat
    return None


def normalize_record(record: dict, source: str) -> dict | None:
    """Normalize a single record to common format. Returns None if invalid."""
    lat = record.get("lat")
    lon = record.get("lon")

    if lat is None or lon is None:
        return None

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return None

    # Check for swapped coordinates
    if not _is_valid_coord(lat, lon):
        swapped = _check_swapped(lat, lon)
        if swapped:
            lat, lon = swapped
        else:
            return None

    name = str(record.get("name") or "").strip()
    site_type = str(record.get("site_type") or "").strip()

    # Must have at least a name or site type
    if not name and not site_type:
        return None

    state = str(record.get("state") or "").strip().upper()
    if len(state) != 2 or state not in STATE_CENTROIDS:
        state = _derive_state(lat, lon)

    period = str(record.get("period") or "").strip()
    source_id = str(record.get("source_id") or "").strip()
    description = str(record.get("description") or "").strip()

    # Confidence based on data completeness
    confidence = 0.5
    if name:
        confidence += 0.15
    if period:
        confidence += 0.1
    if site_type:
        confidence += 0.1
    if source_id:
        confidence += 0.05
    if description:
        confidence += 0.1
    confidence = min(confidence, 1.0)

    return {
        "name": name or f"Site at {lat:.4f}, {lon:.4f}",
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "state": state,
        "period": period,
        "site_type": site_type,
        "source": source,
        "source_id": source_id,
        "confidence": round(confidence, 2),
        "description": description[:500],
    }


def normalize_records(raw_records: list[dict], source: str) -> list[dict]:
    """Normalize a list of raw records. Discards invalid records."""
    normalized = []
    discarded = 0
    for rec in raw_records:
        norm = normalize_record(rec, source)
        if norm:
            normalized.append(norm)
        else:
            discarded += 1

    logger.info(
        f"[normalizer] {source}: {len(normalized)} normalized, {discarded} discarded "
        f"out of {len(raw_records)} raw"
    )
    return normalized
