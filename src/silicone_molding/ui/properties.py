"""Scene-level settings shared by the add-on's operators and panels."""

from collections.abc import Sequence
from typing import Protocol, cast

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from ..core import MIN_SURFACE_CUT_THICKNESS_MM, MIN_THICKNESS_MM

_MIN_DENSITY_G_PER_ML = 0.001
_MIN_MIXTURE_RATIO = 0.001
_MIN_COLORING_VOLUME_ML = 0.001
_MIN_CALIBRATION_DROPS_PER_ML = 0.001

_BOOLEAN_SOLVERS = (
    (
        "MANIFOLD",
        "Manifold",
        "Fastest solver for manifold meshes",
    ),
    (
        "EXACT",
        "Exact",
        "Best results for overlapping and coplanar geometry",
    ),
    (
        "FLOAT",
        "Float",
        "Simple fast solver without overlapping geometry support",
    ),
)


def _mesh_object_poll(
    _settings: bpy.types.PropertyGroup, obj: bpy.types.Object
) -> bool:
    """Only offer mesh objects in the Boolean operand picker."""
    return obj.type == "MESH"


class _SelectableMixturePart(Protocol):
    """Typed view used by the active-row update callback."""

    selected: bool


class _MixtureSelectionState(Protocol):
    """Typed view of dynamic RNA fields unavailable to static analysis."""

    mixture_active_index: int
    mixture_selection_anchor: int
    mixture_parts: Sequence[_SelectableMixturePart]


class SiliconeMoldingMixturePart(bpy.types.PropertyGroup):
    """One manually entered part in the silicone mixture table."""

    enabled: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Enabled",
        description="Include this part in mixture totals",
        default=True,
    )

    selected: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Selected",
        description="Include this part in the selected subtotal",
        default=False,
    )

    part_name: StringProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Name",
        default="Part",
    )

    # Deliberately no ``unit="VOLUME"``: mixture inputs are always mL.
    volume_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Volume (mL)",
        default=0.0,
        min=0.0,
        precision=2,
    )


def _update_color_profile(
    profile: bpy.types.PropertyGroup, _context: bpy.types.Context
) -> None:
    """Refresh a profile material after one of its saved inputs changes."""
    from ..operators.color_simulator import (
        ColorProfileValues,
        update_color_preview_material,
    )

    update_color_preview_material(cast(ColorProfileValues, profile))


def _update_colorant(
    colorant: bpy.types.PropertyGroup, _context: bpy.types.Context
) -> None:
    """Find the colorant's owning profile and refresh only that material."""
    from ..operators.color_simulator import update_color_preview_material

    settings = getattr(colorant.id_data, "silicone_molding", None)
    if settings is None:
        return
    pointer = colorant.as_pointer()
    for profile in settings.color_profiles:
        if any(item.as_pointer() == pointer for item in profile.colorants):
            update_color_preview_material(profile)
            return


def _get_result_color(profile: bpy.types.PropertyGroup) -> tuple[float, float, float]:
    """Calculate the result swatch without storing duplicate color data."""
    from ..operators.color_simulator import (
        ColorProfileValues,
        calculate_profile_color,
    )

    return calculate_profile_color(cast(ColorProfileValues, profile))


def _ignore_result_color_edit(
    _profile: bpy.types.PropertyGroup,
    _value: Sequence[float],
) -> None:
    """Keep the calculated swatch read-only while allowing full-color
    drawing."""


class SiliconeMoldingColorant(bpy.types.PropertyGroup):
    """One calibrated dye dose inside a named color profile."""

    enabled: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Enabled",
        description="Include this colorant in the simulated result",
        default=True,
        update=_update_colorant,
    )

    is_opacifier: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="White Opacifier",
        description=(
            "Treat this as white opacifier; at Calibration Drops / mL the "
            "result becomes fully opaque and milky"
        ),
        default=False,
        update=_update_colorant,
    )

    colorant_name: StringProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Name",
        default="Colorant",
    )

    calibration_color: FloatVectorProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Calibration Color",
        description=(
            "Observed color at this dye's Calibration Drops / mL in the current base"
        ),
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=_update_colorant,
    )

    calibration_drops_per_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Calibration Drops / mL",
        description=(
            "Dye concentration that produced Calibration Color; 1.0 drop/mL is "
            "only a starting estimate and can vary by dye"
        ),
        default=1.0,
        min=_MIN_CALIBRATION_DROPS_PER_ML,
        precision=2,
        step=100,
        update=_update_colorant,
    )

    drops: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Drops",
        description="Colorant amount; decimals support toothpick-sized doses",
        default=0.0,
        min=0.0,
        precision=2,
        step=100,
        update=_update_colorant,
    )


