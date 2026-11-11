"""The person's exact spot: from device location or a tap on the map (owner vision, 29 Oct 2026).

"Exact location is allowed: a typed address or GPS, kept only on the device, to give yard-level
answers." The spot lives in the browser's local storage and reaches only the local Clovis server
for these calculations; it is never written to reports, logs or exports unless the person saves it.
"""
import math

from core.us_places import _places

SOURCES = {"gps": "your device location", "map": "the point you chose on the map"}
NEAR_TOWN_KM = 40  # a spot further than this from the chosen town is treated as belonging elsewhere


def clean(spot):
    """A validated spot dict, or None. Coordinates are rounded to ~1 m."""
    if not isinstance(spot, dict) or spot.get("source") not in SOURCES:
        return None
    try:
        lat, lon = float(spot["lat"]), float(spot["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    cleaned = {"lat": round(lat, 5), "lon": round(lon, 5), "source": spot["source"]}
    accuracy = spot.get("accuracy_m")
    if isinstance(accuracy, (int, float)) and math.isfinite(accuracy) and 0 < accuracy < 100_000:
        cleaned["accuracy_m"] = round(float(accuracy))
    return cleaned


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1.0, a)))


def nearest_place(lat, lon, max_km=60):
    """The nearest public Census place point, or None when nothing is within ``max_km`` (outside the US)."""
    scale = math.cos(math.radians(lat))
    best = min(_places().values(), key=lambda row: (row["latitude"] - lat) ** 2 + ((row["longitude"] - lon) * scale) ** 2)
    km = distance_km(lat, lon, best["latitude"], best["longitude"])
    return {**dict(best), "distance_km": km} if km <= max_km else None


def for_place(spot, place):
    """The spot if it belongs with this town (within NEAR_TOWN_KM of its point), else None."""
    spot = clean(spot)
    if spot is None or not place:
        return None
    return spot if distance_km(spot["lat"], spot["lon"], place["latitude"], place["longitude"]) <= NEAR_TOWN_KM else None


def describe(spot):
    text = f"{spot['lat']:.5f}, {spot['lon']:.5f} from {SOURCES[spot['source']]}"
    return text + (f" (±{spot['accuracy_m']:,} m)" if spot.get("accuracy_m") else "")
