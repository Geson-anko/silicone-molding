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

    # Deliberately no ``unit="VOLUME"``, for the same reason as above: it
    # would make Blender render the value in the scene's unit settings, while
    # this add-on always reports volumes in cubic centimetres.
    volume_cm3: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Volume (cm3)",
        description=(
            "Total volume of the meshes selected when Measure Volume was last "
            "used. It is a snapshot: later changes to the scene do not update it"
        ),
        default=0.0,
        min=0.0,
        precision=2,
    )

    volume_measured: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Measured",
        description="Whether Volume (cm3) holds the result of a measurement",
        default=False,
    )
