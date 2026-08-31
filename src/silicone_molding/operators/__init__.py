"""Operators exposed by the add-on."""

from .boolean_modifier import SILMOLD_OT_add_boolean, SILMOLD_OT_add_surface_cut
from .color_simulator import (
    SILMOLD_OT_add_color_profile,
    SILMOLD_OT_add_colorant,
    SILMOLD_OT_apply_color_material,
    SILMOLD_OT_copy_mixture_volume_to_coloring,
    SILMOLD_OT_remove_color_profile,
    SILMOLD_OT_remove_colorant,
)
from .copy_value import SILMOLD_OT_copy_value
from .export_stl import SILMOLD_OT_export_stl
from .inherit_shape import SILMOLD_OT_inherit_shape
from .measure_volume import SILMOLD_OT_measure_volume
from .mixture_parts import (
    SILMOLD_OT_add_mixture_part,
    SILMOLD_OT_move_mixture_parts,
    SILMOLD_OT_remove_mixture_parts,
    SILMOLD_OT_select_mixture_part,
)
from .separate_loose_parts import SILMOLD_OT_separate_loose_parts
from .solidify import SILMOLD_OT_apply_solidify, SILMOLD_OT_solidify

__all__ = [
    "SILMOLD_OT_add_boolean",
    "SILMOLD_OT_add_color_profile",
    "SILMOLD_OT_add_colorant",
    "SILMOLD_OT_add_surface_cut",
    "SILMOLD_OT_apply_solidify",
    "SILMOLD_OT_apply_color_material",
    "SILMOLD_OT_add_mixture_part",
    "SILMOLD_OT_copy_value",
    "SILMOLD_OT_copy_mixture_volume_to_coloring",
    "SILMOLD_OT_export_stl",
    "SILMOLD_OT_inherit_shape",
    "SILMOLD_OT_measure_volume",
    "SILMOLD_OT_move_mixture_parts",
    "SILMOLD_OT_remove_color_profile",
    "SILMOLD_OT_remove_colorant",
    "SILMOLD_OT_remove_mixture_parts",
    "SILMOLD_OT_select_mixture_part",
    "SILMOLD_OT_separate_loose_parts",
    "SILMOLD_OT_solidify",
]
