"""Scene-level settings shared by the add-on's operators and panels."""

import bpy
from bpy.props import FloatProperty

from ..core import MIN_THICKNESS


class SiliconeMoldingProperties(bpy.types.PropertyGroup):
    """Settings stored on the scene as ``Scene.silicone_molding``."""

    thickness: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Wall Thickness",
        description="Outward wall thickness of the generated mold shell",
        default=0.005,
        min=MIN_THICKNESS,
        soft_max=0.1,
        precision=4,
        unit="LENGTH",
    )
