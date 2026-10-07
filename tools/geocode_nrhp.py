#!/usr/bin/env python3
"""
NRHP Geocoding Pipeline

Geocodes 25,658 archaeological records from the NPS Excel bulk download
using a waterfall strategy: MapServer -> Google -> Census -> County -> City -> State centroids.

Usage:
    python tools/geocode_nrhp.py --all              # Full waterfall: MapServer -> Google -> Census -> County -> City -> State
    python tools/geocode_nrhp.py --method mapserver  # MapServer cross-reference only (free)
    python tools/geocode_nrhp.py --method google     # Google API only (for unmatched)
    python tools/geocode_nrhp.py --method census     # Census API only (free, slow)
    python tools/geocode_nrhp.py --method offline    # County + City + State centroids only
    python tools/geocode_nrhp.py --status            # Show geocoding progress
    python tools/geocode_nrhp.py --embed             # Feed geocoded records into FOURLEAFCLOVIS pipeline
    python tools/geocode_nrhp.py --dry-run --all     # Preview without writing
"""

import argparse
import csv
import io
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
RAW_DIR = TOOLS_DIR / "raw_scrapes"
PROCESSED_DIR = TOOLS_DIR / "processed"
CACHE_DIR = TOOLS_DIR / "geocode_cache"
LOG_FILE = TOOLS_DIR / "geocode_nrhp.log"

OUTPUT_FILE = PROCESSED_DIR / "nrhp_geocoded.json"
CHECKPOINT_FILE = CACHE_DIR / "geocode_checkpoint.json"
MAPSERVER_CACHE = CACHE_DIR / "mapserver_all.json"
COUNTY_CENTROID_FILE = CACHE_DIR / "county_centroids.csv"
CITY_CENTROID_FILE = CACHE_DIR / "city_centroids.csv"
EXCEL_CACHE = CACHE_DIR / "nrhp_excel_cache.xlsx"

CACHE_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("geocoder")
logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(_fh)
logger.addHandler(_ch)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NPS_MAPSERVER = "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0"

NPS_XLSX_URLS = [
    "https://www.nps.gov/subjects/nationalregister/upload/national-register-listed_20250624.xlsx",
    "https://www.nps.gov/subjects/nationalregister/upload/national-register-listed.xlsx",
]

GOOGLE_GEOCODER = "https://maps.googleapis.com/maps/api/geocode/json"
CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/address"
COUNTY_CENTROID_URL = "https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt"
CITY_CENTROID_URL = "https://www2.census.gov/geo/docs/reference/cenpop2020/place/CenPop2020_Mean_PL.txt"

ARCHEO_KEYWORDS = (
    "archeo", "archaeo", "prehist", "archeolog", "archaeolog",
    "mound", "shell ring", "earthwork", "rock shelter", "cave",
    "pueblo", "cliff dwelling", "petroglyph", "pictograph",
    "burial", "village site", "campsite", "quarry",
)

STATE_ABBREVS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    "american samoa": "AS", "guam": "GU", "northern mariana islands": "MP",
    "puerto rico": "PR", "u.s. virgin islands": "VI", "virgin islands": "VI",
}

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
    "WI": (43.8, -89.5), "WY": (43.0, -107.6), "DC": (38.9, -77.0),
    "PR": (18.2, -66.5), "VI": (18.3, -64.9), "GU": (13.4, 144.8),
    "AS": (-14.3, -170.7), "MP": (15.2, 145.7),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_abbrev(name: str) -> str:
    if not name:
        return ""
    name = name.strip()
    if len(name) <= 2:
        return name.upper()
    return STATE_ABBREVS.get(name.lower(), name[:2].upper())


def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    import re
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _name_similarity(a: str, b: str) -> float:
    """Quick token-overlap similarity between two names."""
    ta = set(_normalize_name(a).split())
    tb = set(_normalize_name(b).split())
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    return overlap / max(len(ta), len(tb))


# ---------------------------------------------------------------------------
# Phase 0: Download the NPS Excel and extract archaeological records
# ---------------------------------------------------------------------------

def download_excel() -> Path:
    """Download the NPS Excel file (or use cached copy)."""
    if EXCEL_CACHE.exists():
        size_mb = EXCEL_CACHE.stat().st_size / 1024 / 1024
        logger.info(f"Using cached Excel: {EXCEL_CACHE} ({size_mb:.1f} MB)")
        return EXCEL_CACHE

    session = requests.Session()
    session.headers["User-Agent"] = "FOURLEAFCLOVIS-Geocoder/1.0 (archaeological research)"

    for url in NPS_XLSX_URLS:
        try:
            logger.info(f"Downloading Excel from {url}...")
            resp = session.get(url, timeout=180, stream=True)
            resp.raise_for_status()
            EXCEL_CACHE.write_bytes(resp.content)
            size_mb = len(resp.content) / 1024 / 1024
            logger.info(f"Downloaded {size_mb:.1f} MB -> {EXCEL_CACHE}")
            return EXCEL_CACHE
        except Exception as e:
            logger.warning(f"Download failed ({url}): {e}")

    raise RuntimeError("Could not download NPS Excel from any URL")