class SiliconeMoldingColorProfile(bpy.types.PropertyGroup):
    """A named silicone base, calibrated colorants, and preview material."""

    profile_name: StringProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Profile Name",
        default="Profile",
        update=_update_color_profile,
    )

    base_volume_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Base Volume (mL)",
        default=100.0,
        min=_MIN_COLORING_VOLUME_ML,
        precision=2,
        update=_update_color_profile,
    )

    base_color: FloatVectorProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Base Color",
        description="Untinted silicone color, including any natural yellow cast",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=_update_color_profile,
    )

    transparency: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Base Transparency",
        description="Original silicone: 1.0 is clear and 0.0 is opaque",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=_update_color_profile,
    )

    cloudiness: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Base Cloudiness",
        description="Original silicone: 0.0 is clear and 1.0 is milky white",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=_update_color_profile,
    )

    result_color: FloatVectorProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Result Color",
        description="Calculated mixed color; change the base or dyes to edit it",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        get=_get_result_color,
        set=_ignore_result_color_edit,
        options={"SKIP_SAVE"},
    )

    colorants: CollectionProperty(  # pyright: ignore[reportInvalidTypeForm]
        type=SiliconeMoldingColorant,
    )

    colorant_active_index: IntProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Active Colorant",
        default=-1,
        min=-1,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    preview_material: PointerProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Preview Material",
        type=bpy.types.Material,
    )


class SiliconeMoldingProperties(bpy.types.PropertyGroup):
    """Settings stored on the scene as ``Scene.silicone_molding``."""

    def _select_active_mixture_part(self, _context: bpy.types.Context) -> None:
        """Mirror native UI-list activation into the saved row selection."""
        state = cast(_MixtureSelectionState, self)
        index = state.mixture_active_index
        if not 0 <= index < len(state.mixture_parts):
            return
        for part_index, part in enumerate(state.mixture_parts):
            part.selected = part_index == index
        state.mixture_selection_anchor = index

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

    solidify_even_thickness: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Even Thickness",
        description="Keep the requested wall thickness around corners",
        default=True,
    )

    boolean_operand: PointerProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Operand",
        description="Mesh object used by the Boolean modifier",
        type=bpy.types.Object,
        poll=_mesh_object_poll,
    )

    boolean_solver: EnumProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Solver",
        description="Method used to calculate the Boolean operation",
        items=_BOOLEAN_SOLVERS,
        default="EXACT",
    )

    # Deliberately no ``unit="LENGTH"``: this value is always entered in mm,
    # then converted to Blender units when the modifier is created.
    surface_cut_thickness_mm: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Thickness (mm)",
        description="Surface Cut thickness in millimetres, regardless of scene units",
        default=MIN_SURFACE_CUT_THICKNESS_MM,
        min=MIN_SURFACE_CUT_THICKNESS_MM,
        precision=3,
    )

    # Deliberately no ``unit="VOLUME"``, for the same reason as above: it
    # would make Blender render the value in the scene's unit settings, while
    # this add-on always reports volumes in millilitres.
    volume_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Volume (mL)",
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
        description="Whether Volume (mL) holds the result of a measurement",
        default=False,
    )

    mixture_use_shared_density: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Same Density for A and B",
        description="Use part A's density for both parts",
        default=True,
    )

    mixture_density_a_g_per_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Density A (g/mL)",
        default=1.1,
        min=_MIN_DENSITY_G_PER_ML,
        soft_max=5.0,
        precision=3,
    )

    mixture_density_b_g_per_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Density B (g/mL)",
        default=1.1,
        min=_MIN_DENSITY_G_PER_ML,
        soft_max=5.0,
        precision=3,
    )

    mixture_ratio_a: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Ratio A",
        description="Relative weight of part A",
        default=1.0,
        min=_MIN_MIXTURE_RATIO,
        soft_max=100.0,
        precision=3,
    )

    mixture_ratio_b: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Ratio B",
        description="Relative weight of part B",
        default=1.0,
        min=_MIN_MIXTURE_RATIO,
        soft_max=100.0,
        precision=3,
    )

    mixture_parts: CollectionProperty(  # pyright: ignore[reportInvalidTypeForm]
        type=SiliconeMoldingMixturePart,
    )

    mixture_selection_anchor: IntProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Mixture Selection Anchor",
        default=-1,
        min=-1,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    mixture_active_index: IntProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Active Mixture Part",
        default=-1,
        min=-1,
        options={"HIDDEN", "SKIP_SAVE"},
        update=_select_active_mixture_part,
    )

    color_profiles: CollectionProperty(  # pyright: ignore[reportInvalidTypeForm]
        type=SiliconeMoldingColorProfile,
    )

    color_profile_active_index: IntProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Active Color Profile",
        default=-1,
        min=-1,
        options={"HIDDEN"},
    )
