"""Convert scraped tribal/indigenous data into embedded Python data files.

Reads raw scrape JSON from tools/raw_scrapes/ and writes:
  - atlas/gui/data/tribal_boundaries.py   (TIGER AIANNH legal boundaries)
  - atlas/gui/data/native_territories.py  (combined historical + legal territories)
"""

import json
import logging
import textwrap
from pathlib import Path

logger = logging.getLogger("scraper")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "atlas" / "gui" / "data"
RAW_DIR = Path(__file__).resolve().parent.parent / "raw_scrapes"

# Sovereignty note included in both data files
SOVEREIGNTY_NOTE = (
    "IMPORTANT: Tribal boundaries shown here are approximate and derived from "
    "US Census Bureau TIGER/Line data and Native Land Digital. These boundaries "
    "do not represent legal determinations of tribal territory. Researchers and "
    "land managers should consult directly with tribal nations before conducting "
    "any work on or near tribal lands. Tribal sovereignty and self-determination "
    "must be respected in all archaeological and research activities."
)


def _round_coords(coords, precision=4):
    """Recursively round coordinates to reduce file size."""
    if isinstance(coords, (int, float)):
        return round(coords, precision)
    return [_round_coords(c, precision) for c in coords]


def _simplify_geometry(geom_dict: dict) -> dict:
    """Round coordinates in a GeoJSON geometry dict."""
    if not geom_dict:
        return geom_dict
    result = dict(geom_dict)
    if "coordinates" in result:
        result["coordinates"] = _round_coords(result["coordinates"])
    return result


def _load_raw(source_id: str) -> list[dict]:
    """Load raw scrape records for a source."""
    path = RAW_DIR / f"{source_id}.json"
    if not path.exists():
        logger.info(f"[tribal_embedder] No raw data for {source_id}")
        return []
    with open(path) as f:
        data = json.load(f)
    records = data.get("records", [])
    logger.info(f"[tribal_embedder] Loaded {len(records)} records from {source_id}")
    return records


