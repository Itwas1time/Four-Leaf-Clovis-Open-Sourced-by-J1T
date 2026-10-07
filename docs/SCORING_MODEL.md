> **Public edition:** public Census town points are bundled as spatial context; archaeological/fossil locations are not. See the [README](../README.md). Other datasets described below are optional and are not bundled.

# Convergence Scoring Methodology

> **Status:** This document describes the intended multi-layer model, not a
> validated discovery predictor. The current CLI scoring path uses only
> registered-site proximity, site clustering, and fossil proximity because
> the bundled environmental layers are missing spatial observations. Its
> numerical score must not be interpreted as discovery probability or a dig
> recommendation. The active Atlas workflow and `clovis-plan` now report
> documented context, evidence gaps, and research follow-up instead. See
> [README](../README.md).

## Core Principle

Archaeological sites are predicted not by any single indicator but by **convergence** of multiple independent signals. A grid cell that scores high on water proximity AND terrain anomalies AND soil chemistry AND shelter potential is far more likely to contain a site than one with a single strong signal.

This mirrors how professional archaeologists think: "There's a terrace above the river, with unusual soil color, near a sandstone overhang, and a 1820s journal mentions a 'ruined village' in this area." Each signal alone is suggestive; together they're compelling.

## Scoring Architecture

### Per-Cell Computation

For each H3 hexagonal cell (default resolution 8, ~0.74 km²):

1. **Gather layer scores** — each processor outputs a 0.0–1.0 score
2. **Apply weights** — configurable importance multipliers per layer
3. **Compute weighted average** — the raw composite
4. **Apply confidence scaling** — composite × confidence factor
5. **Record contributing factors** — human-readable explanation

### Layer Weights (Defaults)

| Layer | Weight | Rationale |
|-------|--------|-----------|
| LiDAR anomaly | 0.90 | Most reliable remote indicator |
| Hydro proximity | 0.85 | Strongest universal predictor |
| Soil anomaly | 0.80 | Direct evidence of habitation |
| Terrain anomaly | 0.75 | Strong indicator of earthworks |
| Crop mark | 0.70 | Proven but variable by region |
| Shelter probability | 0.65 | Critical for early periods |
| Oral history | 0.60 | Valuable but variable reliability |
| Known site proximity | 0.50 | Sites cluster, but risks confirmation bias |
| Citizen reports | 0.40 | Noisy signal, useful in aggregate |

### Confidence Model

Confidence is based on the **number of independent layers** contributing:

- **< 3 layers:** Low confidence (score heavily penalized)
- **3-4 layers:** Moderate confidence
- **5+ layers:** High confidence (full score potential)

This prevents a single noisy data source from generating false positives.

### Hotspot Detection

Individual high-scoring cells are less significant than **clusters** of high-scoring cells. The hotspot detector uses neighbor-expansion:

1. Find highest-scoring unvisited cell above threshold
2. Expand to neighboring cells that also score above threshold
3. Continue until no more qualifying neighbors
4. Require minimum cluster size (default 3 cells)
5. Report cluster center, radius, mean/max score, dominant factors

### Regional Presets

Different regions and time periods have different archaeological signatures:

- **Southeast Mississippian:** Higher weight on mound detection, soil
- **Great Basin Paleoindian:** Higher weight on shelters, paleo-lakes
- **Pacific Coast Pre-Clovis:** Highest weight on shelf reconstruction
- **Southwest Archaic:** Balanced shelters and hydrology
- **Northeast Woodland:** LiDAR critical (dense canopy)

## Validation Strategy

The scoring model is validated against known sites:

1. Score a region containing known major sites
2. Verify known sites appear in the top percentile
3. Examine false positives — are they genuinely uninvestigated or actually low-potential?
4. Examine false negatives — what made the model miss known sites?
5. Iterate weights based on findings

No spatially separated validation with negative surveys has been completed.
Such validation is required before assigning discovery likelihoods to cells.
