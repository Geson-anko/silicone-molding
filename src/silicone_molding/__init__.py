"""Silicone Molding -- generate 3D-printable resin molds for silicone casting.

Packaged as a Blender Extension: metadata lives in
``blender_manifest.toml``, not in a ``bl_info`` dict.
"""

import bpy

from .operators import SILMOLD_OT_apply_solidify, SILMOLD_OT_solidify
from .ui import SiliconeMoldingProperties, SILMOLD_PT_main

# Order within the tuple is cosmetic; Blender registers these independently.
# What does matter is that the Scene pointer is attached after the loop, since
# PointerProperty needs SiliconeMoldingProperties already registered.
_CLASSES = (
    SiliconeMoldingProperties,
    SILMOLD_OT_solidify,
    SILMOLD_OT_apply_solidify,
    SILMOLD_PT_main,
)


#: Name of the scene attribute the settings are exposed under. Blender adds
#: it to the Scene RNA type at register time, so it is set and cleared with
#: setattr/delattr rather than as a static attribute.
_SCENE_ATTR = "silicone_molding"


def register() -> None:
    """Register every class and attach the scene-level settings."""
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    setattr(
        bpy.types.Scene,
        _SCENE_ATTR,
        bpy.props.PointerProperty(type=SiliconeMoldingProperties),
    )


def unregister() -> None:
    """Detach the scene-level settings and unregister every class."""
    delattr(bpy.types.Scene, _SCENE_ATTR)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
