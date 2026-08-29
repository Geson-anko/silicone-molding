"""Operators that open, edit, and select the silicone mixture table."""

from typing import Final, cast, override

import bpy
from bpy.props import EnumProperty, IntProperty

from .solidify import OperatorReturn

_SELECTION_MODES = (
    ("REPLACE", "Replace", "Select only this row"),
    ("TOGGLE", "Toggle", "Toggle this row while preserving the others"),
    ("RANGE", "Range", "Select a continuous range from the anchor"),
    ("ADD_RANGE", "Add Range", "Add a continuous range from the anchor"),
)

_MIXTURE_DIALOG_WIDTH: Final = 900


class SILMOLD_OT_open_mixture_calculator(bpy.types.Operator):
    """Open the mixture calculator in a dedicated Blender window."""

    bl_idname = "silicone_molding.open_mixture_calculator"
    bl_label = "Open Mixture Calculator"
    _window_pointer = 0

    @override
    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        del event
        window_manager = context.window_manager
        existing_windows = {window.as_pointer() for window in window_manager.windows}
        result = bpy.ops.wm.window_new()
        if result != {"FINISHED"}:
            return result

        calculator_window = next(
            window
            for window in window_manager.windows
            if window.as_pointer() not in existing_windows
        )
        self._window_pointer = calculator_window.as_pointer()
        area = calculator_window.screen.areas[0]
        region = next(region for region in area.regions if region.type == "WINDOW")
        with context.temp_override(  # pyright: ignore[reportUnknownMemberType]
            window=calculator_window,
            area=area,
            region=region,
        ):
            return window_manager.invoke_props_dialog(
                self,
                width=_MIXTURE_DIALOG_WIDTH,
                title="Mixture Calculator",
                confirm_text="Close",
                translate=False,
            )

    @override
    def draw(self, context: bpy.types.Context) -> None:
        # Imported lazily to keep the operator and panel modules from importing
        # each other while Blender registers the extension.
        from ..ui.panel import draw_mixture_calculator

        layout = self.layout
        assert layout is not None
        draw_mixture_calculator(layout, context.scene.silicone_molding)

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        self._close_window(context)
        return {"FINISHED"}

    @override
    def cancel(self, context: bpy.types.Context) -> None:
        self._close_window(context)

    def _close_window(self, context: bpy.types.Context) -> None:
        window = context.window
        if (
            window is not None
            and window.as_pointer() == self._window_pointer
            and len(context.window_manager.windows) > 1
        ):
            self._window_pointer = 0
            bpy.ops.wm.window_close()


class SILMOLD_OT_add_mixture_part(bpy.types.Operator):
    """Add a manually entered part to the mixture table."""

    bl_idname = "silicone_molding.add_mixture_part"
    bl_label = "Add Mixture Part"
    bl_options = {"REGISTER", "UNDO"}

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        part = context.scene.silicone_molding.mixture_parts.add()
        part.enabled = True
        part.selected = False
        part.part_name = "Part"
        part.volume_ml = 0.0
        context.scene.silicone_molding.mixture_selection_anchor = -1
        return {"FINISHED"}


class SILMOLD_OT_remove_mixture_parts(bpy.types.Operator):
    """Remove every selected part from the mixture table."""

    bl_idname = "silicone_molding.remove_mixture_parts"
    bl_label = "Remove Selected Mixture Parts"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return any(
            part.selected for part in context.scene.silicone_molding.mixture_parts
        )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        props = context.scene.silicone_molding
        parts = props.mixture_parts
        for index in range(len(parts) - 1, -1, -1):
            if parts[index].selected:
                parts.remove(index)
        props.mixture_selection_anchor = -1
        return {"FINISHED"}


class SILMOLD_OT_move_mixture_parts(bpy.types.Operator):
    """Move selected mixture rows one position without reordering them."""

    bl_idname = "silicone_molding.move_mixture_parts"
    bl_label = "Move Selected Mixture Parts"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Direction",
        items=(
            ("UP", "Up", "Move selected rows up"),
            ("DOWN", "Down", "Move selected rows down"),
        ),
        default="UP",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return any(
            part.selected for part in context.scene.silicone_molding.mixture_parts
        )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        props = context.scene.silicone_molding
        parts = props.mixture_parts
        direction = cast(str, self.direction)  # pyright: ignore[reportUnknownMemberType]
        moved = False
        if direction == "UP":
            for index in range(1, len(parts)):
                if parts[index].selected and not parts[index - 1].selected:
                    parts.move(index, index - 1)
                    moved = True
        else:
            for index in range(len(parts) - 2, -1, -1):
                if parts[index].selected and not parts[index + 1].selected:
                    parts.move(index, index + 1)
                    moved = True
        props.mixture_selection_anchor = -1
        return {"FINISHED"} if moved else {"CANCELLED"}


class SILMOLD_OT_select_mixture_part(bpy.types.Operator):
    """Select one mixture row using standard modifier-key semantics."""

    bl_idname = "silicone_molding.select_mixture_part"
    bl_label = "Select Mixture Part"
    bl_options = {"INTERNAL"}

    index: IntProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Index",
        default=0,
        min=0,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    mode: EnumProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Mode",
        items=_SELECTION_MODES,
        default="REPLACE",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @override
    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if event.shift and event.ctrl:
            self.mode = "ADD_RANGE"  # pyright: ignore[reportUnknownMemberType]
        elif event.shift:
            self.mode = "RANGE"  # pyright: ignore[reportUnknownMemberType]
        elif event.ctrl:
            self.mode = "TOGGLE"  # pyright: ignore[reportUnknownMemberType]
        else:
            self.mode = "REPLACE"  # pyright: ignore[reportUnknownMemberType]
        return self.execute(context)

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        props = context.scene.silicone_molding
        parts = props.mixture_parts
        index = cast(int, self.index)  # pyright: ignore[reportUnknownMemberType]
        if index >= len(parts):
            return {"CANCELLED"}

        mode = cast(str, self.mode)  # pyright: ignore[reportUnknownMemberType]
        anchor = props.mixture_selection_anchor
        if mode in {"RANGE", "ADD_RANGE"} and 0 <= anchor < len(parts):
            if mode == "RANGE":
                for part in parts:
                    part.selected = False
            first, last = sorted((anchor, index))
            for selected_index in range(first, last + 1):
                parts[selected_index].selected = True
            return {"FINISHED"}

        if mode != "TOGGLE":
            for part in parts:
                part.selected = False
            parts[index].selected = True
        else:
            parts[index].selected = not parts[index].selected
        props.mixture_selection_anchor = index
        return {"FINISHED"}