def parse_excel_archaeological(xlsx_path: Path) -> list[dict]:
    """Parse Excel into archaeological records with address fields for geocoding."""
    import openpyxl

    logger.info(f"Parsing Excel: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows)]
    logger.info(f"Excel headers: {headers}")

    # Build column map
    col = {}
    for i, h in enumerate(headers):
        hl = h.lower().strip()
        if "property name" in hl or hl in ("resource name", "resname", "name"):
            col["name"] = i
        elif hl in ("state", "st"):
            col["state"] = i
        elif hl == "county":
            col["county"] = i
        elif hl == "city":
            col["city"] = i
        elif "street" in hl or hl == "address":
            col["street"] = i
        elif "area of significance" in hl or (hl.startswith("area") and "significance" in hl):
            col["significance"] = i
        elif "category" in hl and "property" in hl:
            col["category"] = i
        elif hl in ("latitude", "lat"):
            col["lat"] = i
        elif hl in ("longitude", "lon", "long"):
            col["lon"] = i

    logger.info(f"Column mapping: {col}")

    if "name" not in col:
        # Fallback: use first non-ID column
        for i, h in enumerate(headers):
            if h and h not in ("", "ref#", "prefix", "refnum", "nris_refnum"):
                col["name"] = i
                break

    records = []
    total = 0
    for row in rows:
        total += 1
        if not row:
            continue

        def _get(key: str) -> str:
            idx = col.get(key)
            if idx is None or idx >= len(row) or row[idx] is None:
                return ""
            return str(row[idx]).strip()

        name = _get("name")
        state = _get("state")
        county = _get("county")
        city = _get("city")
        street = _get("street")
        significance = _get("significance")
        category = _get("category")

        # Filter for archaeological records
        combined = f"{name} {category} {significance}".lower()
        is_site = category.lower() in ("site", "district")
        is_archeo = any(kw in combined for kw in ARCHEO_KEYWORDS)

        if not (is_site or is_archeo):
            continue

        # Grab existing coords if the Excel has them
        lat_raw = _get("lat")
        lon_raw = _get("lon")
        lat, lon = None, None
        if lat_raw:
            try:
                lat = float(lat_raw)
            except (ValueError, TypeError):
                pass
        if lon_raw:
            try:
                lon = float(lon_raw)
            except (ValueError, TypeError):
                pass

        state_code = _state_abbrev(state) if state else ""

        records.append({
            "name": name or "Unknown NRHP Site",
            "state": state_code,
            "county": county,
            "city": city,
            "street": street,
            "significance": significance[:500],
            "category": category,
            "excel_lat": lat,
            "excel_lon": lon,
            "source_id": f"nrhp_excel_{total}",
        })

    wb.close()
    logger.info(f"Excel: {total} total rows, {len(records)} archaeological records")
    return records


# ---------------------------------------------------------------------------
# Phase 1: Cross-reference against NPS MapServer
# ---------------------------------------------------------------------------

def fetch_mapserver_all() -> list[dict]:
    """Fetch ALL 72,668 records from NPS MapServer (not just archaeological).
    Cache locally so we only do this once."""

    if MAPSERVER_CACHE.exists():
        with open(MAPSERVER_CACHE) as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} MapServer records from cache")
        return data

    logger.info("Fetching ALL records from NPS MapServer (72,668 expected)...")
    session = requests.Session()
    session.headers["User-Agent"] = "FOURLEAFCLOVIS-Geocoder/1.0 (archaeological research)"

    records = []
    offset = 0
    batch_size = 2000

    while True:
        params = {
            "where": "1=1",
            "outFields": "RESNAME,ResType,State,County,City,Address",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }

        try:
            resp = session.get(f"{NPS_MAPSERVER}/query", params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"MapServer fetch failed at offset {offset}: {e}")
            if records:
                break
            raise

        features = data.get("features", [])
        if not features:
            break

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            if not geom or geom.get("type") != "Point":
                continue
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue

            records.append({
                "name": props.get("RESNAME") or "",
                "state": _state_abbrev(props.get("State") or ""),
                "county": props.get("County") or "",
                "city": props.get("City") or "",
                "lat": coords[1],
                "lon": coords[0],
            })

        offset += len(features)
        logger.info(f"MapServer: fetched {offset} total ({len(records)} with geometry)")

        if len(features) < batch_size:
            break
        time.sleep(0.3)

    # Cache
    with open(MAPSERVER_CACHE, "w") as f:
        json.dump(records, f)
    logger.info(f"Cached {len(records)} MapServer records to {MAPSERVER_CACHE}")
    return records


