"""Source 1: NRHP scraper.

Strategy: Download NPS bulk spreadsheet (always available), fall back to ArcGIS API.
NPS data-download page: https://www.nps.gov/subjects/nationalregister/data-downloads.htm
"""

import io
import logging
import tempfile
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# NPS bulk download URL (updated periodically -- try dated, then undated)
NPS_XLSX_URLS = [
    "https://www.nps.gov/subjects/nationalregister/upload/national-register-listed_20250624.xlsx",
    "https://www.nps.gov/subjects/nationalregister/upload/national-register-listed.xlsx",
]

# ArcGIS endpoints (new NPS MapServer found via research)
NPS_MAPSERVER = "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0"
# Old FeatureServer (dead)
ARCGIS_URL = "https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/NRHP_Status/FeatureServer/0"

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
}


def _state_abbrev(name: str) -> str:
    """Convert full state name to 2-letter abbreviation."""
    if not name:
        return ""
    if len(name) <= 2:
        return name.upper()
    return STATE_ABBREVS.get(name.lower().strip(), name[:2].upper())


ARCHEO_KEYWORDS = ("archeo", "archaeo", "prehist", "archeolog", "archaeolog",
                   "mound", "shell ring", "earthwork", "rock shelter", "cave",
                   "pueblo", "cliff dwelling", "petroglyph", "pictograph",
                   "burial", "village site", "campsite", "quarry")


