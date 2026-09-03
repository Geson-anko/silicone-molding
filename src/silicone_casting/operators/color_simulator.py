"""Compatibility facade for the color simulator implementation."""

from ._color_adapter import (
    ColorantCollection as ColorantCollection,
    ColorantValues as ColorantValues,
    ColorProfileCollection as ColorProfileCollection,
    ColorProfileValues as ColorProfileValues,
    ColorSimulatorSettings as ColorSimulatorSettings,
    active_color_profile as active_color_profile,
    calculate_profile_appearance as calculate_profile_appearance,
    calculate_profile_color as calculate_profile_color,
)
from ._color_material import (
    _MATERIAL_PREFIX as _MATERIAL_PREFIX,  # pyright: ignore[reportPrivateUsage]
    _SHADER_NODE_NAME as _SHADER_NODE_NAME,  # pyright: ignore[reportPrivateUsage]
    _configure_material as _configure_material,  # pyright: ignore[reportPrivateUsage]
    _ValueSocket as _ValueSocket,  # pyright: ignore[reportPrivateUsage]
    ensure_color_preview_material as ensure_color_preview_material,
    update_color_preview_material as update_color_preview_material,
)
from ._color_operators import (
    SILCAST_OT_add_color_profile as SILCAST_OT_add_color_profile,
    SILCAST_OT_add_colorant as SILCAST_OT_add_colorant,
    SILCAST_OT_apply_color_material as SILCAST_OT_apply_color_material,
    SILCAST_OT_copy_mixture_volume_to_coloring as SILCAST_OT_copy_mixture_volume_to_coloring,
    SILCAST_OT_remove_color_profile as SILCAST_OT_remove_color_profile,
    SILCAST_OT_remove_colorant as SILCAST_OT_remove_colorant,
    _new_profile as _new_profile,  # pyright: ignore[reportPrivateUsage]
)
from ._operator import (
    OperatorReturn as OperatorReturn,
    selected_meshes as _selected_meshes,  # pyright: ignore[reportUnusedImport]
)
