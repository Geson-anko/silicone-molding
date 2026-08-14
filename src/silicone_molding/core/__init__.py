"""Mesh processing that does not depend on ``bpy.ops`` or an interactive
context."""

from .solidify import (
    MIN_THICKNESS_MM,
    MODIFIER_NAME,
    apply_solidify,
    ensure_solidify,
    find_solidify,
)
from .units import mm_to_units

__all__ = [
    "MIN_THICKNESS_MM",
    "MODIFIER_NAME",
    "apply_solidify",
    "ensure_solidify",
    "find_solidify",
    "mm_to_units",
]