class NRHPScraper(BaseScraper):
    source_id = "nrhp"
    source_name = "National Register of Historic Places"
    base_url = "https://www.nps.gov/subjects/nationalregister/data-downloads.htm"
    rate_limit = 0.5

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        # Try NPS MapServer first (has coordinates!)
        records = self._scrape_nps_mapserver()
        if records:
            return records

        # Try NPS Excel bulk download (no coordinates, but has names)
        records = self._scrape_nps_xlsx()
        if records:
            return records

        # Fall back to old ArcGIS API
        logger.info("[nrhp] All methods failed, trying legacy ArcGIS API...")
        return self._scrape_arcgis()

    def _scrape_nps_mapserver(self) -> list[dict]:
        """Scrape NPS Cultural Resources MapServer -- has coordinates!"""
        records = []
        checkpoint = self._load_checkpoint()
        offset = checkpoint.get("offset", 0) if checkpoint else 0
        if checkpoint:
            records = checkpoint.get("records", [])

        batch_size = 1000
        while True:
            params = {
                "where": "ResType IN ('site','district') OR RESNAME LIKE '%Mound%' OR RESNAME LIKE '%Cave%' OR RESNAME LIKE '%Shelter%' OR RESNAME LIKE '%Pueblo%' OR RESNAME LIKE '%Petroglyph%' OR RESNAME LIKE '%Earthwork%' OR RESNAME LIKE '%Village%' OR RESNAME LIKE '%Shell Ring%'",
                "outFields": "RESNAME,ResType,State,County,City,Address",
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": batch_size,
            }

            try:
                resp = self._request_with_retry(f"{NPS_MAPSERVER}/query", params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[nrhp] MapServer failed at offset {offset}: {e}")
                if records:
                    self._save_checkpoint({"offset": offset, "records": records})
                return records if records else []

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

                name = props.get("RESNAME") or "Unknown NRHP Site"
                state_full = props.get("State") or ""
                # Convert full state name to 2-letter code
                state = _state_abbrev(state_full)

                records.append({
                    "name": name,
                    "lat": coords[1],
                    "lon": coords[0],
                    "site_type": props.get("ResType") or "site",
                    "period": "",
                    "state": state,
                    "source_id": f"nrhp_nps_{offset + len(records)}",
                    "description": f"{props.get('County', '')} County" if props.get('County') else "",
                })

            offset += len(features)
            logger.info(f"[nrhp] MapServer: {offset} fetched, {len(records)} archaeological")

            if len(features) < batch_size:
                break

            if offset % 5000 == 0:
                self._save_checkpoint({"offset": offset, "records": records})

        if records:
            logger.info(f"[nrhp] MapServer yielded {len(records)} records with coordinates")
        return records

    def _scrape_nps_xlsx(self) -> list[dict]:
        """Download and parse NPS NRHP Excel spreadsheet."""
        for url in NPS_XLSX_URLS:
            try:
                logger.info(f"[nrhp] Downloading NRHP spreadsheet from {url}...")
                resp = self._session.get(url, timeout=120, stream=True)
                resp.raise_for_status()

                # Read into memory
                data = io.BytesIO(resp.content)
                logger.info(f"[nrhp] Downloaded {len(resp.content) / 1024 / 1024:.1f} MB")

                return self._parse_xlsx(data)

            except Exception as e:
                logger.warning(f"[nrhp] Excel download failed ({url}): {e}")
                continue

        return []

    def _parse_xlsx(self, data: io.BytesIO) -> list[dict]:
        """Parse NRHP Excel file into records."""
        try:
            import openpyxl
        except ImportError:
            logger.error("[nrhp] openpyxl not installed. pip install openpyxl")
            return []

        wb = openpyxl.load_workbook(data, read_only=True, data_only=True)
        ws = wb.active

        rows = ws.iter_rows(values_only=True)
        headers = [str(h).strip().lower() if h else "" for h in next(rows)]

        # Find column indices -- try various possible column names
        col_map = {}
        for i, h in enumerate(headers):
            if h in ("property name", "resource name", "resname", "name") or "property name" in h:
                col_map["name"] = i
            elif h in ("category of property", "resource type", "restype", "resource_type"):
                col_map["res_type"] = i
            elif h == "area of significance" or (h.startswith("area") and "significance" in h):
                col_map["significance"] = i
            elif h == "state" or h == "st":
                col_map["state"] = i
            elif h == "county":
                col_map["county"] = i
            elif "date" in h and "listed" in h:
                col_map["date_listed"] = i
            elif h in ("latitude", "lat"):
                col_map["lat"] = i
            elif h in ("longitude", "lon", "long"):
                col_map["lon"] = i

        logger.info(f"[nrhp] Column mapping: {col_map}")
        logger.info(f"[nrhp] Headers: {headers}")

        if "name" not in col_map:
            for i, h in enumerate(headers):
                if h and h not in ("", "ref#", "prefix", "refnum", "nris_refnum"):
                    col_map.setdefault("name", i)
                    break

        records = []
        total_rows = 0
        for row in rows:
            total_rows += 1
            if not row:
                continue

            name = str(row[col_map["name"]]) if "name" in col_map and row[col_map["name"]] else ""
            res_type = str(row[col_map.get("res_type", -1)] or "") if "res_type" in col_map else ""
            significance = str(row[col_map.get("significance", -1)] or "") if "significance" in col_map else ""
            state = str(row[col_map.get("state", -1)] or "") if "state" in col_map else ""

            # Check if this is an archaeological site
            combined = f"{name} {res_type} {significance}".lower()
            is_site = res_type.lower() in ("site", "district")
            is_archeo = any(kw in combined for kw in ARCHEO_KEYWORDS)

            if not (is_site or is_archeo):
                continue

            # Get coordinates if available
            lat = None
            lon = None
            if "lat" in col_map and row[col_map["lat"]]:
                try:
                    lat = float(row[col_map["lat"]])
                except (ValueError, TypeError):
                    pass
            if "lon" in col_map and row[col_map["lon"]]:
                try:
                    lon = float(row[col_map["lon"]])
                except (ValueError, TypeError):
                    pass

            records.append({
                "name": name.strip() or "Unknown NRHP Site",
                "lat": lat,
                "lon": lon,
                "site_type": res_type.strip() or "site",
                "period": "",
                "state": state.strip()[:2].upper() if state else "",
                "source_id": f"nrhp_{total_rows}",
                "description": significance.strip()[:500],
            })

        wb.close()
        logger.info(f"[nrhp] Parsed {total_rows} total rows, {len(records)} archaeological records")
        return records

    def _scrape_arcgis(self) -> list[dict]:
        """Fall back to ArcGIS Feature Server (may be down)."""
        records = []
        offset = 0
        batch_size = 1000

        while True:
            params = {
                "where": "1=1",
                "outFields": "ResName,ResType,AreaOfSignificance,State",
                "returnGeometry": "true",
                "resultOffset": offset,
                "resultRecordCount": batch_size,
                "f": "json",
            }

            try:
                resp = self._request_with_retry(f"{ARCGIS_URL}/query", params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[nrhp] ArcGIS failed at offset {offset}: {e}")
                break

            if "error" in data:
                logger.warning(f"[nrhp] ArcGIS error: {data['error']}")
                break

            features = data.get("features", [])
            if not features:
                break

            for feat in features:
                attrs = feat.get("attributes", {})
                geom = feat.get("geometry", {})
                if not geom or geom.get("x") is None:
                    continue

                combined = f"{attrs.get('ResType', '')} {attrs.get('AreaOfSignificance', '')}".lower()
                if not any(kw in combined for kw in ARCHEO_KEYWORDS):
                    if (attrs.get("ResType") or "").lower() not in ("site", "district"):
                        continue

                records.append({
                    "name": attrs.get("ResName") or "Unknown NRHP Site",
                    "lat": geom["y"],
                    "lon": geom["x"],
                    "site_type": attrs.get("ResType") or "site",
                    "period": "",
                    "state": attrs.get("State") or "",
                    "source_id": f"nrhp_arcgis_{offset}",
                    "description": attrs.get("AreaOfSignificance") or "",
                })

            offset += len(features)
            if len(features) < batch_size:
                break

        return records
