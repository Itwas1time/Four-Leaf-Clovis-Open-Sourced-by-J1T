"""
Citizen science module for ARCHAEO-SCAN.

Provides infrastructure for collecting, validating, classifying, and
spatially analyzing field reports from citizen scientists. Surface finds
reported by hikers, farmers, and amateur archaeologists represent
irreplaceable ground-truth data that no satellite or LiDAR scan can
replicate — erosion events, plowing, and construction expose artifacts
that are visible only briefly before being destroyed or reburied.

Components:
    report_schema   — Pydantic models for report submission and tracking
    find_classifier — Multimodal LLM classification of photographed finds
    hotzone_detector — DBSCAN spatial clustering of citizen reports
    api             — FastAPI endpoints for report submission and queries
"""

from citizen.report_schema import (
    ReportSubmission,
    ReportStatus,
    ReporterProfile,
    ReportStatusEnum,
)
from citizen.find_classifier import FindClassifier
from citizen.hotzone_detector import HotzoneDetector
from citizen.api import create_app

__all__ = [
    "ReportSubmission",
    "ReportStatus",
    "ReporterProfile",
    "ReportStatusEnum",
    "FindClassifier",
    "HotzoneDetector",
    "create_app",
]
