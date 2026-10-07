"""
Base collector interface.

All data collectors inherit from BaseCollector and implement its three methods.
This ensures a uniform API for the CLI and orchestration layer: every data
source is collected the same way regardless of its upstream format or API.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract base for all ARCHAEO-SCAN data collectors.

    Subclasses implement three methods:
    1. check_availability() — probe what data exists without downloading
    2. collect() — download and store data for a bounding box
    3. get_metadata() — return source attribution and license info

    Collectors should be:
    - Resumable: use checkpoints so interrupted downloads continue
    - Memory-conscious: process data in tiles/chunks, never load entire states
    - Documented: explain archaeological rationale in docstrings
    """

    def __init__(self, data_dir: str | Path = "./data", cache_dir: str | Path = "./cache"):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this collector (e.g., 'terrain', 'hydro')."""
        ...

    @abstractmethod
    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Check what data exists for this area WITHOUT downloading.

        Returns a CoverageReport describing coverage extent, tile count,
        and estimated download size. Useful for planning collection
        campaigns and estimating storage needs.
        """
        ...

    @abstractmethod
    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download and store data for the given bounding box.

        Returns a DataLayer with metadata about what was collected.
        Must be resumable — if interrupted, calling collect() again
        should pick up where it left off.
        """
        ...

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """
        Return source attribution, license, and documentation.

        This information is included in all exports for proper
        attribution and reproducibility.
        """
        ...

    def _checkpoint_path(self, bbox: BoundingBox) -> Path:
        """Path for this collector's checkpoint file within a bbox."""
        bbox_hash = f"{bbox.min_lat:.4f}_{bbox.min_lon:.4f}_{bbox.max_lat:.4f}_{bbox.max_lon:.4f}"
        return self.cache_dir / f"{self.name}_checkpoint_{bbox_hash}.json"

    def _save_checkpoint(self, bbox: BoundingBox, state: dict[str, Any]) -> None:
        """Save collection progress for resumability."""
        path = self._checkpoint_path(bbox)
        with open(path, "w") as f:
            json.dump(state, f)
        logger.debug("Checkpoint saved: %s", path)

    def _load_checkpoint(self, bbox: BoundingBox) -> dict[str, Any] | None:
        """Load previously saved collection progress."""
        path = self._checkpoint_path(bbox)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _clear_checkpoint(self, bbox: BoundingBox) -> None:
        """Remove checkpoint after successful completion."""
        path = self._checkpoint_path(bbox)
        if path.exists():
            path.unlink()
