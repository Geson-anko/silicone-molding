"""Mesh processing that does not depend on ``bpy.ops`` or an interactive
context."""

from .solidify import (
    MIN_THICKNESS_MM,
    MODIFIER_NAME,
    apply_solidify,
    ensure_solidify,
    find_solidify,
)
from .units import cubic_units_to_cm3, format_cm3, mm_to_units
from .volume import VolumeSummary, total_volume, world_volume

__all__ = [
    "MIN_THICKNESS_MM",
    "MODIFIER_NAME",
    "VolumeSummary",
    "apply_solidify",
    "cubic_units_to_cm3",
    "ensure_solidify",
    "find_solidify",
    "format_cm3",
    "mm_to_units",
    "total_volume",
    "world_volume",
]
