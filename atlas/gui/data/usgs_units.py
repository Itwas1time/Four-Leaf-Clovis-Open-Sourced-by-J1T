"""GUI-facing import for the offline USGS Cooperative National Geologic Map."""

from core.usgs_unit_library import (
    available,
    catalog_stats,
    get_unit,
    search_units,
    units_for_place,
)

__all__ = [
    "available",
    "catalog_stats",
    "get_unit",
    "search_units",
    "units_for_place",
]
