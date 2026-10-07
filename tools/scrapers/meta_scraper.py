"""Sources 14-18: Meta/discovery scrapers (SKOPE, Open Arch Data, CARD, ArchSynth, GitHub)."""

import json
import logging
import re
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")


class SKOPEScraper(BaseScraper):
    source_id = "skope"
    source_name = "SKOPE (Synthesizing Knowledge of Past Environments)"
    base_url = "https://openskope.org/"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        # SKOPE is primarily a visualization tool; try to find data endpoints
        endpoints = [
            "https://openskope.org/api/datasets",
            "https://openskope.org/api/v1/datasets",
            "https://app.openskope.org/api/datasets",
        ]
        for url in endpoints:
            try:
                resp = self._request_with_retry(url)
                data = resp.json()
                items = data if isinstance(data, list) else data.get("datasets", data.get("data", []))
                for item in items:
                    if isinstance(item, dict):
                        records.append({
                            "name": item.get("title") or item.get("name") or "",
                            "description": item.get("description") or "",
                            "url": item.get("url") or "",
                            "type": "paleoenvironmental_dataset",
                        })
                if records:
                    break
            except Exception as e:
                logger.debug(f"[skope] {url} failed: {e}")

        if not records:
            # Just note SKOPE as a reference source
            try:
                resp = self._request_with_retry(self.base_url)
                logger.info("[skope] Main page accessible but no API found")
            except Exception:
                pass

        return records


class OpenArchDataScraper(BaseScraper):
    source_id = "open_arch_data"
    source_name = "Open Archaeology Data Journal"
    base_url = "https://openarchaeologydata.metajnl.com/articles"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        try:
            resp = self._request_with_retry(self.base_url)
            html = resp.text
            # Extract article links and their data repository URLs
            article_pattern = re.compile(
                r'href=["\']([^"\']*article[^"\']*)["\']', re.IGNORECASE
            )
            article_urls = set()
            for match in article_pattern.finditer(html):
                url = match.group(1)
                if not url.startswith("http"):
                    url = f"https://openarchaeologydata.metajnl.com{url}"
                article_urls.add(url)

            for article_url in list(article_urls)[:50]:  # Cap at 50 articles
                try:
                    art_resp = self._request_with_retry(article_url)
                    art_html = art_resp.text

                    # Look for data repository links
                    data_links = re.findall(
                        r'href=["\']([^"\']*(?:zenodo|figshare|tdar|doi\.org|dataverse)[^"\']*)["\']',
                        art_html, re.IGNORECASE
                    )
                    # Extract title
                    title_match = re.search(r'<title>([^<]+)</title>', art_html)
                    title = title_match.group(1) if title_match else article_url

                    for link in data_links[:3]:
                        records.append({
                            "name": title,
                            "url": link,
                            "source_article": article_url,
                            "type": "dataset_reference",
                        })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"[open_arch_data] Failed: {e}")

        return records