def cross_reference_mapserver(excel_records: list[dict], mapserver_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Match Excel records against MapServer by name+state.
    Returns (matched, unmatched) where matched records have coordinates."""

    # Build lookup: (normalized_name, state) -> list of mapserver records
    ms_index: dict[tuple[str, str], list[dict]] = {}
    for rec in mapserver_records:
        key = (_normalize_name(rec["name"]), rec["state"].upper())
        ms_index.setdefault(key, []).append(rec)

    # Also build a state-only index for fuzzy matching
    ms_by_state: dict[str, list[dict]] = {}
    for rec in mapserver_records:
        ms_by_state.setdefault(rec["state"].upper(), []).append(rec)

    matched = []
    unmatched = []
    match_count_exact = 0
    match_count_fuzzy = 0

    for erec in excel_records:
        norm_name = _normalize_name(erec["name"])
        state = erec["state"].upper()

        # Exact name+state match
        key = (norm_name, state)
        if key in ms_index:
            ms_rec = ms_index[key][0]
            matched.append({
                **erec,
                "lat": ms_rec["lat"],
                "lon": ms_rec["lon"],
                "geocode_method": "mapserver_exact",
                "geocode_confidence": 0.95,
            })
            match_count_exact += 1
            continue

        # Fuzzy: find best name match within same state
        best_sim = 0.0
        best_ms = None
        candidates = ms_by_state.get(state, [])
        for ms_rec in candidates:
            sim = _name_similarity(erec["name"], ms_rec["name"])
            if sim > best_sim:
                best_sim = sim
                best_ms = ms_rec

        if best_sim >= 0.75 and best_ms:
            matched.append({
                **erec,
                "lat": best_ms["lat"],
                "lon": best_ms["lon"],
                "geocode_method": "mapserver_fuzzy",
                "geocode_confidence": round(0.95 * best_sim, 2),
            })
            match_count_fuzzy += 1
        else:
            unmatched.append(erec)

    logger.info(
        f"MapServer cross-reference: {match_count_exact} exact + {match_count_fuzzy} fuzzy = "
        f"{match_count_exact + match_count_fuzzy} matched, {len(unmatched)} unmatched"
    )
    return matched, unmatched


# ---------------------------------------------------------------------------
# Phase 2: Google Geocoding API
# ---------------------------------------------------------------------------

CONFIG_FILE = TOOLS_DIR / "config.json"


def _load_google_api_key() -> str:
    """Load Google Geocoding API key from config.json."""
    if not CONFIG_FILE.exists():
        raise RuntimeError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    key = config.get("google_geocoding_api_key", "")
    if not key:
        raise RuntimeError("google_geocoding_api_key not set in config.json")
    return key


def geocode_google_api(record: dict, api_key: str, session: requests.Session) -> dict | None:
    """Try Google Geocoding API. Returns record with coords or None."""
    name = record.get("name", "").strip()
    city = record.get("city", "").strip()
    county = record.get("county", "").strip()
    state = record.get("state", "").strip()
    street = record.get("street", "").strip()

    # Build address string — most specific to least specific
    parts = []
    if street:
        parts.append(street)
    if name:
        parts.append(name)
    if city:
        parts.append(city)
    if county:
        parts.append(county)
    if state:
        parts.append(state)

    if not parts:
        return None

    address = ", ".join(parts)

    try:
        resp = session.get(GOOGLE_GEOCODER, params={"address": address, "key": api_key}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            lat = loc["lat"]
            lng = loc["lng"]
            if lat and lng:
                return {
                    **record,
                    "lat": lat,
                    "lon": lng,
                    "geocode_method": "google",
                    "geocode_confidence": 0.93,
                }

        # If name-based search failed, try without name (just location)
        if name and (city or county):
            fallback_parts = []
            if city:
                fallback_parts.append(city)
            if county:
                fallback_parts.append(county)
            if state:
                fallback_parts.append(state)
            fallback_address = ", ".join(fallback_parts)

            resp2 = session.get(GOOGLE_GEOCODER, params={"address": fallback_address, "key": api_key}, timeout=15)
            resp2.raise_for_status()
            data2 = resp2.json()

            if data2.get("status") == "OK" and data2.get("results"):
                loc2 = data2["results"][0]["geometry"]["location"]
                lat2 = loc2["lat"]
                lng2 = loc2["lng"]
                if lat2 and lng2:
                    return {
                        **record,
                        "lat": lat2,
                        "lon": lng2,
                        "geocode_method": "google_locality",
                        "geocode_confidence": 0.85,
                    }

    except Exception as e:
        logger.debug(f"Google API failed for {record.get('name', '?')}: {e}")

    return None


GOOGLE_RESULTS_CACHE = CACHE_DIR / "google_results.jsonl"


def geocode_batch_google(records: list[dict], checkpoint_offset: int = 0) -> tuple[list[dict], list[dict], int]:
    """Geocode records via Google API with rate limiting and checkpoints.
    Saves results incrementally to a JSONL cache file.
    Returns (geocoded, failed, total_api_calls)."""

    api_key = _load_google_api_key()
    session = requests.Session()
    session.headers["User-Agent"] = "FOURLEAFCLOVIS-Geocoder/1.0 (archaeological research)"

    # Load any previously cached Google results
    cached_ids = set()
    geocoded = []
    if GOOGLE_RESULTS_CACHE.exists():
        with open(GOOGLE_RESULTS_CACHE) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    geocoded.append(rec)
                    cached_ids.add(rec.get("source_id"))
        logger.info(f"Loaded {len(geocoded)} cached Google results")

    failed = []
    total = len(records)
    api_calls = 0
    batch_start = time.time()
    skipped = 0

    with open(GOOGLE_RESULTS_CACHE, "a") as cache_f:
        for i, rec in enumerate(records):
            if i < checkpoint_offset:
                continue

            # Skip if already in cache
            if rec.get("source_id") in cached_ids:
                skipped += 1
                continue

            result = geocode_google_api(rec, api_key, session)
            api_calls += 1

            if result:
                geocoded.append(result)
                # Write to cache immediately
                cache_f.write(json.dumps(result) + "\n")
                cache_f.flush()
            else:
                failed.append(rec)

            # Rate limit: ~40 requests/second (conservative under 50/sec limit)
            time.sleep(0.025)

            # Progress + checkpoint every 100
            done = i + 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - batch_start
                rate = (done - skipped) / elapsed if elapsed > 0 else 0
                est_cost = api_calls * 0.005  # $5 per 1000 requests
                logger.info(
                    f"Google API: {done}/{total} processed ({skipped} cached), "
                    f"{len(geocoded)} geocoded, {len(failed)} failed, "
                    f"~${est_cost:.2f} spent, {rate:.1f} rec/sec"
                )
                _save_checkpoint({
                    "phase": "google_api",
                    "offset": done,
                    "geocoded_count": len(geocoded),
                    "failed_count": len(failed),
                    "api_calls": api_calls,
                })

    if skipped:
        logger.info(f"Skipped {skipped} records already in Google cache")
    logger.info(f"Google API complete: {len(geocoded)} geocoded, {len(failed)} failed, {api_calls} new API calls")
    return geocoded, failed, api_calls


# ---------------------------------------------------------------------------
# Phase 3: Census API geocoding
# ---------------------------------------------------------------------------

def geocode_census_api(record: dict, session: requests.Session) -> dict | None:
    """Try Census Geocoder API. Returns record with coords or None."""
    street = record.get("street", "").strip()
    city = record.get("city", "").strip()
    state = record.get("state", "").strip()

    if not street and not city:
        return None

    params = {
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }

    # Try with full address first
    if street:
        params["street"] = street
    if city:
        params["city"] = city
    if state:
        params["state"] = state

    try:
        resp = session.get(CENSUS_GEOCODER, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("result", {}).get("addressMatches", [])
        if results:
            coords = results[0].get("coordinates", {})
            lat = coords.get("y")
            lon = coords.get("x")
            if lat and lon:
                return {
                    **record,
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "census_api",
                    "geocode_confidence": 0.90,
                }

        # If street failed, try city+state only (less precise but still useful)
        if street and city:
            params2 = {
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
                "street": city,  # Census sometimes takes city as street
                "state": state,
            }
            time.sleep(0.5)
            resp2 = session.get(CENSUS_GEOCODER, params=params2, timeout=30)
            resp2.raise_for_status()
            data2 = resp2.json()
            results2 = data2.get("result", {}).get("addressMatches", [])
            if results2:
                coords = results2[0].get("coordinates", {})
                lat = coords.get("y")
                lon = coords.get("x")
                if lat and lon:
                    return {
                        **record,
                        "lat": lat,
                        "lon": lon,
                        "geocode_method": "census_api_city",
                        "geocode_confidence": 0.80,
                    }

    except Exception as e:
        logger.debug(f"Census API failed for {record.get('name', '?')}: {e}")

    return None


def geocode_batch_census(records: list[dict], checkpoint_offset: int = 0) -> tuple[list[dict], list[dict]]:
    """Geocode records via Census API with rate limiting and checkpoints.
    Returns (geocoded, failed)."""

    session = requests.Session()
    session.headers["User-Agent"] = "FOURLEAFCLOVIS-Geocoder/1.0 (archaeological research)"

    geocoded = []
    failed = []
    total = len(records)

    for i, rec in enumerate(records):
        if i < checkpoint_offset:
            continue

        result = geocode_census_api(rec, session)
        if result:
            geocoded.append(result)
        else:
            failed.append(rec)

        # Rate limit: 1 request per second
        time.sleep(1.0)

        # Progress + checkpoint every 100
        done = i + 1
        if done % 100 == 0 or done == total:
            logger.info(
                f"Census API: {done}/{total} processed, "
                f"{len(geocoded)} geocoded, {len(failed)} failed"
            )
            _save_checkpoint({
                "phase": "census_api",
                "offset": done,
                "geocoded_count": len(geocoded),
                "failed_count": len(failed),
            })

    logger.info(f"Census API complete: {len(geocoded)} geocoded, {len(failed)} failed")
    return geocoded, failed


# ---------------------------------------------------------------------------
# Phase 3: County centroid fallback
# ---------------------------------------------------------------------------

def download_county_centroids() -> dict[tuple[str, str], tuple[float, float]]:
    """Download Census county centroids. Returns {(state, county_lower): (lat, lon)}."""
    if COUNTY_CENTROID_FILE.exists():
        logger.info(f"Loading cached county centroids: {COUNTY_CENTROID_FILE}")
    else:
        logger.info(f"Downloading county centroids from {COUNTY_CENTROID_URL}...")
        resp = requests.get(COUNTY_CENTROID_URL, timeout=60)
        resp.raise_for_status()
        COUNTY_CENTROID_FILE.write_bytes(resp.content)
        logger.info(f"Saved county centroids to {COUNTY_CENTROID_FILE}")

    centroids = {}
    with open(COUNTY_CENTROID_FILE, encoding="latin-1") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Columns: STATEFP, COUNTYFP, COUNAME, STNAME, POPULATION, LATITUDE, LONGITUDE
        # Actual header names vary; find them by content
        h_lower = [h.strip().upper() for h in header]

        idx_state = None
        idx_county = None
        idx_lat = None
        idx_lon = None

        for i, h in enumerate(h_lower):
            if h in ("STNAME", "STATE_NAME"):
                idx_state = i
            elif h in ("STATEFP",):
                if idx_state is None:
                    idx_state = i  # Will be FIPS, convert later
            elif h in ("COUNAME", "COUNTY_NAME", "COUNTYNAME"):
                idx_county = i
            elif h in ("LATITUDE", "LAT"):
                idx_lat = i
            elif h in ("LONGITUDE", "LON", "LONG"):
                idx_lon = i

        if idx_lat is None or idx_lon is None:
            # Try positional: STATEFP, COUNTYFP, COUNAME, STNAME, POP, LAT, LON
            idx_state = 3  # STNAME
            idx_county = 2  # COUNAME
            idx_lat = 5
            idx_lon = 6

        for row in reader:
            try:
                if len(row) <= max(idx_state, idx_county, idx_lat, idx_lon):
                    continue
                state_name = row[idx_state].strip()
                county_name = row[idx_county].strip()
                lat = float(row[idx_lat].strip())
                lon = float(row[idx_lon].strip())

                state_code = _state_abbrev(state_name)
                # Strip trailing " County", " Parish", etc.
                county_clean = county_name.lower()
                for suffix in (" county", " parish", " borough", " census area",
                               " municipality", " city and borough", " city"):
                    county_clean = county_clean.removesuffix(suffix)
                county_clean = county_clean.strip()

                centroids[(state_code, county_clean)] = (lat, lon)
            except (ValueError, IndexError):
                continue

    logger.info(f"Loaded {len(centroids)} county centroids")
    return centroids


def geocode_county_centroid(records: list[dict], centroids: dict) -> tuple[list[dict], list[dict]]:
    """Geocode records using county centroids. Returns (geocoded, failed)."""
    geocoded = []
    failed = []

    for rec in records:
        state = rec.get("state", "").upper()
        county_raw = rec.get("county", "").lower().strip()
        if not county_raw or not state:
            failed.append(rec)
            continue

        # Strip suffix
        county_clean = county_raw
        for suffix in (" county", " parish", " borough", " census area",
                       " municipality", " city and borough", " city"):
            county_clean = county_clean.removesuffix(suffix)
        county_clean = county_clean.strip()

        key = (state, county_clean)
        if key in centroids:
            lat, lon = centroids[key]
            geocoded.append({
                **rec,
                "lat": lat,
                "lon": lon,
                "geocode_method": "county_centroid",
                "geocode_confidence": 0.6,
            })
        else:
            failed.append(rec)

    logger.info(f"County centroid: {len(geocoded)} geocoded, {len(failed)} failed")
    return geocoded, failed


# ---------------------------------------------------------------------------
# Phase 4: City centroid fallback
# ---------------------------------------------------------------------------

def download_city_centroids() -> dict[tuple[str, str], tuple[float, float]]:
    """Download Census city/place centroids. Returns {(state_fips, city_lower): (lat, lon)}."""
    if CITY_CENTROID_FILE.exists() and CITY_CENTROID_FILE.stat().st_size > 1000:
        logger.info(f"Loading cached city centroids: {CITY_CENTROID_FILE}")
    else:
        logger.info(f"Downloading city centroids from {CITY_CENTROID_URL}...")
        try:
            resp = requests.get(CITY_CENTROID_URL, timeout=30)
            resp.raise_for_status()
            # Verify it's actual CSV data, not an error page
            content = resp.content
            if b"<!DOCTYPE" in content[:200] or len(content) < 1000:
                logger.warning("City centroid URL returned error page or empty data, skipping")
                return {}
            CITY_CENTROID_FILE.write_bytes(content)
            logger.info(f"Saved city centroids to {CITY_CENTROID_FILE}")
        except Exception as e:
            logger.warning(f"Could not download city centroids: {e} — skipping")
            return {}

    # Build FIPS -> state abbrev mapping
    fips_to_state = {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
        "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
        "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
        "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
        "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
        "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
        "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
        "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
        "56": "WY", "72": "PR", "78": "VI",
    }

    centroids = {}
    with open(CITY_CENTROID_FILE, encoding="latin-1") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Columns: STATEFP, PLACEFP, POPULATION, LATITUDE, LONGITUDE, PLACENAME, STNAME
        h_upper = [h.strip().upper() for h in header]

        idx_statefp = None
        idx_place = None
        idx_lat = None
        idx_lon = None

        for i, h in enumerate(h_upper):
            if h == "STATEFP":
                idx_statefp = i
            elif h in ("PLACENAME", "PLACE_NAME", "NAME"):
                idx_place = i
            elif h in ("LATITUDE", "LAT"):
                idx_lat = i
            elif h in ("LONGITUDE", "LON", "LONG"):
                idx_lon = i
            elif h == "STNAME":
                if idx_place is None:
                    pass  # state name, not place name

        # Fallback positional
        if idx_lat is None:
            idx_statefp = 0
            idx_place = 5
            idx_lat = 3
            idx_lon = 4

        for row in reader:
            try:
                if len(row) <= max(idx_statefp, idx_place, idx_lat, idx_lon):
                    continue
                statefp = row[idx_statefp].strip()
                place_name = row[idx_place].strip()
                lat = float(row[idx_lat].strip())
                lon = float(row[idx_lon].strip())

                state_code = fips_to_state.get(statefp, "")
                if not state_code:
                    continue

                # Clean place name
                city_clean = place_name.lower()
                for suffix in (" city", " town", " village", " cdp",
                               " (balance)", " municipality", " borough"):
                    city_clean = city_clean.removesuffix(suffix)
                city_clean = city_clean.strip()

                centroids[(state_code, city_clean)] = (lat, lon)
            except (ValueError, IndexError):
                continue

    logger.info(f"Loaded {len(centroids)} city centroids")
    return centroids


def geocode_city_centroid(records: list[dict], centroids: dict) -> tuple[list[dict], list[dict]]:
    """Geocode records using city centroids. Returns (geocoded, failed)."""
    geocoded = []
    failed = []

    for rec in records:
        state = rec.get("state", "").upper()
        city_raw = rec.get("city", "").lower().strip()
        if not city_raw or not state:
            failed.append(rec)
            continue

        # Clean city name
        city_clean = city_raw
        for suffix in (" city", " town", " village", " cdp",
                       " (balance)", " municipality", " borough"):
            city_clean = city_clean.removesuffix(suffix)
        city_clean = city_clean.strip()

        key = (state, city_clean)
        if key in centroids:
            lat, lon = centroids[key]
            geocoded.append({
                **rec,
                "lat": lat,
                "lon": lon,
                "geocode_method": "city_centroid",
                "geocode_confidence": 0.5,
            })
        else:
            failed.append(rec)

    logger.info(f"City centroid: {len(geocoded)} geocoded, {len(failed)} failed")
    return geocoded, failed


# ---------------------------------------------------------------------------
# Phase 5: State centroid (last resort)
# ---------------------------------------------------------------------------

def geocode_state_centroid(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Last resort: use state centroid. Returns (geocoded, failed)."""
    geocoded = []
    failed = []

    for rec in records:
        state = rec.get("state", "").upper()
        if state in STATE_CENTROIDS:
            lat, lon = STATE_CENTROIDS[state]
            geocoded.append({
                **rec,
                "lat": lat,
                "lon": lon,
                "geocode_method": "state_centroid",
                "geocode_confidence": 0.3,
            })
        else:
            failed.append(rec)

    logger.info(f"State centroid: {len(geocoded)} geocoded, {len(failed)} failed")
    return geocoded, failed


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def _save_checkpoint(state: dict):
    state["timestamp"] = str(datetime.now())
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _load_existing_geocoded() -> list[dict]:
    """Load previously geocoded records from output file."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        return data.get("records", [])
    return []


def _load_checkpoint() -> dict | None:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_geocoded(records: list[dict]):
    """Save geocoded records to output file."""
    # Clean up internal fields before saving
    cleaned = []
    for rec in records:
        out = {
            "name": rec.get("name", ""),
            "lat": rec.get("lat"),
            "lon": rec.get("lon"),
            "site_type": rec.get("category", rec.get("site_type", "site")).upper() or "SITE",
            "period": "",
            "state": rec.get("state", ""),
            "source_id": rec.get("source_id", ""),
            "description": rec.get("significance", rec.get("description", "")),
            "geocode_method": rec.get("geocode_method", ""),
            "geocode_confidence": rec.get("geocode_confidence", 0.0),
            "county": rec.get("county", ""),
            "city": rec.get("city", ""),
        }
        cleaned.append(out)

    output = {
        "source": "nrhp_geocoded",
        "geocode_date": str(datetime.now()),
        "record_count": len(cleaned),
        "records": cleaned,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Saved {len(cleaned)} geocoded records to {OUTPUT_FILE}")


def show_status():
    """Show geocoding progress."""
    print(f"\n{'='*60}")
    print("NRHP Geocoding Status")
    print(f"{'='*60}")

    # Check output file
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        total = data.get("record_count", 0)
        records = data.get("records", [])
        date = data.get("geocode_date", "?")

        print(f"\nOutput: {OUTPUT_FILE}")
        print(f"Date: {date}")
        print(f"Total geocoded records: {total}")

        # Breakdown by method
        methods = {}
        for rec in records:
            m = rec.get("geocode_method", "unknown")
            methods[m] = methods.get(m, 0) + 1

        print(f"\nBy method:")
        for m, count in sorted(methods.items(), key=lambda x: -x[1]):
            pct = 100 * count / total if total else 0
            conf_desc = {
                "mapserver_exact": "high (0.95)",
                "mapserver_fuzzy": "high (0.71-0.95)",
                "google": "high (0.93)",
                "google_locality": "high (0.85)",
                "census_api": "high (0.90)",
                "census_api_city": "medium (0.80)",
                "county_centroid": "medium (0.60)",
                "city_centroid": "low (0.50)",
                "state_centroid": "low (0.30)",
            }.get(m, "?")
            print(f"  {m:<25} {count:>7} ({pct:5.1f}%)  confidence: {conf_desc}")

        # Breakdown by state (top 10)
        states = {}
        for rec in records:
            s = rec.get("state", "??")
            states[s] = states.get(s, 0) + 1
        print(f"\nTop 10 states:")
        for s, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
            print(f"  {s}: {count}")
    else:
        print("\nNo geocoded output yet.")

    # Check checkpoint
    cp = _load_checkpoint()
    if cp:
        print(f"\nCheckpoint: phase={cp.get('phase')}, offset={cp.get('offset')}, time={cp.get('timestamp')}")
        if cp.get("api_calls"):
            est_cost = cp["api_calls"] * 0.005
            print(f"  Google API calls so far: {cp['api_calls']} (~${est_cost:.2f})")

    # Check caches
    print(f"\nCaches:")
    for name, path in [
        ("MapServer", MAPSERVER_CACHE),
        ("County centroids", COUNTY_CENTROID_FILE),
        ("City centroids", CITY_CENTROID_FILE),
        ("Excel", EXCEL_CACHE),
    ]:
        if path.exists():
            size = path.stat().st_size / 1024
            unit = "KB"
            if size > 1024:
                size /= 1024
                unit = "MB"
            print(f"  {name:<20} CACHED  ({size:.1f} {unit})")
        else:
            print(f"  {name:<20} not downloaded")

    print()


# ---------------------------------------------------------------------------
# Embed integration
# ---------------------------------------------------------------------------

def embed_geocoded():
    """Feed geocoded records through the existing FOURLEAFCLOVIS pipeline."""
    if not OUTPUT_FILE.exists():
        logger.error(f"No geocoded data at {OUTPUT_FILE}. Run --all first.")
        return

    with open(OUTPUT_FILE) as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        logger.warning("No records to embed")
        return

    # Convert to the format expected by the raw scrape pipeline
    # Save as a raw scrape file so scrape_databases.py --process --embed picks it up
    raw_output = {
        "source": "nrhp_geocoded",
        "url": "geocode_nrhp.py",
        "scrape_date": str(datetime.now()),
        "record_count": len(records),
        "records": records,
    }

    raw_file = RAW_DIR / "nrhp_geocoded.json"
    with open(raw_file, "w") as f:
        json.dump(raw_output, f, indent=2)
    logger.info(f"Wrote {len(records)} records to {raw_file}")

    # Now run process + embed
    logger.info("Running normalize -> classify -> dedup -> embed pipeline...")

    from tools.processors.normalizer import normalize_records
    from tools.processors.classifier import classify_records
    from tools.processors.deduplicator import deduplicate_records
    from tools.processors.embedder import embed_records

    normalized = normalize_records(records, "nrhp_geocoded")
    logger.info(f"Normalized: {len(normalized)} records")

    classified = classify_records(normalized)
    logger.info(f"Classified: {len(classified)} records")

    # Load existing sites for dedup
    existing_sites = []
    try:
        from atlas.gui.data.known_sites_expanded import get_known_sites_geojson
        geojson = get_known_sites_geojson()
        for feat in geojson["features"]:
            props = feat["properties"]
            coords = feat["geometry"]["coordinates"]
            existing_sites.append((props["name"], coords[0], coords[1]))
    except Exception as e:
        logger.warning(f"Could not load existing sites for dedup: {e}")

    deduped = deduplicate_records(classified, existing_sites if existing_sites else None)
    logger.info(f"Deduplicated: {len(deduped)} records")

    results = embed_records(deduped)
    for layer, count in results.items():
        if count:
            logger.info(f"  Embedded {layer}: +{count}")

    logger.info("Embedding complete!")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_full_pipeline(dry_run: bool = False):
    """Run the complete geocoding pipeline."""

    logger.info("=" * 60)
    logger.info("NRHP Geocoding Pipeline - Full Run")
    logger.info("=" * 60)

    start_time = time.time()

    # Step 1: Download and parse Excel
    logger.info("\n--- Phase 0: Download & parse NPS Excel ---")
    xlsx_path = download_excel()
    excel_records = parse_excel_archaeological(xlsx_path)
    logger.info(f"Extracted {len(excel_records)} archaeological records from Excel")

    if dry_run:
        logger.info(f"[DRY RUN] Would geocode {len(excel_records)} records")
        return

    all_geocoded = []
    google_api_calls = 0

    # Check for existing partial results to resume from
    existing = _load_existing_geocoded()
    existing_ids = {r.get("source_id") for r in existing if r.get("lat") is not None}
    if existing_ids:
        logger.info(f"Found {len(existing_ids)} previously geocoded records — will skip these")
        already_done = [r for r in existing if r.get("source_id") in existing_ids]
        all_geocoded.extend(already_done)
        excel_records = [r for r in excel_records if r.get("source_id") not in existing_ids]
        logger.info(f"Remaining to geocode: {len(excel_records)}")

    # Step 2: Cross-reference with MapServer
    logger.info("\n--- Phase 1: Cross-reference NPS MapServer ---")
    mapserver_records = fetch_mapserver_all()
    matched, remaining = cross_reference_mapserver(excel_records, mapserver_records)
    all_geocoded.extend(matched)
    logger.info(f"MapServer matched: {len(matched)}, remaining: {len(remaining)}")

    # Save after MapServer phase
    save_geocoded(all_geocoded)
    logger.info(f"Saved {len(all_geocoded)} records after MapServer phase")

    # Step 3: Google Geocoding API for remaining unmatched records
    logger.info("\n--- Phase 2: Google Geocoding API ---")
    google_api_calls = 0
    if remaining:
        cp = _load_checkpoint()
        offset = 0
        if cp and cp.get("phase") == "google_api":
            offset = cp.get("offset", 0)
            logger.info(f"Resuming Google API from offset {offset}")

        google_ok, google_fail, google_api_calls = geocode_batch_google(remaining, checkpoint_offset=offset)
        all_geocoded.extend(google_ok)
        remaining = google_fail
        logger.info(f"Google API: {len(google_ok)} geocoded, {len(google_fail)} failed -> Census fallback")

        # Save after Google phase
        save_geocoded(all_geocoded)
        logger.info(f"Saved {len(all_geocoded)} records after Google phase")
    else:
        remaining = []

    # Step 4: Census API geocoding for remaining records with addresses
    logger.info("\n--- Phase 3: Census API geocoding ---")
    has_address = [r for r in remaining if r.get("street")]
    no_address = [r for r in remaining if not r.get("street")]
    logger.info(f"Records with street addresses: {len(has_address)}")
    logger.info(f"Records without street addresses: {len(no_address)}")

    if has_address:
        cp = _load_checkpoint()
        offset = 0
        if cp and cp.get("phase") == "census_api":
            offset = cp.get("offset", 0)
            logger.info(f"Resuming Census API from offset {offset}")

        census_ok, census_fail = geocode_batch_census(has_address, checkpoint_offset=offset)
        all_geocoded.extend(census_ok)
        no_address.extend(census_fail)
        logger.info(f"Census API: {len(census_ok)} geocoded, {len(census_fail)} failed -> fallback pool")

    # Step 5: County centroid fallback
    logger.info("\n--- Phase 4: County centroid fallback ---")
    county_centroids = download_county_centroids()
    county_ok, county_fail = geocode_county_centroid(no_address, county_centroids)
    all_geocoded.extend(county_ok)

    # Step 6: City centroid fallback
    logger.info("\n--- Phase 5: City centroid fallback ---")
    city_centroids = download_city_centroids()
    city_ok, city_fail = geocode_city_centroid(county_fail, city_centroids)
    all_geocoded.extend(city_ok)

    # Step 7: State centroid (last resort)
    logger.info("\n--- Phase 6: State centroid (last resort) ---")
    state_ok, state_fail = geocode_state_centroid(city_fail)
    all_geocoded.extend(state_ok)

    # Summary
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("GEOCODING COMPLETE")
    logger.info(f"Total geocoded: {len(all_geocoded)} / {len(excel_records)}")
    logger.info(f"Unresolved: {len(state_fail)}")
    logger.info(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")

    methods = {}
    for r in all_geocoded:
        m = r.get("geocode_method", "?")
        methods[m] = methods.get(m, 0) + 1
    for m, c in sorted(methods.items(), key=lambda x: -x[1]):
        logger.info(f"  {m}: {c}")

    # Cost estimate
    if google_api_calls > 0:
        est_cost = google_api_calls * 0.005  # $5 per 1000 requests
        logger.info(f"\nGoogle API: {google_api_calls} requests = ~${est_cost:.2f}")

    # Save
    save_geocoded(all_geocoded)

    # Clean up checkpoint
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def run_method_only(method: str, dry_run: bool = False):
    """Run a single geocoding method."""
    logger.info(f"Running single method: {method}")

    xlsx_path = download_excel()
    excel_records = parse_excel_archaeological(xlsx_path)

    if dry_run:
        logger.info(f"[DRY RUN] Would geocode {len(excel_records)} records with method={method}")
        return

    if method == "mapserver":
        ms = fetch_mapserver_all()
        matched, unmatched = cross_reference_mapserver(excel_records, ms)
        save_geocoded(matched)

    elif method == "google":
        # Load existing geocoded to find unmatched records
        existing = _load_existing_geocoded()
        geocoded_ids = {r.get("source_id") for r in existing}
        unmatched = [r for r in excel_records if r.get("source_id") not in geocoded_ids]
        logger.info(f"{len(unmatched)} records not yet geocoded, sending to Google API")
        if unmatched:
            google_ok, google_fail, api_calls = geocode_batch_google(unmatched)
            # Merge with existing
            all_records = existing + google_ok
            save_geocoded(all_records)
            est_cost = api_calls * 0.005
            logger.info(f"Google API: {api_calls} requests = ~${est_cost:.2f}")
        else:
            logger.info("All records already geocoded!")

    elif method == "census":
        existing = _load_existing_geocoded()
        geocoded_ids = {r.get("source_id") for r in existing}
        unmatched = [r for r in excel_records if r.get("source_id") not in geocoded_ids]
        has_address = [r for r in unmatched if r.get("street")]
        logger.info(f"{len(has_address)} unmatched records have addresses for Census API")
        if has_address:
            census_ok, census_fail = geocode_batch_census(has_address)
            all_records = existing + census_ok
            save_geocoded(all_records)

    elif method == "offline":
        # Run county + city + state centroids on unmatched records
        existing = _load_existing_geocoded()
        geocoded_ids = {r.get("source_id") for r in existing}
        unmatched = [r for r in excel_records if r.get("source_id") not in geocoded_ids]
        logger.info(f"{len(unmatched)} records for offline geocoding")

        county_centroids = download_county_centroids()
        county_ok, county_fail = geocode_county_centroid(unmatched, county_centroids)

        city_centroids = download_city_centroids()
        city_ok, city_fail = geocode_city_centroid(county_fail, city_centroids)

        state_ok, state_fail = geocode_state_centroid(city_fail)

        all_records = existing + county_ok + city_ok + state_ok
        save_geocoded(all_records)
        logger.info(f"Offline: +{len(county_ok)} county, +{len(city_ok)} city, +{len(state_ok)} state")

    else:
        logger.error(f"Unknown method: {method}. Choose: mapserver, google, census, offline")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NRHP Geocoding Pipeline - geocode 25,658 archaeological records"
    )
    parser.add_argument("--all", action="store_true",
                        help="Run full waterfall: MapServer -> Google -> Census -> County -> City -> State")
    parser.add_argument("--method", type=str,
                        help="Run single method: mapserver, google, census, offline")
    parser.add_argument("--status", action="store_true",
                        help="Show geocoding progress and statistics")
    parser.add_argument("--embed", action="store_true",
                        help="Feed geocoded records into FOURLEAFCLOVIS pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing data")

    args = parser.parse_args()

    if not any([args.all, args.method, args.status, args.embed]):
        parser.print_help()
        return

    if args.status:
        show_status()
        return

    if args.embed:
        embed_geocoded()
        return

    if args.all:
        run_full_pipeline(dry_run=args.dry_run)
    elif args.method:
        run_method_only(args.method, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
