"""
Multi-layer weighted convergence scorer — THE HEART OF ARCHAEO-SCAN.

The fundamental archaeological insight this system is built on:
sites aren't found by any single indicator, but by CONVERGENCE of
multiple independent signals. A cell near paleo-water, on a terrace,
with anomalous soil chemistry, in a geologic zone that forms shelters,
showing crop marks in satellite imagery — that convergence is far more
significant than any single factor alone.

The scorer:
1. Gathers all available layer scores for each grid cell
2. Applies configurable weights (tunable per region/time period)
3. Computes a composite score with confidence based on layer count
4. Identifies spatial clusters of high-scoring cells (hotspots)

Weights are loaded from config/scoring_weights.yaml and can be
overridden with regional presets (southeast_mississippian,
great_basin_paleoindian, pacific_coast_pre_clovis, etc.).
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import yaml

from core.schemas import BoundingBox, GridCell, Hotspot, ScoredCell
from core.tile_grid import cell_neighbors, cells_in_bbox, point_to_cell

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_PATH = Path(__file__).parent.parent / "config" / "scoring_weights.yaml"


class ConvergenceScorer:
    """
    Multi-layer weighted overlay scoring engine.

    Combines scores from all available data layers into a single
    composite archaeological potential score per grid cell. The
    composite is a weighted average, but confidence scales with
    the NUMBER of independent contributing layers — because
    convergence of evidence is the key signal.
    """

    def __init__(
        self,
        weights_path: str | Path = DEFAULT_WEIGHTS_PATH,
        preset: str | None = None,
    ):
        self.config = self._load_config(weights_path)
        self.weights = dict(self.config.get("weights", {}))
        self.confidence_thresholds = self.config.get("confidence_thresholds", {})

        # Apply regional preset if specified
        if preset:
            presets = self.config.get("regional_presets", {})
            if preset in presets:
                self.weights.update(presets[preset])
                logger.info("Applied regional preset: %s", preset)
            else:
                logger.warning("Unknown preset '%s', using defaults. Available: %s",
                               preset, list(presets.keys()))

    def _load_config(self, path: str | Path) -> dict[str, Any]:
        """Load scoring weights from YAML configuration."""
        path = Path(path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        logger.warning("Weights config not found at %s, using defaults", path)
        return {"weights": {}, "confidence_thresholds": {"minimum_layers": 3, "high_confidence": 5}}

    def score_cell(self, cell_id: str, layer_scores: dict[str, float]) -> ScoredCell:
        """
        Compute the convergence score for a single grid cell.

        The composite is a WEIGHTED average of available layer scores,
        where weights come from the configuration. Confidence is based
        on how many independent layers contributed — a cell scored by
        5 layers is more trustworthy than one scored by 2.

        Args:
            cell_id: H3 cell identifier.
            layer_scores: Dict mapping layer names to their 0.0-1.0 scores.

        Returns:
            ScoredCell with composite score, confidence, and factor breakdown.
        """
        if not layer_scores:
            return ScoredCell(
                cell_id=cell_id,
                layer_scores={},
                composite_score=0.0,
                confidence=0.0,
                contributing_factors=["No data layers available"],
            )

        # Compute weighted composite
        weighted_sum = 0.0
        weight_total = 0.0
        contributing_factors = []

        for layer_name, score in layer_scores.items():
            weight = self.weights.get(layer_name, 0.5)  # Default weight for unknown layers
            weighted_sum += score * weight
            weight_total += weight

            # Track significant contributors
            if score >= 0.5:
                contributing_factors.append(
                    f"{layer_name}: {score:.2f} (weight {weight:.2f})"
                )

        composite = weighted_sum / weight_total if weight_total > 0 else 0.0

        # Confidence scales with layer count
        min_layers = self.confidence_thresholds.get("minimum_layers", 3)
        high_conf_layers = self.confidence_thresholds.get("high_confidence", 5)
        n_layers = len(layer_scores)

        if n_layers < min_layers:
            # Below minimum: confidence is heavily penalized
            confidence = (n_layers / min_layers) * 0.5
        elif n_layers >= high_conf_layers:
            confidence = 1.0
        else:
            # Linear interpolation between minimum and high confidence
            confidence = 0.5 + 0.5 * (n_layers - min_layers) / (high_conf_layers - min_layers)

        # Cap composite by confidence — a high score from 1 layer shouldn't
        # rank above a moderate score from 5 layers
        adjusted_composite = composite * (0.5 + 0.5 * confidence)

        return ScoredCell(
            cell_id=cell_id,
            layer_scores=layer_scores,
            composite_score=round(min(adjusted_composite, 1.0), 4),
            confidence=round(confidence, 4),
            contributing_factors=contributing_factors,
            layer_count=n_layers,
        )

    def score_region(
        self,
        cell_scores: dict[str, dict[str, float]],
    ) -> list[ScoredCell]:
        """
        Score all cells in a region.

        Args:
            cell_scores: Dict mapping cell_id -> {layer_name: score}.

        Returns:
            List of ScoredCells sorted by composite score descending.
        """
        results = []
        for cell_id, layer_scores in cell_scores.items():
            scored = self.score_cell(cell_id, layer_scores)
            results.append(scored)

        results.sort(key=lambda s: s.composite_score, reverse=True)
        return results

    def find_hotspots(
        self,
        scored_cells: list[ScoredCell],
        threshold: float = 0.6,
        min_cluster_size: int = 3,
    ) -> list[Hotspot]:
        """
        Identify spatial clusters of high-scoring cells.

        A cluster of high-scoring cells is more archaeologically
        significant than an isolated high scorer. Isolated high scores
        may be data artifacts; clusters indicate real landscape-scale
        patterns consistent with human settlement areas.

        Uses a simple neighbor-expansion approach: start from the
        highest-scoring unvisited cell, expand to high-scoring neighbors,
        continue until no more high-scoring neighbors exist.
        """
        # Filter to cells above threshold
        high_cells = {s.cell_id: s for s in scored_cells if s.composite_score >= threshold}

        if not high_cells:
            return []

        visited: set[str] = set()
        hotspots: list[Hotspot] = []

        # Sort by score descending — start clusters from the strongest signals
        sorted_ids = sorted(high_cells, key=lambda c: high_cells[c].composite_score, reverse=True)

        for start_id in sorted_ids:
            if start_id in visited:
                continue

            # BFS to find connected cluster of high-scoring cells
            cluster: list[ScoredCell] = []
            queue = [start_id]

            while queue:
                cell_id = queue.pop(0)
                if cell_id in visited:
                    continue
                if cell_id not in high_cells:
                    continue

                visited.add(cell_id)
                cluster.append(high_cells[cell_id])

                # Add high-scoring neighbors to queue
                for neighbor in cell_neighbors(cell_id):
                    if neighbor not in visited and neighbor in high_cells:
                        queue.append(neighbor)

            if len(cluster) >= min_cluster_size:
                hotspot = self._cluster_to_hotspot(cluster, len(hotspots))
                hotspots.append(hotspot)

        hotspots.sort(key=lambda h: h.mean_score, reverse=True)
        return hotspots

    def _cluster_to_hotspot(self, cluster: list[ScoredCell], index: int) -> Hotspot:
        """Convert a cluster of scored cells into a Hotspot summary."""
        import h3

        scores = [c.composite_score for c in cluster]
        lats = []
        lons = []
        for c in cluster:
            lat, lon = h3.cell_to_latlng(c.cell_id)
            lats.append(lat)
            lons.append(lon)

        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Estimate radius from center to farthest cell
        from core.geo_utils import haversine_distance
        max_dist = max(
            haversine_distance(center_lat, center_lon, lat, lon)
            for lat, lon in zip(lats, lons)
        )

        # Aggregate dominant factors across the cluster
        factor_counts: dict[str, int] = {}
        for cell in cluster:
            for factor in cell.contributing_factors:
                layer_name = factor.split(":")[0].strip()
                factor_counts[layer_name] = factor_counts.get(layer_name, 0) + 1

        dominant = sorted(factor_counts, key=factor_counts.get, reverse=True)[:5]

        return Hotspot(
            hotspot_id=f"HS-{index:04d}",
            center_lat=round(center_lat, 6),
            center_lon=round(center_lon, 6),
            radius_km=round(max(max_dist, 0.5), 2),  # Minimum 0.5km radius
            mean_score=round(sum(scores) / len(scores), 4),
            max_score=round(max(scores), 4),
            cell_count=len(cluster),
            dominant_factors=dominant,
        )
