"""Base scraper with retry, rate-limiting, checkpointing, and logging."""

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

logger = logging.getLogger("scraper")


class BaseScraper(ABC):
    """Abstract base for all archaeological database scrapers."""

    source_id: str = ""       # e.g. "nrhp", "dinaa"
    source_name: str = ""     # e.g. "National Register of Historic Places"
    base_url: str = ""
    rate_limit: float = 1.0   # seconds between requests
    max_retries: int = 3
    timeout: int = 30

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.checkpoint_dir = output_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "FOURLEAFCLOVIS-ArchaeoDB-Scraper/1.0 (academic research)"
        })

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrape all records from this source. Returns list of raw record dicts."""
        ...

    def _request_with_retry(self, url: str, params: dict | None = None,
                            method: str = "GET", json_body: dict | None = None) -> requests.Response:
        """HTTP request with rate limiting, exponential backoff retry."""
        # Rate limit
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                self._last_request_time = time.time()
                if method == "POST":
                    resp = self._session.post(url, params=params, json=json_body,
                                              timeout=self.timeout)
                else:
                    resp = self._session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp
            except (requests.RequestException, requests.Timeout) as e:
                last_exc = e
                wait = (2 ** attempt) * 2
                logger.warning(
                    f"[{self.source_id}] Request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"{e}. Retrying in {wait}s..."
                )
                time.sleep(wait)

        logger.error(f"[{self.source_id}] All {self.max_retries} retries exhausted for {url}")
        raise last_exc

    def _save_checkpoint(self, state: dict):
        """Save scraping progress for resumability."""
        path = self.checkpoint_dir / f"{self.source_id}.json"
        with open(path, "w") as f:
            json.dump(state, f)
        logger.debug(f"[{self.source_id}] Checkpoint saved: {state.get('offset', '?')} records")

    def _load_checkpoint(self) -> dict | None:
        """Load previous checkpoint, or None if no checkpoint exists."""
        path = self.checkpoint_dir / f"{self.source_id}.json"
        if path.exists():
            with open(path) as f:
                state = json.load(f)
            logger.info(f"[{self.source_id}] Resuming from checkpoint: {state.get('offset', '?')} records")
            return state
        return None

    def _clear_checkpoint(self):
        """Remove checkpoint after successful completion."""
        path = self.checkpoint_dir / f"{self.source_id}.json"
        if path.exists():
            path.unlink()

    def _save_raw(self, records: list[dict]):
        """Save raw scraped records to JSON."""
        from datetime import date
        output = {
            "source": self.source_id,
            "url": self.base_url,
            "scrape_date": str(date.today()),
            "record_count": len(records),
            "records": records,
        }
        path = self.output_dir / f"{self.source_id}.json"
        with open(path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"[{self.source_id}] Saved {len(records)} raw records to {path}")

    def run(self) -> list[dict]:
        """Execute scrape, save raw output, clear checkpoint."""
        logger.info(f"[{self.source_id}] Starting scrape of {self.source_name}...")
        try:
            records = self.scrape()
            self._save_raw(records)
            self._clear_checkpoint()
            logger.info(f"[{self.source_id}] Complete: {len(records)} records scraped")
            return records
        except Exception as e:
            logger.error(f"[{self.source_id}] Scrape failed: {e}")
            raise
