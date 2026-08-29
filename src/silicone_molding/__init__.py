"""Silicone Molding -- generate 3D-printable resin molds for silicone casting.

Packaged as a Blender Extension: metadata lives in
``blender_manifest.toml``, not in a ``bl_info`` dict.
"""

import bpy
from bpy.app.handlers import persistent

from .operators import (
    SILMOLD_OT_add_mixture_part,
    SILMOLD_OT_apply_solidify,
    SILMOLD_OT_copy_value,
    SILMOLD_OT_export_stl,
    SILMOLD_OT_inherit_shape,
    SILMOLD_OT_measure_volume,
    SILMOLD_OT_move_mixture_parts,
    SILMOLD_OT_remove_mixture_parts,
    SILMOLD_OT_select_mixture_part,
    SILMOLD_OT_solidify,
)
from .ui import (
    SiliconeMoldingMixturePart,
    SiliconeMoldingProperties,
    SILMOLD_PT_main,
    SILMOLD_PT_measurement,
    SILMOLD_PT_mixture_calculator,
    SILMOLD_PT_processing,
    SILMOLD_UL_mixture_parts,
)

# The order matters: SILMOLD_PT_main has to be registered before its two
# sub-panels, because Blender resolves `bl_parent_id` at registration time and
# raises RuntimeError when the parent is not there yet, which would fail
# register() as a whole. The Scene pointer is attached after the loop, since
# PointerProperty needs SiliconeMoldingProperties already registered.
_CLASSES = (
    SiliconeMoldingMixturePart,
    SiliconeMoldingProperties,
    SILMOLD_OT_solidify,
    SILMOLD_OT_apply_solidify,
    SILMOLD_OT_measure_volume,
    SILMOLD_OT_copy_value,
    SILMOLD_OT_export_stl,
    SILMOLD_OT_inherit_shape,
    SILMOLD_OT_add_mixture_part,
    SILMOLD_OT_remove_mixture_parts,
    SILMOLD_OT_move_mixture_parts,
    SILMOLD_OT_select_mixture_part,
    SILMOLD_UL_mixture_parts,
    SILMOLD_PT_main,
    SILMOLD_PT_measurement,
    SILMOLD_PT_mixture_calculator,
    SILMOLD_PT_processing,
)


#: Name of the scene attribute the settings are exposed under. Blender adds
#: it to the Scene RNA type at register time, so it is set and cleared with
#: setattr/delattr rather than as a static attribute.
_SCENE_ATTR = "silicone_molding"


@persistent
def _reset_mixture_selection_state(_unused: object) -> None:
    """Clear transient mixture-list state after loading a file."""
    for scene in bpy.data.scenes:
        props = getattr(scene, _SCENE_ATTR, None)
        if props is not None:
            props.mixture_selection_anchor = -1
            props.mixture_active_index = -1


def register() -> None:
    """Register every class and attach the scene-level settings."""
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    setattr(
        bpy.types.Scene,
        _SCENE_ATTR,
        bpy.props.PointerProperty(type=SiliconeMoldingProperties),
    )
    if _reset_mixture_selection_state not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_reset_mixture_selection_state)


def unregister() -> None:
    """Detach the scene-level settings and unregister every class."""
    if _reset_mixture_selection_state in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_reset_mixture_selection_state)
    delattr(bpy.types.Scene, _SCENE_ATTR)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
