"""Length conversion between millimetres and Blender units.

Wall thickness is authored in millimetres because that is the language of
3D printing, while Blender stores lengths in its own unit system. This
module holds that conversion and nothing else: it must not import
``bpy``, so the scene's unit scale is passed in as a plain number by the
caller.
"""


def mm_to_units(mm: float, scale_length: float) -> float:
    """Convert a length in millimetres to Blender units.

    Args:
        mm: Length to convert, in millimetres.
        scale_length: Metres represented by one Blender unit, taken from
            ``scene.unit_settings.scale_length``. Blender only accepts
            positive values, so no zero guard is needed here.

    Returns:
        The same length expressed in Blender units.
    """
    return mm / 1000 / scale_length
