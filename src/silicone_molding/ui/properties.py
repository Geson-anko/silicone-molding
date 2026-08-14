"""Scene-level settings shared by the add-on's operators and panels."""

import bpy
from bpy.props import BoolProperty, FloatProperty

from ..core import MIN_THICKNESS_MM


class SiliconeMoldingProperties(bpy.types.PropertyGroup):
    """Settings stored on the scene as ``Scene.silicone_molding``."""

    # Deliberately no ``unit="LENGTH"``: a length unit makes Blender display
    # and accept the value in the scene's ``unit_settings.length_unit``, which
    # contradicts this property always being expressed in millimetres.
    solidify_thickness_mm: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Thickness (mm)",
        description="Wall thickness in millimetres, regardless of scene units",
        default=3.0,
        min=MIN_THICKNESS_MM,
        soft_max=50.0,
        precision=2,
    )

    solidify_flip: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Flip Direction",
        description="Grow the wall inwards instead of outwards",
        default=False,
    )
