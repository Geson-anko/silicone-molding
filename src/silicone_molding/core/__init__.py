"""Mesh processing that does not depend on ``bpy.ops`` or an interactive
context."""

from .solidify import (
    MIN_THICKNESS_MM,
    MODIFIER_NAME,
    apply_solidify,
    ensure_solidify,
    find_solidify,
)
from .units import cubic_units_to_ml, format_ml, mm_to_units
from .volume import VolumeSummary, total_volume, world_volume

__all__ = [
    "MIN_THICKNESS_MM",
    "MODIFIER_NAME",
    "VolumeSummary",
    "apply_solidify",
    "cubic_units_to_ml",
    "ensure_solidify",
    "find_solidify",
    "format_ml",
    "mm_to_units",
    "total_volume",
    "world_volume",
]
