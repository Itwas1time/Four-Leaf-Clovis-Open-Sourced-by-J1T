"""
GeoPackage-backed data store for ARCHAEO-SCAN.

All spatial data is stored in a single GeoPackage file — a portable,
standards-compliant SQLite database with spatial extensions. No database
server needed. A researcher can email the .gpkg file to a colleague
and they have the complete dataset.

GeoPackage was chosen over PostGIS because:
1. Zero infrastructure — no server to install or maintain
2. Portable — single file, works on any OS
3. Standard — readable by QGIS, ArcGIS, R, and every GIS tool
4. Sufficient — our query patterns are simple spatial lookups, not
   complex multi-table joins that need a full RDBMS
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import box, shape

from core.schemas import BoundingBox, DataLayer, ScoredCell


class DataStore:
    """
    Dual-file data store: GeoPackage for spatial layers + SQLite for metadata.

    Spatial data (GeoDataFrames) lives in a GPKG file managed exclusively
    by GDAL/pyogrio. Layer metadata and convergence scores live in a
    companion SQLite file (.meta.db) that we manage directly.

    This separation exists because GDAL is authoritative over the GPKG
    format — it writes the correct application_id, user_version, and
    system tables (gpkg_contents, gpkg_spatial_ref_sys). If we create
    the file first via sqlite3, GDAL either warns (bad application_id)
    or rejects it outright (missing system tables on append). And if
    GDAL creates the file from scratch, it wipes any pre-existing tables.

    Two files solve it cleanly: GDAL owns the .gpkg, we own the .meta.db.
    Both travel together (same directory, same stem).
    """

    def __init__(self, gpkg_path: str | Path):
        self.gpkg_path = Path(gpkg_path)
        self.meta_path = self.gpkg_path.with_suffix(".meta.db")
        self.gpkg_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_metadata_table()

    def _ensure_metadata_table(self) -> None:
        """Create the metadata + scores tables in the companion SQLite."""
        conn = sqlite3.connect(str(self.meta_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archaeo_layers (
                    name TEXT PRIMARY KEY,
                    source TEXT,
                    source_url TEXT,
                    license TEXT,
                    timestamp TEXT,
                    min_lat REAL,
                    min_lon REAL,
                    max_lat REAL,
                    max_lon REAL,
                    local_path TEXT,
                    format TEXT,
                    crs TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archaeo_scores (
                    cell_id TEXT PRIMARY KEY,
                    layer_scores_json TEXT,
                    composite_score REAL,
                    confidence REAL,
                    contributing_factors_json TEXT,
                    layer_count INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def store_layer(self, layer: DataLayer, gdf: gpd.GeoDataFrame) -> None:
        """
        Store a geospatial data layer in the GeoPackage.

        The GeoDataFrame is written as a named layer, and metadata is
        tracked in the archaeo_layers table for discovery and provenance.
        """
        # GDAL owns the .gpkg file exclusively. Use append if it already
        # exists (has content from a previous write), otherwise let GDAL
        # create it from scratch with all required GPKG system tables.
        if self.gpkg_path.exists() and self.gpkg_path.stat().st_size > 0:
            gdf.to_file(str(self.gpkg_path), layer=layer.name, driver="GPKG", mode="a")
        else:
            gdf.to_file(str(self.gpkg_path), layer=layer.name, driver="GPKG")

        # Write metadata to the companion .meta.db (never touches the GPKG)
        conn = sqlite3.connect(str(self.meta_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO archaeo_layers
                (name, source, source_url, license, timestamp,
                 min_lat, min_lon, max_lat, max_lon,
                 local_path, format, crs, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                layer.name,
                layer.source,
                layer.source_url,
                layer.license,
                layer.timestamp.isoformat(),
                layer.coverage_bbox.min_lat,
                layer.coverage_bbox.min_lon,
                layer.coverage_bbox.max_lat,
                layer.coverage_bbox.max_lon,
                str(layer.local_path),
                layer.format,
                layer.crs,
                json.dumps(layer.metadata),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_layer(self, name: str, bbox: BoundingBox | None = None) -> gpd.GeoDataFrame:
        """
        Retrieve a data layer, optionally clipped to a bounding box.

        Spatial filtering happens at read time via the bbox parameter,
        so we only load the data we need — critical for large layers
        like NHD hydrography.
        """
        read_bbox = bbox.as_tuple if bbox else None
        return gpd.read_file(
            str(self.gpkg_path),
            layer=name,
            bbox=read_bbox,
        )

    def layer_exists(self, name: str) -> bool:
        """Check if a layer exists in the GeoPackage."""
        try:
            import fiona
            layers = fiona.listlayers(str(self.gpkg_path))
            return name in layers
        except Exception:
            return False

    def list_layers(self) -> list[DataLayer]:
        """List all stored data layers with their metadata."""
        conn = sqlite3.connect(str(self.meta_path))
        try:
            cursor = conn.execute("SELECT * FROM archaeo_layers")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        finally:
            conn.close()

        layers = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            layers.append(DataLayer(
                name=row_dict["name"],
                source=row_dict["source"],
                source_url=row_dict.get("source_url", ""),
                license=row_dict.get("license", ""),
                timestamp=row_dict["timestamp"],
                coverage_bbox=BoundingBox(
                    min_lat=row_dict["min_lat"],
                    min_lon=row_dict["min_lon"],
                    max_lat=row_dict["max_lat"],
                    max_lon=row_dict["max_lon"],
                ),
                local_path=Path(row_dict["local_path"]),
                format=row_dict.get("format", "gpkg"),
                crs=row_dict.get("crs", "EPSG:4326"),
                metadata=json.loads(row_dict.get("metadata_json", "{}")),
            ))
        return layers

    def store_scores(self, scores: list[ScoredCell]) -> None:
        """
        Store convergence scores for a set of grid cells.

        Scores are upserted — if a cell already has a score, it's
        replaced with the new one. This supports iterative refinement
        as new data layers are added to a region.
        """
        conn = sqlite3.connect(str(self.meta_path))
        try:
            for score in scores:
                conn.execute("""
                    INSERT OR REPLACE INTO archaeo_scores
                    (cell_id, layer_scores_json, composite_score,
                     confidence, contributing_factors_json, layer_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    score.cell_id,
                    json.dumps(score.layer_scores),
                    score.composite_score,
                    score.confidence,
                    json.dumps(score.contributing_factors),
                    score.layer_count,
                ))
            conn.commit()
        finally:
            conn.close()

    def get_scores(
        self,
        bbox: BoundingBox | None = None,
        min_score: float = 0.0,
    ) -> list[ScoredCell]:
        """
        Retrieve scored cells, optionally filtered by bbox and minimum score.

        The bbox filter works by checking which H3 cell centers fall
        within the bounding box. This is approximate but fast.
        """
        conn = sqlite3.connect(str(self.meta_path))
        try:
            query = "SELECT * FROM archaeo_scores WHERE composite_score >= ?"
            params: list[Any] = [min_score]

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        finally:
            conn.close()

        scores = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            cell = ScoredCell(
                cell_id=row_dict["cell_id"],
                layer_scores=json.loads(row_dict["layer_scores_json"]),
                composite_score=row_dict["composite_score"],
                confidence=row_dict["confidence"],
                contributing_factors=json.loads(row_dict["contributing_factors_json"]),
                layer_count=row_dict["layer_count"],
            )

            # Filter by bbox if provided (check cell center via H3)
            if bbox:
                try:
                    import h3
                    lat, lon = h3.cell_to_latlng(cell.cell_id)
                    if not bbox.contains_point(lat, lon):
                        continue
                except Exception:
                    pass

            scores.append(cell)

        return sorted(scores, key=lambda s: s.composite_score, reverse=True)

    def delete_layer(self, name: str) -> None:
        """Remove a layer and its metadata."""
        # Drop metadata from companion DB
        conn = sqlite3.connect(str(self.meta_path))
        try:
            conn.execute("DELETE FROM archaeo_layers WHERE name = ?", (name,))
            conn.commit()
        finally:
            conn.close()

        # Try to drop the spatial table from the GPKG
        if self.gpkg_path.exists():
            gpkg_conn = sqlite3.connect(str(self.gpkg_path))
            try:
                gpkg_conn.execute(f'DROP TABLE IF EXISTS "{name}"')
                gpkg_conn.commit()
            except Exception:
                pass
            finally:
                gpkg_conn.close()

    def clear_scores(self) -> None:
        """Remove all scored cells (e.g., before re-scoring with new weights)."""
        conn = sqlite3.connect(str(self.meta_path))
        try:
            conn.execute("DELETE FROM archaeo_scores")
            conn.commit()
        finally:
            conn.close()
