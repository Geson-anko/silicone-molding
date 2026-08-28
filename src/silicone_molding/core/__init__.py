"""Mesh processing that does not depend on ``bpy.ops`` or an interactive
context."""

from .mixture import MixtureBreakdown, calculate_mixture
from .solidify import (
    MIN_THICKNESS_MM,
    MODIFIER_NAME,
    apply_solidify,
    ensure_solidify,
    find_solidify,
)
from .units import cubic_units_to_ml, format_grams, format_ml, mm_to_units
from .volume import VolumeSummary, total_volume, world_volume

__all__ = [
    "MIN_THICKNESS_MM",
    "MixtureBreakdown",
    "MODIFIER_NAME",
    "VolumeSummary",
    "apply_solidify",
    "calculate_mixture",
    "cubic_units_to_ml",
    "ensure_solidify",
    "find_solidify",
    "format_grams",
    "format_ml",
    "mm_to_units",
    "total_volume",
    "world_volume",
]
