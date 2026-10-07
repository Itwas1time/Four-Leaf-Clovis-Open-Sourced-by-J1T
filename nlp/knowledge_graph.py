"""
Lightweight knowledge graph for historical references.

Connects places, documents, time periods, features, and people/groups
using NetworkX. Enables convergence queries: "show all locations
referenced by multiple independent sources" — because multiple
independent sources pointing to the same location is strong evidence.

Archaeological rationale:
    A single expedition journal mentioning "a great mound by the river"
    could refer to any number of places. But when a 1542 Spanish account,
    an 1823 American survey, and a 1907 ethnography all describe features
    in the same area, that convergence of textual evidence parallels the
    convergence of environmental signals in the scoring model.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

import networkx as nx

from core.schemas import HistoricalReference, TimePeriod

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    NetworkX-based knowledge graph for geocoded historical references.

    Node types:
        - place: A resolved geographic location
        - document: A source document
        - period: A time period
        - feature: A described structure or landscape feature
        - person: A person (author, explorer, informant)

    Edge types:
        - REFERENCES: document -> place (with confidence)
        - DESCRIBES: document -> feature
        - DATED_TO: place/document -> period
        - AUTHORED: person -> document
        - VISITED: person -> place
        - HAS_FEATURE: place -> feature
        - NEAR: place -> place (spatial proximity)
    """

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

    # ------------------------------------------------------------------
    # Core mutation
    # ------------------------------------------------------------------

    def add_reference(self, ref: HistoricalReference) -> None:
        """
        Add a historical reference and all its relationships to the graph.

        Creates nodes for the document, resolved location, author (person),
        described features, and time period, then links them with typed edges.
        A single HistoricalReference can produce up to 5+ nodes and many edges.
        """
        doc_id = f"doc:{ref.source_document}"
        self.graph.add_node(doc_id, type="document", author=ref.author,
                           date=ref.document_date, label=ref.source_document)

        # Person node (author)
        person_id: str | None = None
        if ref.author:
            person_id = f"person:{ref.author}"
            self.graph.add_node(person_id, type="person",
                               name=ref.author, label=ref.author)
            self.graph.add_edge(person_id, doc_id, type="AUTHORED")

        # Place node (if geocoded)
        place_id: str | None = None
        if ref.resolved_lat is not None and ref.resolved_lon is not None:
            place_id = f"place:{ref.resolved_lat:.4f},{ref.resolved_lon:.4f}"
            self.graph.add_node(place_id, type="place",
                               lat=ref.resolved_lat, lon=ref.resolved_lon,
                               label=f"{ref.resolved_lat:.4f}N, {ref.resolved_lon:.4f}W")

            # Update confidence to max seen
            existing_conf = self.graph.nodes[place_id].get("confidence", 0.0)
            self.graph.nodes[place_id]["confidence"] = max(existing_conf, ref.confidence)
            self.graph.nodes[place_id]["method"] = ref.resolution_method

            self.graph.add_edge(doc_id, place_id,
                               type="REFERENCES",
                               confidence=ref.confidence,
                               method=ref.resolution_method,
                               text=ref.extracted_text[:200])

            # Person -> Place edge
            if person_id:
                self.graph.add_edge(person_id, place_id, type="VISITED")

        # Time period node
        if ref.time_period:
            period_id = f"period:{ref.time_period.value}"
            self.graph.add_node(period_id, type="period", label=ref.time_period.value)
            self.graph.add_edge(doc_id, period_id, type="DATED_TO")
            if place_id is not None:
                self.graph.add_edge(place_id, period_id, type="DATED_TO")

        # Feature nodes
        for feature in ref.described_features:
            feature_id = f"feature:{feature.lower().strip()}"
            self.graph.add_node(feature_id, type="feature", label=feature)
            self.graph.add_edge(doc_id, feature_id, type="DESCRIBES")
            if place_id is not None:
                self.graph.add_edge(place_id, feature_id, type="HAS_FEATURE")

    # ------------------------------------------------------------------
    # Convergence queries
    # ------------------------------------------------------------------

    def get_locations_by_convergence(self, min_sources: int = 2) -> list[dict[str, Any]]:
        """
        Find locations referenced by multiple independent sources.

        This is the key query: textual convergence mirrors environmental
        convergence. A place mentioned by 3+ independent documents is
        a high-priority candidate for investigation.

        Args:
            min_sources: Minimum number of distinct documents referencing
                         the place. Default 2 (any corroboration).

        Returns:
            Locations sorted by number of referencing documents (descending).
        """
        place_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "place"]

        results: list[dict[str, Any]] = []
        for place_id in place_nodes:
            data = self.graph.nodes[place_id]

            # Count incoming REFERENCES edges (from documents)
            referencing_docs: list[dict[str, Any]] = []
            for pred in self.graph.predecessors(place_id):
                for key, edge_data in self.graph[pred][place_id].items():
                    if edge_data.get("type") == "REFERENCES":
                        referencing_docs.append({
                            "document": pred,
                            "confidence": edge_data.get("confidence", 0),
                            "text": edge_data.get("text", ""),
                        })

            if len(referencing_docs) >= min_sources:
                # Get associated features
                features: list[str] = []
                for succ in self.graph.successors(place_id):
                    succ_data = self.graph.nodes[succ]
                    if succ_data.get("type") == "feature":
                        features.append(succ_data.get("label", ""))

                # Get time periods
                periods: list[str] = []
                for succ in self.graph.successors(place_id):
                    succ_data = self.graph.nodes[succ]
                    if succ_data.get("type") == "period":
                        periods.append(succ_data.get("label", ""))

                # Get people who visited this place
                people: list[str] = []
                for pred in self.graph.predecessors(place_id):
                    pred_data = self.graph.nodes[pred]
                    if pred_data.get("type") == "person":
                        people.append(pred_data.get("name", ""))

                avg_confidence = (sum(d["confidence"] for d in referencing_docs) /
                                  len(referencing_docs)) if referencing_docs else 0

                results.append({
                    "place_id": place_id,
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "source_count": len(referencing_docs),
                    "avg_confidence": round(avg_confidence, 3),
                    "documents": referencing_docs,
                    "features": features,
                    "periods": periods,
                    "people": people,
                })

        results.sort(key=lambda r: (r["source_count"], r["avg_confidence"]), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Location queries
    # ------------------------------------------------------------------

    def get_documents_for_location(
        self, lat: float, lon: float, radius_deg: float = 0.05
    ) -> list[dict[str, Any]]:
        """
        Find all documents referencing locations near a given point.

        Args:
            lat: Query latitude.
            lon: Query longitude.
            radius_deg: Coordinate tolerance in degrees (~5.5 km at mid-latitudes
                        with default 0.05).

        Returns:
            List of document metadata dicts with referencing edge details.
        """
        results: list[dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "place":
                continue
            node_lat = data.get("lat", 0)
            node_lon = data.get("lon", 0)
            if (abs(node_lat - lat) < radius_deg and abs(node_lon - lon) < radius_deg):
                for pred in self.graph.predecessors(node_id):
                    pred_data = self.graph.nodes[pred]
                    if pred_data.get("type") == "document":
                        # Collect edge details
                        edge_details: list[dict[str, Any]] = []
                        for _key, edge_data in self.graph[pred][node_id].items():
                            edge_details.append(dict(edge_data))

                        results.append({
                            "document": pred_data.get("label", pred),
                            "author": pred_data.get("author", ""),
                            "date": pred_data.get("date", ""),
                            "place_lat": node_lat,
                            "place_lon": node_lon,
                            "edges": edge_details,
                        })
        return results

    def get_features_at_location(
        self, lat: float, lon: float, radius_deg: float = 0.05
    ) -> list[str]:
        """Get all described features near a location."""
        features: set[str] = set()
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "place":
                continue
            if (abs(data.get("lat", 0) - lat) < radius_deg and
                    abs(data.get("lon", 0) - lon) < radius_deg):
                for succ in self.graph.successors(node_id):
                    succ_data = self.graph.nodes[succ]
                    if succ_data.get("type") == "feature":
                        features.add(succ_data.get("label", ""))
        return sorted(features)

    def get_places_for_period(self, period: TimePeriod) -> list[dict[str, Any]]:
        """
        Find all places associated with a specific time period.

        Useful for mapping the geographic extent of occupation during
        a particular archaeological era.
        """
        period_id = f"period:{period.value}"
        if not self.graph.has_node(period_id):
            return []

        results: list[dict[str, Any]] = []
        for pred in self.graph.predecessors(period_id):
            attrs = self.graph.nodes[pred]
            if attrs.get("type") == "place":
                results.append({
                    "place_id": pred,
                    "lat": attrs.get("lat"),
                    "lon": attrs.get("lon"),
                    "confidence": attrs.get("confidence", 0.0),
                    "label": attrs.get("label", ""),
                })
        return results

    def get_person_places(self, person_name: str) -> list[dict[str, Any]]:
        """
        Find all places associated with a person (author/explorer).

        Useful for reconstructing historical travel routes and
        identifying which sources cover overlapping geographies.
        """
        person_id = f"person:{person_name}"
        if not self.graph.has_node(person_id):
            return []

        results: list[dict[str, Any]] = []
        for succ in self.graph.successors(person_id):
            attrs = self.graph.nodes[succ]
            if attrs.get("type") == "place":
                results.append({
                    "place_id": succ,
                    "lat": attrs.get("lat"),
                    "lon": attrs.get("lon"),
                    "confidence": attrs.get("confidence", 0.0),
                    "label": attrs.get("label", ""),
                })
        return results

    # ------------------------------------------------------------------
    # GeoJSON export
    # ------------------------------------------------------------------

    def export_to_geojson(
        self,
        *,
        min_confidence: float = 0.0,
        min_sources: int = 1,
    ) -> dict[str, Any]:
        """
        Export all place nodes as a GeoJSON FeatureCollection.

        Each place includes its referencing documents, features, people,
        time periods, and convergence count — ready for display on the
        Atlas map or any GIS viewer.

        Args:
            min_confidence: Only export places with confidence >= this.
            min_sources: Only export places referenced by >= this many documents.

        Returns:
            GeoJSON FeatureCollection dict.
        """
        features: list[dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "place":
                continue

            lat = data.get("lat")
            lon = data.get("lon")
            if lat is None or lon is None:
                continue

            confidence = data.get("confidence", 0.0)
            if confidence < min_confidence:
                continue

            # Count references and collect extracted texts
            doc_count = 0
            extracted_texts: list[str] = []
            doc_labels: list[str] = []
            for pred in self.graph.predecessors(node_id):
                pred_data = self.graph.nodes[pred]
                if pred_data.get("type") == "document":
                    for _key, edge_data in self.graph[pred][node_id].items():
                        if edge_data.get("type") == "REFERENCES":
                            doc_count += 1
                            doc_labels.append(pred_data.get("label", pred))
                            text = edge_data.get("text", "")
                            if text:
                                extracted_texts.append(text)

            if doc_count < min_sources:
                continue

            # Features
            feature_list: list[str] = []
            for succ in self.graph.successors(node_id):
                if self.graph.nodes[succ].get("type") == "feature":
                    feature_list.append(self.graph.nodes[succ].get("label", ""))

            # Time periods
            period_list: list[str] = []
            for succ in self.graph.successors(node_id):
                if self.graph.nodes[succ].get("type") == "period":
                    period_list.append(self.graph.nodes[succ].get("label", ""))

            # People
            people_list: list[str] = []
            for pred in self.graph.predecessors(node_id):
                if self.graph.nodes[pred].get("type") == "person":
                    people_list.append(self.graph.nodes[pred].get("name", ""))

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "place_id": node_id,
                    "confidence": confidence,
                    "resolution_method": data.get("method", ""),
                    "document_count": doc_count,
                    "documents": doc_labels,
                    "features": feature_list,
                    "time_periods": period_list,
                    "people": people_list,
                    "extracted_texts": extracted_texts,
                    "label": data.get("label", ""),
                },
            })

        return {"type": "FeatureCollection", "features": features}

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, int]:
        """Return a summary of graph contents by node and edge type."""
        type_counts: dict[str, int] = defaultdict(int)
        for _, data in self.graph.nodes(data=True):
            type_counts[data.get("type", "unknown")] += 1

        edge_counts: dict[str, int] = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            edge_counts[data.get("type", "unknown")] += 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": dict(type_counts),
            "edge_types": dict(edge_counts),
        }
