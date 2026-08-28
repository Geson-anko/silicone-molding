"""Sidebar panels for the add-on."""

from collections.abc import Iterable
from typing import Final, Protocol, override

import bpy

from ..core import MixtureBreakdown, calculate_mixture, format_grams, format_ml
from ..operators import (
    SILMOLD_OT_add_mixture_part,
    SILMOLD_OT_apply_solidify,
    SILMOLD_OT_copy_value,
    SILMOLD_OT_export_stl,
    SILMOLD_OT_measure_volume,
    SILMOLD_OT_move_mixture_parts,
    SILMOLD_OT_remove_mixture_parts,
    SILMOLD_OT_select_mixture_part,
    SILMOLD_OT_solidify,
)

#: Left column of the volume row. The unit lives in the label so that the
#: value stays a bare number, ready to be pasted into a spreadsheet.
_VOLUME_LABEL: Final = "Volume (mL)"

#: Stands in for the value before the first measurement. Keeping it to two
#: characters keeps the row's shape identical before and after measuring.
_NOT_MEASURED: Final = "--"


class _MixturePartValues(Protocol):
    """Typed view of the RNA fields read by the panel."""

    enabled: bool
    selected: bool
    part_name: str
    volume_ml: float


class _MixtureSettings(Protocol):
    """Typed view of the mixture-related scene settings read by the panel."""

    mixture_use_shared_density: bool
    mixture_density_a_g_per_ml: float
    mixture_density_b_g_per_ml: float
    mixture_ratio_a: float
    mixture_ratio_b: float
    mixture_parts: Iterable[_MixturePartValues]


def _mixture_breakdown(props: _MixtureSettings, volume_ml: float) -> MixtureBreakdown:
    """Calculate one row using the density mode currently shown in the UI."""
    density_b = (
        props.mixture_density_a_g_per_ml
        if props.mixture_use_shared_density
        else props.mixture_density_b_g_per_ml
    )
    return calculate_mixture(
        volume_ml,
        props.mixture_density_a_g_per_ml,
        density_b,
        props.mixture_ratio_a,
        props.mixture_ratio_b,
    )


def _draw_mixture_input_header(layout: bpy.types.UILayout) -> None:
    """Draw headings for the editable first line of every table row."""
    grid = layout.grid_flow(columns=4, even_columns=True, align=True)
    grid.label(text="")
    grid.label(text="Enabled")
    grid.label(text="Name")
    grid.label(text="Volume (mL)")


def _draw_mixture_output_header(layout: bpy.types.UILayout) -> None:
    """Draw headings for the calculated second line of every table row."""
    grid = layout.grid_flow(columns=5, even_columns=True, align=True)
    grid.label(text="Weight (g)")
    grid.label(text="A Vol.")
    grid.label(text="B Vol.")
    grid.label(text="A Weight")
    grid.label(text="B Weight")


def _draw_mixture_output_values(
    layout: bpy.types.UILayout,
    breakdown: MixtureBreakdown,
    *,
    enabled: bool = True,
) -> None:
    """Draw a fixed two-decimal calculated row."""
    grid = layout.grid_flow(columns=5, even_columns=True, align=True)
    grid.enabled = enabled
    grid.label(text=format_grams(breakdown.weight_g))
    grid.label(text=format_ml(breakdown.a_volume_ml))
    grid.label(text=format_ml(breakdown.b_volume_ml))
    grid.label(text=format_grams(breakdown.a_weight_g))
    grid.label(text=format_grams(breakdown.b_weight_g))


def _draw_mixture_part(
    layout: bpy.types.UILayout,
    props: _MixtureSettings,
    part: _MixturePartValues,
    index: int,
) -> None:
    """Draw one editable input line and its derived output line."""
    box = layout.box()
    grid = box.grid_flow(columns=4, even_columns=True, align=True)
    select = grid.operator(
        SILMOLD_OT_select_mixture_part.bl_idname,
        text="",
        icon="CHECKBOX_HLT" if part.selected else "CHECKBOX_DEHLT",
        emboss=False,
    )
    select.index = index
    grid.prop(part, "enabled", text="")
    grid.prop(part, "part_name", text="")
    grid.prop(part, "volume_ml", text="")
    _draw_mixture_output_values(
        box,
        _mixture_breakdown(props, part.volume_ml),
        enabled=part.enabled,
    )


def _draw_mixture_summary(
    layout: bpy.types.UILayout,
    props: _MixtureSettings,
    label: str,
    volume_ml: float,
) -> None:
    """Draw one subtotal using the same columns as a part."""
    box = layout.box()
    heading = box.row(align=True)
    heading.label(text=label)
    heading.label(text=f"{format_ml(volume_ml)} mL")
    _draw_mixture_output_values(box, _mixture_breakdown(props, volume_ml))


def _included_mixture_volume(
    props: _MixtureSettings, *, selected_only: bool = False
) -> float:
    """Sum enabled rows, optionally restricting the sum to selected rows."""
    return sum(
        part.volume_ml
        for part in props.mixture_parts
        if part.enabled and (not selected_only or part.selected)
    )


