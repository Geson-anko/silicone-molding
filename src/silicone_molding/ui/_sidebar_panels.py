"""Panels shown in the add-on's 3D View sidebar."""

from __future__ import annotations

from typing import Final, override

import bpy

from ..core import format_ml
from ..operators import (
    SILMOLD_OT_add_boolean,
    SILMOLD_OT_add_surface_cut,
    SILMOLD_OT_apply_solidify,
    SILMOLD_OT_copy_value,
    SILMOLD_OT_export_stl,
    SILMOLD_OT_inherit_shape,
    SILMOLD_OT_measure_volume,
    SILMOLD_OT_separate_loose_parts,
    SILMOLD_OT_solidify,
)
from ._color_panel import SILMOLD_PT_color_simulator
from ._mixture_panel import SILMOLD_PT_mixture_calculator

#: Left column of the volume row. The unit lives in the label so that the
#: value stays a bare number, ready to be pasted into a spreadsheet.
_VOLUME_LABEL: Final = "Volume (mL)"

#: Stands in for the value before the first measurement. Keeping it to two
#: characters keeps the row's shape identical before and after measuring.
_NOT_MEASURED: Final = "--"


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

        layout.separator()
        layout.popover(
            panel=SILMOLD_PT_mixture_calculator.bl_idname,
            text="Mixture Calculator",
            icon="SPREADSHEET",
            direction="HORIZONTAL",
        )


class SILMOLD_PT_coloring(bpy.types.Panel):
    """Entry point for named silicone color recipes."""

    bl_label = "Coloring"
    bl_idname = "SILMOLD_PT_coloring"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = SILMOLD_PT_main.bl_idname
    bl_order = 1

    @override
    def draw(self, context: bpy.types.Context) -> None:
        del context
        layout = self.layout
        assert layout is not None
        layout.popover(
            panel=SILMOLD_PT_color_simulator.bl_idname,
            text="Color Mixing Simulator",
            icon="COLOR",
            direction="HORIZONTAL",
        )


class SILMOLD_PT_processing(bpy.types.Panel):
    """Operations that reshape the selected meshes."""

    bl_label = "Processing"
    bl_idname = "SILMOLD_PT_processing"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = SILMOLD_PT_main.bl_idname
    bl_order = 2

    @override
    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        # `Panel.layout` is typed optional because it is unset outside a draw
        # call; Blender always populates it before invoking draw().
        assert layout is not None
        props = context.scene.silicone_molding
        layout.prop(props, "solidify_thickness_mm")
        row = layout.row()
        row.prop(props, "solidify_flip")
        row.prop(props, "solidify_even_thickness")
        layout.operator(SILMOLD_OT_solidify.bl_idname, icon="MOD_SOLIDIFY")
        layout.operator(SILMOLD_OT_apply_solidify.bl_idname)
        layout.separator()
        boolean = layout.box()
        boolean.label(text="Boolean", icon="MOD_BOOLEAN")
        boolean.prop(props, "boolean_operand")
        boolean.prop(props, "boolean_solver", expand=True)
        operations = boolean.row(align=True)
        for operation, label in (
            ("DIFFERENCE", "Difference"),
            ("UNION", "Union"),
            ("INTERSECT", "Intersect"),
        ):
            button = operations.operator(
                SILMOLD_OT_add_boolean.bl_idname,
                text=label,
            )
            button.operation = operation
        boolean.prop(props, "surface_cut_thickness_mm")
        boolean.operator(
            SILMOLD_OT_add_surface_cut.bl_idname,
            icon="MOD_SOLIDIFY",
        )
        layout.operator(SILMOLD_OT_inherit_shape.bl_idname, icon="MOD_BOOLEAN")
        layout.operator(
            SILMOLD_OT_separate_loose_parts.bl_idname,
            icon="MESH_DATA",
        )
        layout.separator()
        layout.operator(SILMOLD_OT_export_stl.bl_idname, icon="EXPORT")
