"""
USDA SSURGO soil composition data collector.

Downloads soil survey data from the USDA Web Soil Survey / Soil Data Access
service. Extracts key fields relevant to archaeological prospection.

Archaeological rationale:
    Centuries of human habitation alter soil chemistry in detectable ways.
    "Anthrosols" — soils modified by sustained human activity — show elevated
    phosphorus (from bone, food waste, excrement), darker color (charcoal,
    organic refuse), different texture (compaction, fill), and anomalous
    organic matter content. The SSURGO database maps these properties at
    regional scale, enabling identification of areas where soil chemistry
    deviates from natural baselines.

    The USDA soil taxonomy system even includes specific classifications
    for human-modified soils: "Anthropic" (cultivated) and "Plaggen"
    (European-style manured soils). While these primarily capture historic-era
    agriculture, the underlying chemistry signals extend to prehistoric sites.

Data source:
    - USDA SSURGO (Soil Survey Geographic Database)
    - Available via Soil Data Access (SDA) REST API
    - Coverage: ~95% of US counties surveyed
    - License: Public Domain (US Government)
    - Format: Tabular (joined to spatial map units)
    - Update frequency: Annually
    - Storage: ~5-20 MB per county
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx
import pandas as pd

from collectors.base import BaseCollector
from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)

SDA_API_URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"


class SoilCollector(BaseCollector):
    """
    Collect soil survey data from USDA SSURGO via Soil Data Access.

    Extracts archaeologically relevant soil properties: organic matter,
    taxonomy (anthropic indicators), drainage class, and parent material.
    """

    @property
    def name(self) -> str:
        return "soil"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        SSURGO covers ~95% of US counties. Some areas (wilderness,
        tribal lands, recent surveys) may have gaps.
        """
        from core.geo_utils import is_in_us
        if not is_in_us(bbox.center_lat, bbox.center_lon, continental_only=False):
            return CoverageReport(
                layer_name=self.name,
                bbox=bbox,
                available=False,
                coverage_fraction=0.0,
                notes="SSURGO covers US territories only",
            )

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=True,
            coverage_fraction=0.95,
            notes="SSURGO covers ~95% of US counties; gaps in wilderness/tribal areas",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download SSURGO soil data for the bounding box.

        Steps:
        1. Query SDA for soil map unit polygons intersecting the bbox
        2. For each map unit, retrieve component-level soil properties
        3. Join spatial and tabular data
        4. Store as GeoPackage
        """
        output_dir = self.data_dir / "soil"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"ssurgo_{bbox.min_lat:.2f}_{bbox.min_lon:.2f}.gpkg"

        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Soil data already collected for this bbox")
        else:
            # Step 1: Get spatial map units
            mapunits_gdf = self._get_mapunit_polygons(bbox)
            if mapunits_gdf is not None and len(mapunits_gdf) > 0:
                # Step 2: Get soil properties for these map units
                mukeys = mapunits_gdf["mukey"].unique().tolist() if "mukey" in mapunits_gdf.columns else []
                if mukeys:
                    props_df = self._get_soil_properties(mukeys)
                    if props_df is not None and len(props_df) > 0:
                        # Step 3: Join
                        mapunits_gdf["mukey"] = mapunits_gdf["mukey"].astype(str)
                        props_df["mukey"] = props_df["mukey"].astype(str)
                        result_gdf = mapunits_gdf.merge(props_df, on="mukey", how="left")
                    else:
                        result_gdf = mapunits_gdf
                else:
                    result_gdf = mapunits_gdf

                result_gdf.to_file(str(output_path), driver="GPKG")
                logger.info("Collected %d soil map units", len(result_gdf))

            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="soil_ssurgo",
            source="USDA SSURGO (Soil Survey Geographic Database)",
            source_url=SDA_API_URL,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="gpkg",
            crs="EPSG:4326",
            metadata={
                "properties_collected": [
                    "organic_matter_pct",
                    "drainage_class",
                    "taxonomy_subgroup",
                    "parent_material",
                    "ph_value",
                ],
            },
        )

    def _get_mapunit_polygons(self, bbox: BoundingBox) -> gpd.GeoDataFrame | None:
        """Query SDA for soil map unit polygons within the bbox."""
        # SDA requires SQL text; BoundingBox validates every interpolated number.
        query = f"""
            SELECT mupolygongeo.STAsText() as geom, mukey, muname
            FROM mupolygon
            WHERE mupolygongeo.STIntersects(
                geometry::STGeomFromText(
                    'POLYGON(({bbox.min_lon} {bbox.min_lat},
                              {bbox.max_lon} {bbox.min_lat},
                              {bbox.max_lon} {bbox.max_lat},
                              {bbox.min_lon} {bbox.max_lat},
                              {bbox.min_lon} {bbox.min_lat}))',
                    4326
                )
            ) = 1
        """  # nosec B608

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    SDA_API_URL,
                    json={"query": query, "format": "JSON+COLUMNNAME+METADATA"},
                )
                response.raise_for_status()
                data = response.json()

                if "Table" not in data or len(data["Table"]) < 2:
                    logger.warning("No soil map units found for bbox")
                    return None

                # Parse the SDA response format
                columns = data["Table"][0]
                rows = data["Table"][1:]

                df = pd.DataFrame(rows, columns=columns)
                if "geom" in df.columns:
                    from shapely import wkt
                    df["geometry"] = df["geom"].apply(wkt.loads)
                    gdf = gpd.GeoDataFrame(df.drop(columns=["geom"]), geometry="geometry", crs="EPSG:4326")
                    return gdf

        except Exception as e:
            logger.error("Failed to query SDA for map units: %s", e)

        return None

    def _get_soil_properties(self, mukeys: list[str]) -> pd.DataFrame | None:
        """Retrieve archaeologically relevant soil properties for map unit keys."""
        if not mukeys:
            return None

        if any(not str(key).isascii() or not str(key).isdecimal() or len(str(key)) > 20 for key in mukeys):
            raise ValueError("Soil map-unit keys must be decimal identifiers")

        # Batch mukeys to avoid query limits
        mukey_str = ",".join(f"'{k}'" for k in mukeys[:500])

        # SDA requires SQL text; only validated decimal identifiers enter it.
        query = f"""
            SELECT
                c.mukey,
                c.comppct_r as component_pct,
                c.taxsubgrp as taxonomy_subgroup,
                c.drainagecl as drainage_class,
                c.pmkind as parent_material,
                h.om_r as organic_matter_pct,
                h.ph1to1h2o_r as ph_value
            FROM component c
            LEFT JOIN chorizon h ON c.cokey = h.cokey AND h.hzdept_r = 0
            WHERE c.mukey IN ({mukey_str})
            AND c.comppct_r >= 15
            ORDER BY c.mukey, c.comppct_r DESC
        """  # nosec B608

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    SDA_API_URL,
                    json={"query": query, "format": "JSON+COLUMNNAME+METADATA"},
                )
                response.raise_for_status()
                data = response.json()

                if "Table" not in data or len(data["Table"]) < 2:
                    return None

                columns = data["Table"][0]
                rows = data["Table"][1:]
                return pd.DataFrame(rows, columns=columns)

        except Exception as e:
            logger.error("Failed to query SDA for soil properties: %s", e)
            return None

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "SSURGO Soil Survey Geographic Database",
            "source": "USDA Natural Resources Conservation Service (NRCS)",
            "url": "https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo",
            "license": "Public Domain",
            "coverage": "~95% of US counties",
            "format": "Tabular + spatial map units",
            "crs": "EPSG:4326",
            "update_frequency": "Annual",
            "storage_estimate": "5-20 MB per county",
            "key_fields": [
                "Organic matter content (elevated = human habitation indicator)",
                "Taxonomy subgroup (anthropic/plaggen = human-modified)",
                "Drainage class (well-drained terraces = preferred habitation)",
                "Parent material (alluvial = river-deposited, good for agriculture)",
                "pH value (anomalous pH can indicate cultural deposits)",
            ],
            "archaeological_rationale": (
                "Centuries of human habitation create 'anthrosols' with elevated "
                "phosphorus, darker color from charcoal, different texture from "
                "compaction, and anomalous organic matter. These signatures are "
                "detectable at regional scale via SSURGO soil survey data."
            ),
        }