def embed_tribal_boundaries() -> int:
    """Generate tribal_boundaries.py from TIGER AIANNH data.

    Returns the number of features embedded.
    """
    records = _load_raw("tiger_aiannh")
    if not records:
        logger.warning("[tribal_embedder] No TIGER AIANNH data to embed")
        return 0

    features = []
    for rec in records:
        geom = rec.get("geometry")
        if not geom:
            continue

        land_sqm = rec.get("land_area_sqm", 0)
        land_sqkm = round(land_sqm / 1_000_000, 2) if land_sqm else 0

        feature = {
            "type": "Feature",
            "properties": {
                "name": rec["name"],
                "code": rec.get("code", ""),
                "boundary_type": rec.get("boundary_type", "unknown"),
                "land_area_sqkm": land_sqkm,
                "source": "US Census Bureau TIGER/Line AIANNH 2023",
            },
            "geometry": _simplify_geometry(geom),
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    # Write as Python module
    out_path = DATA_DIR / "tribal_boundaries.py"
    _write_geojson_module(
        out_path,
        "tribal_boundaries",
        "get_tribal_boundaries_geojson",
        geojson,
        docstring=(
            "Return GeoJSON FeatureCollection of federally recognized tribal boundaries.\n"
            "\n"
            "Source: US Census Bureau TIGER/Line AIANNH shapefile (2023).\n"
            f"Contains {len(features)} American Indian, Alaska Native, and Native Hawaiian areas.\n"
            "\n"
            f"{SOVEREIGNTY_NOTE}"
        ),
    )

    logger.info(f"[tribal_embedder] Wrote {len(features)} tribal boundaries to {out_path}")
    return len(features)


def embed_native_territories() -> int:
    """Generate native_territories.py combining all sources.

    Merges TIGER legal boundaries with Native Land historical territories,
    BIA trust land, and EPA cession boundaries.

    Returns the number of features embedded.
    """
    features = []
    seen_names = set()

    # 1. TIGER AIANNH as "current legal" boundaries
    tiger_records = _load_raw("tiger_aiannh")
    for rec in tiger_records:
        geom = rec.get("geometry")
        if not geom:
            continue
        name = rec["name"]
        land_sqm = rec.get("land_area_sqm", 0)
        land_sqkm = round(land_sqm / 1_000_000, 2) if land_sqm else 0

        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "native_name": "",
                "territory_type": rec.get("boundary_type", "reservation"),
                "is_current_legal": True,
                "is_historical": False,
                "source": "US Census TIGER/Line 2023",
                "land_area_sqkm": land_sqkm,
            },
            "geometry": _simplify_geometry(geom),
        })
        seen_names.add(name.lower())

    # 2. Native Land Digital territories (historical)
    nl_records = _load_raw("native_land")
    for rec in nl_records:
        geom = rec.get("geometry")
        if not geom:
            continue
        layer = rec.get("layer", "territories")
        name = rec.get("name", "Unknown")

        territory_type_map = {
            "territories": "historical_territory",
            "languages": "language_area",
            "treaties": "treaty_boundary",
        }

        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "native_name": rec.get("native_name", ""),
                "territory_type": territory_type_map.get(layer, "historical_territory"),
                "is_current_legal": False,
                "is_historical": True,
                "source": "Native Land Digital",
                "slug": rec.get("slug", ""),
                "description": rec.get("description", ""),
            },
            "geometry": _simplify_geometry(geom),
        })

    # 3. BIA trust land
    bia_records = _load_raw("bia_tribal")
    for rec in bia_records:
        geom = rec.get("geometry")
        if not geom:
            continue
        name = rec.get("name", "Unknown")
        # Skip if we already have this from TIGER (avoid duplicates)
        if name.lower() in seen_names:
            continue

        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "native_name": "",
                "territory_type": "trust_land",
                "is_current_legal": True,
                "is_historical": False,
                "source": "BIA AIAN National LAR",
            },
            "geometry": _simplify_geometry(geom),
        })

    # 4. EPA tribal layers (especially cession boundaries)
    epa_records = _load_raw("epa_tribal")
    for rec in epa_records:
        geom = rec.get("geometry")
        if not geom:
            continue
        layer = rec.get("layer", "")
        name = rec.get("name", "Unknown")

        is_historical = layer == "tribal_cession_boundaries"
        territory_type = "cession_boundary" if is_historical else "federal_tribal_area"

        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "native_name": "",
                "territory_type": territory_type,
                "is_current_legal": not is_historical,
                "is_historical": is_historical,
                "source": "EPA Tribal ArcGIS",
                "epa_layer": layer,
            },
            "geometry": _simplify_geometry(geom),
        })

    geojson = {"type": "FeatureCollection", "features": features}

    out_path = DATA_DIR / "native_territories.py"
    _write_geojson_module(
        out_path,
        "native_territories",
        "get_native_territories_geojson",
        geojson,
        docstring=(
            "Return GeoJSON FeatureCollection of historical Native American territories.\n"
            "\n"
            "Combines US Census TIGER/Line legal boundaries with Native Land Digital\n"
            "historical territories, BIA trust land, and EPA tribal layers.\n"
            f"Contains {len(features)} features total.\n"
            "\n"
            "Each feature includes the nation/tribe name, territory type,\n"
            "and whether it represents current legal boundaries or historical extent.\n"
            "\n"
            f"{SOVEREIGNTY_NOTE}"
        ),
    )

    logger.info(f"[tribal_embedder] Wrote {len(features)} native territories to {out_path}")
    return len(features)


def _write_geojson_module(path: Path, module_name: str, func_name: str,
                          geojson: dict, docstring: str):
    """Write a GeoJSON dict as a Python module with a getter function."""
    # Serialize the GeoJSON compactly
    json_str = json.dumps(geojson, separators=(",", ":"))

    # Wrap docstring
    wrapped_doc = docstring.replace("\n", "\n    ")

    code = f'''"""Embedded {module_name} data for the archaeological atlas.

{SOVEREIGNTY_NOTE}
"""

import json as _json

_GEOJSON_STR = {json_str!r}

_CACHE = None


def {func_name}() -> dict:
    """{wrapped_doc}
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = _json.loads(_GEOJSON_STR)
    return _CACHE
'''

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)


def embed_all_tribal() -> dict[str, int]:
    """Run all tribal embedding. Returns {layer_name: feature_count}."""
    results = {}
    results["tribal_boundaries"] = embed_tribal_boundaries()
    results["native_territories"] = embed_native_territories()
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    results = embed_all_tribal()
    for layer, count in results.items():
        print(f"  {layer}: {count} features")
