from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Iterable

from pyproj import CRS, Transformer
from shapely.errors import GEOSException
from shapely.geometry import Point, box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform, unary_union

from core.local_data import LocalDataStore
from core.discovery_planner import ARCHAEOLOGY_TERMS, SENSITIVE_TERMS, assess_candidate
from core.schemas import BoundingBox

EMPTY_FC = {"type": "FeatureCollection", "features": []}
MAX_AOI_FEATURES = 25
MAX_AOI_VERTICES = 5_000
MAX_CIRCLE_RADIUS_METERS = 100_000


def _finite_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def _projected_transformers(geom: BaseGeometry) -> tuple[Transformer, Transformer]:
    center = geom.centroid
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m"
    )
    forward = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    inverse = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True)
    return forward, inverse


def buffer_geometry_km(geom: BaseGeometry, distance_km: float) -> BaseGeometry:
    if not _finite_number(distance_km) or distance_km < 0:
        raise ValueError("Buffer distance must be a finite, nonnegative number.")
    if distance_km <= 0:
        return geom
    forward, inverse = _projected_transformers(geom)
    projected = shapely_transform(forward.transform, geom)
    buffered = projected.buffer(distance_km * 1000.0)
    return shapely_transform(inverse.transform, buffered)


def geometry_from_viewport(bounds: list[list[float]] | None) -> BaseGeometry:
    if not bounds or len(bounds) != 2:
        return box(-98.8, 39.2, -98.3, 39.7)
    south, west = bounds[0]
    north, east = bounds[1]
    return box(west, south, east, north)


def geometry_from_geojson(geojson: dict | None) -> BaseGeometry | None:
    if not geojson:
        return None
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection":
        raise ValueError("Drawn area must be a GeoJSON FeatureCollection.")
    features = geojson.get("features")
    if not isinstance(features, list) or len(features) > MAX_AOI_FEATURES:
        raise ValueError(f"Draw at most {MAX_AOI_FEATURES} area shapes.")
    vertex_count = 0

    def validate_coordinates(coordinates, depth=0):
        nonlocal vertex_count
        if depth > 4 or not isinstance(coordinates, (list, tuple)) or not coordinates:
            raise ValueError("Drawn area contains invalid coordinates.")
        if not isinstance(coordinates[0], (list, tuple)):
            if len(coordinates) != 2 or any(
                not _finite_number(value)
                for value in coordinates
            ) or not (-180 <= coordinates[0] <= 180 and -90 <= coordinates[1] <= 90):
                raise ValueError("Area coordinates must be finite longitude/latitude pairs in range.")
            vertex_count += 1
            if vertex_count > MAX_AOI_VERTICES:
                raise ValueError(f"Draw at most {MAX_AOI_VERTICES:,} area vertices.")
            return
        for item in coordinates:
            validate_coordinates(item, depth + 1)

    geometries: list[BaseGeometry] = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Each drawn area must be a GeoJSON Feature.")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon", "Point"}:
            raise ValueError("Draw a polygon, rectangle, or circle for area review.")
        validate_coordinates(geometry.get("coordinates"))
        try:
            geom = shape(geometry)
        except (TypeError, ValueError, KeyError, GEOSException) as exc:
            raise ValueError("Drawn area contains invalid geometry.") from exc
        if geom.is_empty or not geom.is_valid:
            raise ValueError("Drawn area must be nonempty and must not cross itself.")
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            raise ValueError("Drawn area properties must be an object.")
        radius = properties.get("radius")
        if geom.geom_type == "Point":
            if not _finite_number(radius) or not 0 < radius <= MAX_CIRCLE_RADIUS_METERS:
                raise ValueError("Circle radius must be a finite number from 0 to 100,000 meters, excluding 0.")
            geom = buffer_geometry_km(geom, radius / 1000.0)
        if geom.area <= 0:
            raise ValueError("Drawn area must cover a nonzero area.")
        geometries.append(geom)
    if not geometries:
        return None
    if len(geometries) == 1:
        return geometries[0]
    return unary_union(geometries)


def _bbox_from_geometry(geom: BaseGeometry) -> BoundingBox:
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    return BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)