def _draw_mixture_calculator(
    layout: bpy.types.UILayout, props: _MixtureSettings
) -> None:
    """Draw the saved settings and manually entered mixture table."""
    layout.separator()
    layout.label(text="Mixture Calculator")
    layout.prop(props, "mixture_use_shared_density")
    if props.mixture_use_shared_density:
        layout.prop(
            props,
            "mixture_density_a_g_per_ml",
            text="Density (g/mL)",
        )
    else:
        density = layout.row(align=True)
        density.prop(props, "mixture_density_a_g_per_ml", text="Density A")
        density.prop(props, "mixture_density_b_g_per_ml", text="Density B")

    ratio = layout.row(align=True)
    ratio.prop(props, "mixture_ratio_a", text="Ratio A")
    ratio.prop(props, "mixture_ratio_b", text="Ratio B")

    _draw_mixture_input_header(layout)
    _draw_mixture_output_header(layout)
    for index, part in enumerate(props.mixture_parts):
        _draw_mixture_part(layout, props, part, index)

    any_selected = any(part.selected for part in props.mixture_parts)
    controls = layout.row(align=True)
    controls.operator(SILMOLD_OT_add_mixture_part.bl_idname, text="", icon="ADD")
    selected_controls = controls.row(align=True)
    selected_controls.enabled = any_selected
    selected_controls.operator(
        SILMOLD_OT_remove_mixture_parts.bl_idname,
        text="",
        icon="REMOVE",
    )
    move_up = selected_controls.operator(
        SILMOLD_OT_move_mixture_parts.bl_idname,
        text="",
        icon="TRIA_UP",
    )
    move_up.direction = "UP"
    move_down = selected_controls.operator(
        SILMOLD_OT_move_mixture_parts.bl_idname,
        text="",
        icon="TRIA_DOWN",
    )
    move_down.direction = "DOWN"

    if any_selected:
        selected_volume = _included_mixture_volume(props, selected_only=True)
        _draw_mixture_summary(layout, props, "Selected", selected_volume)

    total_volume = _included_mixture_volume(props)
    _draw_mixture_summary(layout, props, "Total", total_volume)


class SILMOLD_PT_main(bpy.types.Panel):
    """Entry point for the add-on in the 3D View sidebar."""

    bl_label = "Silicone Molding"
    bl_idname = "SILMOLD_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Silicone Molding"

    @override
    def draw(self, context: bpy.types.Context) -> None:
        """Add nothing: this panel is a header, its sub-panels hold every
        control.

        The method stays because Blender refuses to register a panel
        without a ``draw``.
        """


class SILMOLD_PT_measurement(bpy.types.Panel):
    """Measured quantities of the current selection."""

    bl_label = "Measurement"
    bl_idname = "SILMOLD_PT_measurement"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # No bl_category: a child panel follows its parent's tab, so naming one
    # here would give the tab two sources of truth.
    bl_parent_id = SILMOLD_PT_main.bl_idname
    bl_order = 0

    @override
    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        # `Panel.layout` is typed optional because it is unset outside a draw
        # call; Blender always populates it before invoking draw().
        assert layout is not None
        props = context.scene.silicone_molding
        layout.operator(SILMOLD_OT_measure_volume.bl_idname, icon="DRIVER_DISTANCE")

        row = layout.split(factor=0.5)
        row.label(text=_VOLUME_LABEL)
        if not props.volume_measured:
            # Nothing to copy yet, so the value is a plain label.
            row.label(text=_NOT_MEASURED)
        else:
            # Formatted exactly once: the same string is what the user sees and
            # what the copy operator puts on the clipboard.
            text = format_ml(props.volume_ml)
            # `layout.label` cannot be clicked, so the value is drawn as the text
            # of an un-embossed operator button instead.
            copy = row.operator(
                SILMOLD_OT_copy_value.bl_idname, text=text, emboss=False
            )
            copy.value = text

        _draw_mixture_calculator(layout, props)


class SILMOLD_PT_processing(bpy.types.Panel):
    """Operations that reshape the selected meshes."""

    bl_label = "Processing"
    bl_idname = "SILMOLD_PT_processing"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = SILMOLD_PT_main.bl_idname
    bl_order = 1

    @override
    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        # `Panel.layout` is typed optional because it is unset outside a draw
        # call; Blender always populates it before invoking draw().
        assert layout is not None
        props = context.scene.silicone_molding
        layout.prop(props, "solidify_thickness_mm")
        layout.prop(props, "solidify_flip")
        layout.operator(SILMOLD_OT_solidify.bl_idname, icon="MOD_SOLIDIFY")
        layout.operator(SILMOLD_OT_apply_solidify.bl_idname)
        layout.separator()
        layout.operator(SILMOLD_OT_export_stl.bl_idname, icon="EXPORT")