class CARDScraper(BaseScraper):
    source_id = "card"
    source_name = "Canadian Archaeological Radiocarbon Database"
    base_url = "https://www.canadianarchaeology.ca/resources/card"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []

        endpoints = [
            "https://www.canadianarchaeology.ca/api/card/sites",
            "https://www.canadianarchaeology.ca/card/data",
            self.base_url,
        ]

        for url in endpoints:
            try:
                resp = self._request_with_retry(url)
                ct = resp.headers.get("content-type", "")

                if "json" in ct:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("sites", data.get("data", []))
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        lat = item.get("lat") or item.get("latitude")
                        lon = item.get("lon") or item.get("longitude") or item.get("lng")
                        if lat is None or lon is None:
                            continue
                        try:
                            lat, lon = float(lat), float(lon)
                        except (ValueError, TypeError):
                            continue
                        # Only keep sites in or near northern US (lat > 40)
                        if lat < 40 or lon < -125 or lon > -66:
                            continue
                        records.append({
                            "name": item.get("site_name") or item.get("name") or "",
                            "lat": lat,
                            "lon": lon,
                            "state": "",
                            "period": f"{item.get('date_bp', '')} BP" if item.get("date_bp") else "",
                            "site_type": item.get("site_type") or "radiocarbon-dated",
                            "source_id": str(item.get("id", "")),
                            "description": item.get("material_dated") or "",
                        })
                    if records:
                        break
                elif "html" in ct:
                    # Look for data download links
                    data_links = re.findall(
                        r'href=["\']([^"\']*(?:\.csv|\.json|download|data)[^"\']*)["\']',
                        resp.text, re.IGNORECASE
                    )
                    for link in data_links[:5]:
                        if not link.startswith("http"):
                            link = f"https://www.canadianarchaeology.ca/{link.lstrip('/')}"
                        try:
                            dr = self._request_with_retry(link)
                            if "json" in dr.headers.get("content-type", ""):
                                # Recurse with JSON
                                jdata = dr.json()
                                items = jdata if isinstance(jdata, list) else jdata.get("sites", [])
                                for item in items:
                                    lat = item.get("lat") or item.get("latitude")
                                    lon = item.get("lon") or item.get("longitude")
                                    if lat and lon:
                                        try:
                                            lat, lon = float(lat), float(lon)
                                            if lat >= 40:
                                                records.append({
                                                    "name": item.get("site_name") or item.get("name") or "",
                                                    "lat": lat, "lon": lon,
                                                    "state": "", "period": "",
                                                    "site_type": "radiocarbon-dated",
                                                    "source_id": "", "description": "",
                                                })
                                        except (ValueError, TypeError):
                                            continue
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"[card] {url} failed: {e}")

        return records


class ArchSynthScraper(BaseScraper):
    source_id = "archsynth"
    source_name = "ArchSynth Resources / open-archaeo.info"
    base_url = "https://open-archaeo.info"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        """Scrape meta-directories for additional data source references."""
        sources = []

        urls = [
            "https://open-archaeo.info/tags/api-interfaces-and-web-scrapers/",
            "https://open-archaeo.info/",
        ]

        for url in urls:
            try:
                resp = self._request_with_retry(url)
                html = resp.text

                # Extract tool/resource entries
                entries = re.findall(
                    r'<h[23][^>]*>([^<]+)</h[23]>.*?href=["\']([^"\']+)["\']',
                    html, re.DOTALL
                )
                for name, link in entries[:30]:
                    sources.append({
                        "name": name.strip(),
                        "url": link,
                        "type": "discovered_source",
                    })
            except Exception as e:
                logger.debug(f"[archsynth] {url} failed: {e}")

        # Save discovered sources
        if sources:
            disc_path = self.output_dir.parent / "discovered_sources.json"
            with open(disc_path, "w") as f:
                json.dump(sources, f, indent=2)
            logger.info(f"[archsynth] Saved {len(sources)} discovered sources to {disc_path}")

        return sources


class GitHubArchScraper(BaseScraper):
    source_id = "github_arch"
    source_name = "GitHub Archaeology Topic"
    base_url = "https://api.github.com/search/repositories"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        """Search GitHub for archaeology data repositories."""
        records = []

        params = {
            "q": "archaeology data geojson",
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }

        try:
            resp = self._request_with_retry(self.base_url, params=params)
            data = resp.json()
            repos = data.get("items", [])

            for repo in repos:
                stars = repo.get("stargazers_count", 0)
                if stars < 5:
                    continue

                records.append({
                    "name": repo.get("full_name") or repo.get("name") or "",
                    "url": repo.get("html_url") or "",
                    "description": (repo.get("description") or "")[:200],
                    "stars": stars,
                    "type": "github_dataset",
                })

        except Exception as e:
            logger.warning(f"[github_arch] Search failed: {e}")

        # Also try direct topic search
        try:
            resp = self._request_with_retry(
                "https://api.github.com/search/repositories",
                params={
                    "q": "archaeological sites geojson OR csv",
                    "sort": "stars",
                    "per_page": 20,
                }
            )
            data = resp.json()
            for repo in data.get("items", []):
                if repo.get("stargazers_count", 0) >= 5:
                    records.append({
                        "name": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "description": (repo.get("description") or "")[:200],
                        "stars": repo.get("stargazers_count", 0),
                        "type": "github_dataset",
                    })
        except Exception:
            pass

        return records