def _point_feature(lat: float, lon: float, properties: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def _polygon_feature(geom: BaseGeometry, properties: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": properties,
    }


def _safe_text(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class CachedPolygon:
    name: str
    geometry: BaseGeometry
    properties: dict


@dataclass(frozen=True)
class _AreaPlanContext:
    """Limit record-text context to records intersecting the reviewed geometry."""

    master_sites: list[dict]
    nrhp_sites: list[dict]


class AOIAnalysisEngine:
    def __init__(self, project_root: Path | None = None):
        self.store = LocalDataStore(project_root)

    @staticmethod
    def archaeology_records(store: LocalDataStore) -> list[dict]:
        master = [
            {
                **record,
                "dataset": "open_context",
                "record_type": "documented_site",
            }
            for record in store.master_sites
            if record.get("source") == "open_context" and _safe_text(record.get("site_type")).lower() == "site"
            and not any(term in " ".join((
                _safe_text(record.get("name")), _safe_text(record.get("description")),
            )).lower() for term in SENSITIVE_TERMS)
        ]
        nrhp = [
            {
                **record,
                "dataset": "nrhp",
                "record_type": "archaeological_register_site",
            }
            for record in store.nrhp_sites
            if _safe_text(record.get("site_type")).upper() == "SITE"
            and any(term in " ".join((
                _safe_text(record.get("name")), _safe_text(record.get("description")),
            )).lower() for term in ARCHAEOLOGY_TERMS)
            and not any(term in " ".join((
                _safe_text(record.get("name")), _safe_text(record.get("description")),
            )).lower() for term in SENSITIVE_TERMS)
        ]
        return master + nrhp

    @staticmethod
    def paleo_records(store: LocalDataStore) -> list[dict]:
        return [
            {
                **record,
                "dataset": "fossil_processed",
                "record_type": "paleo_context",
            }
            for record in store.fossils
            if record.get("lat") is not None and record.get("lon") is not None
        ]

    @staticmethod
    @lru_cache(maxsize=1)
    def cached_native_records() -> tuple[CachedPolygon, ...]:
        store = LocalDataStore()
        rows: list[CachedPolygon] = []
        for record in store.native_territories:
            geometry = record.get("geometry")
            if not geometry:
                continue
            geom = shape(geometry)
            if geom.is_empty:
                continue
            rows.append(
                CachedPolygon(
                    name=_safe_text(record.get("name")) or "Native territory",
                    geometry=geom,
                    properties={
                        "name": _safe_text(record.get("name")) or "Native territory",
                        "native_name": _safe_text(record.get("native_name")),
                        "source": "Native Land Digital",
                        "territory_type": _safe_text(record.get("layer")) or "historical_territory",
                        "description": _safe_text(record.get("description")),
                        "is_historical": True,
                    },
                )
            )
        return tuple(rows)

    @staticmethod
    @lru_cache(maxsize=1)
    def cached_tribal_records() -> tuple[CachedPolygon, ...]:
        store = LocalDataStore()
        rows: list[CachedPolygon] = []
        for record in [*store.bia_tribal, *store.tiger_aiannh]:
            geometry = record.get("geometry")
            if not geometry:
                continue
            geom = shape(geometry)
            if geom.is_empty:
                continue
            props = record.get("properties") or {}
            rows.append(
                CachedPolygon(
                    name=_safe_text(record.get("name")) or _safe_text(props.get("LARNAME")) or "Tribal boundary",
                    geometry=geom,
                    properties={
                        "name": _safe_text(record.get("name")) or _safe_text(props.get("LARNAME")) or "Tribal boundary",
                        "source": _safe_text(record.get("source")) or "Local tribal dataset",
                        "boundary_type": _safe_text(record.get("boundary_type"))
                        or _safe_text(props.get("CLASSIFICATION"))
                        or "reservation",
                        "description": _safe_text(props.get("REGION")),
                    },
                )
            )
        return tuple(rows)

    def _filter_points(self, records: Iterable[dict], geom: BaseGeometry) -> list[dict]:
        bbox = _bbox_from_geometry(geom)
        results: list[dict] = []
        for record in records:
            lat = record.get("lat")
            lon = record.get("lon")
            if lat is None or lon is None:
                continue
            lat = float(lat)
            lon = float(lon)
            if not bbox.contains_point(lat, lon):
                continue
            point = Point(lon, lat)
            if geom.contains(point) or geom.touches(point):
                results.append(record)
        return results

    def _filter_polygons(self, records: Iterable[CachedPolygon], geom: BaseGeometry) -> list[CachedPolygon]:
        return [record for record in records if record.geometry.intersects(geom)]

    def analyze(
        self,
        *,
        aoi_geojson: dict | None,
        viewport_bounds: list[list[float]] | None,
        buffer_km: float,
    ) -> dict:
        if not _finite_number(buffer_km) or not 0 <= buffer_km <= 5:
            raise ValueError("Review buffer must be a finite number from 0 to 5 km.")
        aoi_geom = geometry_from_geojson(aoi_geojson) or geometry_from_viewport(viewport_bounds)
        buffered_geom = buffer_geometry_km(aoi_geom, buffer_km)

        all_sites = self.archaeology_records(self.store)
        nearby_sites = self._filter_points(all_sites, buffered_geom)
        aoi_sites = self._filter_points(nearby_sites, aoi_geom)
        nearby_only = [
            record for record in nearby_sites
            if record not in aoi_sites
        ]
        site_source_counts = dict(Counter(
            _safe_text(record.get("dataset")) or "unknown"
            for record in [*aoi_sites, *nearby_only]
        ))
        geocode_method_missing_count = sum(
            not _safe_text(record.get("geocode_method"))
            for record in [*aoi_sites, *nearby_only]
        )
        paleo_hits = self._filter_points(self.paleo_records(self.store), buffered_geom)
        native_hits = self._filter_polygons(self.cached_native_records(), buffered_geom)
        tribal_hits = self._filter_polygons(self.cached_tribal_records(), buffered_geom)

        study_bbox = _bbox_from_geometry(buffered_geom)
        plan = assess_candidate(
            {
                "name": "Selected study area",
                "bbox": [study_bbox.min_lat, study_bbox.min_lon, study_bbox.max_lat, study_bbox.max_lon],
            },
            _AreaPlanContext(
                master_sites=[record for record in nearby_sites if record.get("dataset") == "open_context"],
                nrhp_sites=[record for record in nearby_sites if record.get("dataset") == "nrhp"],
            ),
        )

        periods = [record.get("period") for record in nearby_sites if _safe_text(record.get("period"))]
        top_periods = [period for period, _ in Counter(periods).most_common(3)]

        evidence_lines = [
            f"{len(aoi_sites)} documented archaeological record(s) intersect the AOI.",
            f"{len(nearby_only)} more documented record(s) fall inside the {buffer_km:.1f} km buffer.",
        ]
        if native_hits:
            evidence_lines.append(
                f"{len(native_hits)} Native Land territory record(s) intersect the AOI or buffer."
            )
        if tribal_hits:
            evidence_lines.append(
                f"{len(tribal_hits)} tribal boundary record(s) intersect the AOI or buffer."
            )
        evidence_lines.append("Existing site records and fossil records are not independent signals of a new archaeological discovery.")

        legal_caution = (
            "Tribal or Native context overlaps this area. Do not dig, collect, or publicize exact locations. Consultation with Tribes, land managers, and the SHPO is appropriate before any ground disturbance."
            if native_hits or tribal_hits
            else "Public archaeological records occur nearby. Treat this as a caution zone and verify land ownership and state or federal law before any collecting or disturbance."
            if nearby_sites
            else "No indexed archaeological records or territory context were returned. Coverage is incomplete; verify land ownership, relevant communities, and state or federal requirements before any fieldwork."
        )

        known_sites_fc = {
            "type": "FeatureCollection",
            "features": [
                _point_feature(
                    float(record["lat"]),
                    float(record["lon"]),
                    {
                        "name": _safe_text(record.get("name")) or "Documented site",
                        "site_type": _safe_text(record.get("site_type")) or record.get("record_type"),
                        "period": _safe_text(record.get("period")) or "Undated",
                        "source": _safe_text(record.get("dataset")) or _safe_text(record.get("source")),
                        "description": _safe_text(record.get("description")),
                        "state": _safe_text(record.get("state")),
                        "record_id": _safe_text(record.get("source_id")),
                        "geocode_method": _safe_text(record.get("geocode_method")) or "Not reported",
                        "geocode_confidence": record.get("geocode_confidence"),
                    },
                )
                for record in aoi_sites[:600]
            ],
        }
        nearby_sites_fc = {
            "type": "FeatureCollection",
            "features": [
                _point_feature(
                    float(record["lat"]),
                    float(record["lon"]),
                    {
                        "name": _safe_text(record.get("name")) or "Nearby record",
                        "site_type": _safe_text(record.get("site_type")) or record.get("record_type"),
                        "period": _safe_text(record.get("period")) or "Undated",
                        "source": _safe_text(record.get("dataset")) or _safe_text(record.get("source")),
                        "description": _safe_text(record.get("description")),
                        "state": _safe_text(record.get("state")),
                        "record_id": _safe_text(record.get("source_id")),
                        "geocode_method": _safe_text(record.get("geocode_method")) or "Not reported",
                        "geocode_confidence": record.get("geocode_confidence"),
                    },
                )
                for record in nearby_only[:600]
            ],
        }
        paleo_fc = {
            "type": "FeatureCollection",
            "features": [
                _point_feature(
                    float(record["lat"]),
                    float(record["lon"]),
                    {
                        "name": _safe_text(record.get("common_name")) or _safe_text(record.get("name")) or "Paleo context",
                        "site_type": _safe_text(record.get("taxon_group")) or "Paleo context",
                        "period": _safe_text(record.get("time_period")) or "Undated",
                        "source": _safe_text(record.get("source")),
                        "description": _safe_text(record.get("institution")),
                    },
                )
                for record in paleo_hits[:500]
            ],
        }
        native_fc = {
            "type": "FeatureCollection",
            "features": [
                _polygon_feature(hit.geometry, hit.properties)
                for hit in native_hits[:80]
            ],
        }
        tribal_fc = {
            "type": "FeatureCollection",
            "features": [
                _polygon_feature(hit.geometry, hit.properties)
                for hit in tribal_hits[:80]
            ],
        }

        return {
            "aoi": _polygon_feature(
                aoi_geom,
                {
                    "name": "Selected AOI",
                    "source": "User drawn area" if aoi_geojson and (aoi_geojson.get("features") or []) else "Current viewport",
                    "buffer_km": buffer_km,
                },
            ),
            "buffer": _polygon_feature(
                buffered_geom,
                {
                    "name": "Analysis buffer",
                    "source": "Local analysis buffer",
                    "buffer_km": buffer_km,
                },
            ),
            "layers": {
                "known_sites": known_sites_fc,
                "nearby_sites": nearby_sites_fc,
                "paleo_context": paleo_fc,
                "tribal_boundaries": tribal_fc,
                "native_territories": native_fc,
                "scored_cells": EMPTY_FC,
                "hotspots": EMPTY_FC,
            },
            "summary": {
                "mode": "drawn_aoi" if aoi_geojson and (aoi_geojson.get("features") or []) else "viewport_fallback",
                "aoi_site_count": len(aoi_sites),
                "buffer_site_count": len(nearby_only),
                "site_source_counts": site_source_counts,
                "geocode_method_missing_count": geocode_method_missing_count,
                "paleo_count": len(paleo_hits),
                "tribal_count": len(tribal_hits),
                "native_count": len(native_hits),
                "research_priority_index": plan["priority_index"],
                "independent_signal_count": len(plan["independent_signals"]),
                "possible_find_classes": [item["class"] for item in plan["possible_find_classes"]],
                "finds_note": plan["finds_note"],
                "next_step": plan["next_step"],
                "data_gaps": plan["data_gaps"],
                "period_mix": top_periods or ["Undated in local public records"],
                "depth_context": "Depth is unknown without documented stratigraphy or field measurements.",
                "legal_caution": legal_caution,
                "evidence": evidence_lines,
            },
        }
