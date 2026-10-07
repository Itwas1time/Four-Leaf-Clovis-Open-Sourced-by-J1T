"""
NLP Document Geocoding module for ARCHAEO-SCAN.

Extracts spatial references from historical documents — expedition journals,
ethnographies, early land surveys, missionary accounts — and resolves them
to geographic coordinates. These texts contain firsthand descriptions of
archaeological sites that may have been destroyed, buried, or forgotten
since they were written. No satellite can replicate this knowledge layer.

Pipeline:
    1. document_ingestor  — Accept PDF/text/HTML/DOCX, chunk into passages
    2. spatial_extractor  — LLM-powered extraction of spatial references
    3. reference_resolver — Geocode extracted references via gazetteers + spatial logic
    4. knowledge_graph    — Link places, documents, time periods, and people
"""

from nlp.document_ingestor import DocumentIngestor
from nlp.spatial_extractor import SpatialExtractor
from nlp.reference_resolver import ReferenceResolver
from nlp.knowledge_graph import KnowledgeGraph

__all__ = [
    "DocumentIngestor",
    "SpatialExtractor",
    "ReferenceResolver",
    "KnowledgeGraph",
]
