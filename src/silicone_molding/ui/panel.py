"""Sidebar panels for the add-on."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Protocol, cast, override

import bpy

if TYPE_CHECKING:
    from bpy.types import bpy_prop_array

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

# Relative widths keep the whole table responsive while reserving most of the
# flexible space for the editable part name. Selection and Enabled stay compact.
_MIXTURE_COLUMN_WEIGHTS: Final = (
    0.65,
    1.2,
    4.4,
    1.55,
    1.55,
    1.55,
    1.55,
    1.55,
    1.55,
)


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
    mixture_parts: Sequence[_MixturePartValues]
    mixture_active_index: int


def _mixture_table_cells(
    layout: bpy.types.UILayout,
) -> tuple[bpy.types.UILayout, ...]:
    """Return responsive table cells using the shared column proportions."""
    remaining = layout.row(align=True)
    remaining_weight = sum(_MIXTURE_COLUMN_WEIGHTS)
    cells: list[bpy.types.UILayout] = []

    for weight in _MIXTURE_COLUMN_WEIGHTS[:-1]:
        split = remaining.split(factor=weight / remaining_weight, align=True)
        cells.append(split.column(align=True))
        remaining = split.column(align=True)
        remaining_weight -= weight

    cells.append(remaining)
    return tuple(cells)


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


def _draw_mixture_header(layout: bpy.types.UILayout) -> None:
    """Draw headings for the editable and calculated table columns."""
    cells = _mixture_table_cells(layout)
    for cell, label in zip(
        cells,
        ("#", "Enabled", "Name", "Vol", "W (g)", "A Vol", "B Vol", "A W", "B W"),
        strict=True,
    ):
        cell.label(text=label)


def _draw_mixture_output_cell(
    layout: bpy.types.UILayout, text: str, *, enabled: bool = True
) -> None:
    """Draw one derived value without disabling the editable inputs."""
    cell = layout.row(align=True)
    cell.enabled = enabled
    cell.label(text=text)


def _draw_mixture_part(
    layout: bpy.types.UILayout,
    props: _MixtureSettings,
    part: _MixturePartValues,
    index: int,
) -> None:
    """Draw one part across the full width of the calculator popover."""
    cells = _mixture_table_cells(layout)
    select = cells[0].operator(
        SILMOLD_OT_select_mixture_part.bl_idname,
        text=str(index + 1),
        depress=part.selected,
    )
    select.index = index
    cells[1].prop(part, "enabled", text="")
    cells[2].prop(part, "part_name", text="")
    cells[3].prop(part, "volume_ml", text="")

    breakdown = _mixture_breakdown(props, part.volume_ml)
    for cell, text in zip(
        cells[4:],
        (
            format_grams(breakdown.weight_g),
            format_ml(breakdown.a_volume_ml),
            format_ml(breakdown.b_volume_ml),
            format_grams(breakdown.a_weight_g),
            format_grams(breakdown.b_weight_g),
        ),
        strict=True,
    ):
        _draw_mixture_output_cell(cell, text, enabled=part.enabled)


def _draw_mixture_summary(
    layout: bpy.types.UILayout,
    props: _MixtureSettings,
    label: str,
    volume_ml: float,
) -> None:
    """Draw one subtotal using the same columns as a part row."""
    cells = _mixture_table_cells(layout)
    cells[0].label(text="")
    cells[1].label(text="")
    cells[2].label(text=label)
    cells[3].label(text=format_ml(volume_ml))

    breakdown = _mixture_breakdown(props, volume_ml)
    for cell, text in zip(
        cells[4:],
        (
            format_grams(breakdown.weight_g),
            format_ml(breakdown.a_volume_ml),
            format_ml(breakdown.b_volume_ml),
            format_grams(breakdown.a_weight_g),
            format_grams(breakdown.b_weight_g),
        ),
        strict=True,
    ):
        cell.label(text=text)


def _included_mixture_volume(
    props: _MixtureSettings, *, selected_only: bool = False
) -> float:
    """Sum enabled rows, optionally restricting the sum to selected rows."""
    return sum(
        part.volume_ml
        for part in props.mixture_parts
        if part.enabled and (not selected_only or part.selected)
    )


def _filter_mixture_parts_by_name(
    pattern: str,
    bitflag: int,
    parts: Sequence[_MixturePartValues],
    *,
    reverse: bool = False,
) -> list[int]:
    """Return Blender UI-list flags matching the saved part name."""
    return cast(
        list[int],
        bpy.types.UI_UL_list.filter_items_by_name(  # pyright: ignore[reportUnknownMemberType]
            pattern,
            bitflag,
            parts,
            "part_name",
            reverse=reverse,
        ),
    )


def draw_mixture_calculator(
    layout: bpy.types.UILayout, props: _MixtureSettings
) -> None:
    """Draw the saved settings and wide, manually entered mixture table."""
    settings = layout.box()
    density = settings.row(align=True)
    density.prop(props, "mixture_use_shared_density")
    if props.mixture_use_shared_density:
        density.prop(
            props,
            "mixture_density_a_g_per_ml",
            text="Density (g/mL)",
        )
    else:
        density.prop(props, "mixture_density_a_g_per_ml", text="Density A")
        density.prop(props, "mixture_density_b_g_per_ml", text="Density B")

    ratio = settings.row(align=True)
    ratio.prop(props, "mixture_ratio_a", text="Ratio A")
    ratio.prop(props, "mixture_ratio_b", text="Ratio B")

    guidance = layout.row(align=True)
    guidance.label(text="Select row numbers with Click / Ctrl / Shift")
    guidance.label(text="Volumes: mL / Weights: g")
    _draw_mixture_header(layout)
    layout.template_list(
        SILMOLD_UL_mixture_parts.bl_idname,
        "mixture_parts",
        props,
        "mixture_parts",
        props,
        "mixture_active_index",
        rows=6,
        maxrows=10,
    )

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
        layout.separator(factor=0.35)
        _draw_mixture_summary(layout, props, "Selected", selected_volume)

    total_volume = _included_mixture_volume(props)
    _draw_mixture_summary(layout, props, "Total", total_volume)


class SILMOLD_UL_mixture_parts(bpy.types.UIList):
    """Editable mixture rows with Blender's native active-row highlight."""

    bl_idname = "SILMOLD_UL_mixture_parts"

    @override
    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: object | None,
        item: object | None,
        icon: int | None,
        active_data: object,
        active_property: str | None,
        index: int | None,
        flt_flag: int | None,
    ) -> None:
        """Draw one editable table row inside the native UI list."""
        del context, data, icon, active_property, flt_flag
        if item is None or index is None:
            return
        props = cast(_MixtureSettings, active_data)
        part = cast(_MixturePartValues, item)
        _draw_mixture_part(layout, props, part, index)

    @override
    def filter_items(
        self,
        context: bpy.types.Context,
        data: object | None,
        property: str,
    ) -> tuple[bpy_prop_array, bpy_prop_array]:
        """Filter displayed rows by their editable Name value."""
        del context
        if data is None:
            return cast("bpy_prop_array", []), cast("bpy_prop_array", [])
        parts = cast(Sequence[_MixturePartValues], getattr(data, property))
        flags = _filter_mixture_parts_by_name(
            self.filter_name,
            self.bitflag_filter_item,
            parts,
            reverse=self.use_filter_invert,
        )
        # Blender consumes ordinary Python lists here, while the 5.1 stub
        # declares the callback result as bpy_prop_array.
        return (
            cast("bpy_prop_array", flags),
            cast("bpy_prop_array", []),
        )


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


class SILMOLD_PT_mixture_calculator(bpy.types.Panel):
    """Wide calculator opened as a popover beside the sidebar."""

    bl_label = "Mixture Calculator"
    bl_idname = "SILMOLD_PT_mixture_calculator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_ui_units_x = 48

    @override
    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        assert layout is not None
        draw_mixture_calculator(layout, context.scene.silicone_molding)


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

        layout.separator()
        layout.popover(
            panel=SILMOLD_PT_mixture_calculator.bl_idname,
            text="Mixture Calculator",
            icon="SPREADSHEET",
            direction="HORIZONTAL",
        )


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
