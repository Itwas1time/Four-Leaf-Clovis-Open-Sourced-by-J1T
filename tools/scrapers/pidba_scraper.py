"""Source 7: PIDBA (Paleoindian Database of the Americas).

Strategy: Download the entire database XLS from pidba.org/content/entiredatabase_06_13_11.xls
This has county-level lat/lon with Paleoindian point type counts per county.
"""

import io
import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

ENTIRE_DB_URL = "http://pidba.org/content/entiredatabase_06_13_11.xls"

# Major Paleoindian point types and their column offsets (from col 8 onward)
POINT_TYPES = [
    "Clovis", "Ross County", "Clovis Variant", "Pelican/Clovis",
    "Gainey/Bull Brook", "Vail/Debert", "Barnes/Michaud/Neponset",
    "Northumberland", "Crowfield", "Cumberland", "Redstone",
    "Holcombe/Nicolas", "Hi-Lo", "Wheeler", "Beaver Lake", "Quad",
    "Coldwater", "Hinds", "Arkabutla", "Dalton", "Hardaway-Dalton",
    "Greenbrier", "San Patrice", "Suwannee", "Simpson", "Folsom",
    "Midland", "Plainview", "Goshen", "Agate Basin", "Hell Gap",
    "Alberta", "Scottsbluff", "Eden",
]


class PIDBAScraper(BaseScraper):
    source_id = "pidba"
    source_name = "Paleoindian Database of the Americas"
    base_url = "http://pidba.org"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self._session.verify = False

    def scrape(self) -> list[dict]:
        try:
            return self._scrape_entire_db()
        except Exception as e:
            logger.warning(f"[pidba] Entire DB download failed: {e}")
            return self._scrape_state_pages()

    def _scrape_entire_db(self) -> list[dict]:
        """Download and parse the entire PIDBA database XLS."""
        try:
            import xlrd
        except ImportError:
            logger.error("[pidba] xlrd not installed. pip install xlrd")
            return []

        logger.info("[pidba] Downloading entire PIDBA database...")
        resp = self._session.get(ENTIRE_DB_URL, timeout=120)
        resp.raise_for_status()
        logger.info(f"[pidba] Downloaded {len(resp.content) / 1024 / 1024:.1f} MB")

        wb = xlrd.open_workbook(file_contents=resp.content)
        ws = wb.sheet_by_index(0)

        # Row 12 is header, data starts at 13
        # Col 0=Country, 1=CODE, 2=COUNTY, 3=Lat, 4=Lon, 5=FPS, 6=Area, 7=SAMPLE, 8+=point types

        # Get point type names from header row
        point_type_cols = {}
        for c in range(8, min(ws.ncols, 78)):
            v = str(ws.cell_value(12, c)).strip()
            if v:
                point_type_cols[c] = v

        records = []
        for r in range(13, ws.nrows):
            lat = ws.cell_value(r, 3)
            lon = ws.cell_value(r, 4)
            if not lat or not lon:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue

            # Filter to US (including Alaska)
            if not (24.0 <= lat <= 72.0 and -180.0 <= lon <= -66.0):
                continue

            county = str(ws.cell_value(r, 2)).strip()
            state_code = str(ws.cell_value(r, 1)).strip()
            sample = 0
            try:
                sample = int(float(ws.cell_value(r, 7) or 0))
            except (ValueError, TypeError):
                pass

            # Find which point types are present in this county
            present_types = []
            for c, ptype in point_type_cols.items():
                try:
                    count = int(float(ws.cell_value(r, c) or 0))
                    if count > 0:
                        present_types.append(f"{ptype}:{count}")
                except (ValueError, TypeError):
                    continue

            if sample == 0 and not present_types:
                continue

            # Create one record per county with significant finds
            type_summary = "; ".join(present_types[:10])
            primary_type = present_types[0].split(":")[0] if present_types else "untyped fluted"

            records.append({
                "name": f"{county} Paleoindian finds, {state_code}",
                "lat": lat,
                "lon": lon,
                "state": state_code[:2] if len(state_code) >= 2 else "",
                "period": "Paleoindian",
                "site_type": f"Paleoindian_{primary_type.replace('/', '_')}",
                "source_id": f"pidba_{state_code}_{county}".replace(" ", "_"),
                "description": f"{sample} specimens: {type_summary}" if type_summary else f"{sample} specimens",
            })

        logger.info(f"[pidba] Parsed {len(records)} US county records with Paleoindian finds")
        return records

    def _scrape_state_pages(self) -> list[dict]:
        """Fallback: scrape individual state Excel files."""
        import re

        records = []
        regions = {
            "southeast": ["florida", "georgia", "southcarolina", "alabama", "tennessee",
                          "mississippi", "louisiana", "arkansas", "kentucky",
                          "northcarolina", "westvirginia", "virginia", "maryland", "delaware"],
            "northeast": ["maine", "newhampshire", "vermont", "massachusetts",
                          "rhodeisland", "connecticut", "newyork", "newjersey",
                          "pennsylvania"],
            "midwest": ["ohio", "indiana", "illinois", "michigan", "wisconsin",
                        "minnesota", "iowa", "missouri"],
        }

        for region, states in regions.items():
            for state in states:
                try:
                    # Get state page to find Excel link
                    resp = self._session.get(f"https://pidba.utk.edu/{state}.htm", timeout=30)
                    if resp.status_code != 200:
                        continue

                    xlsx_links = re.findall(
                        r'href=["\']([^"\']*\.xlsx?)["\']', resp.text, re.IGNORECASE
                    )
                    for link in xlsx_links[:1]:
                        if not link.startswith("http"):
                            link = f"http://pidba.org/{link.lstrip('/')}"
                        logger.info(f"[pidba] Found Excel for {state}: {link}")
                except Exception as e:
                    logger.debug(f"[pidba] State {state} failed: {e}")

        return records
