"""Operator that copies a value shown in the sidebar to the clipboard."""

from typing import cast, override

import bpy
from bpy.props import StringProperty

from .solidify import OperatorReturn


class SILMOLD_OT_copy_value(bpy.types.Operator):
    """Copy this value to the clipboard."""

    bl_idname = "silicone_molding.copy_value"
    bl_label = "Copy Value"
    # The button's text is the value itself, so the tooltip is the only place
    # that can tell the user a click copies it.
    bl_description = "Copy this value to the clipboard"
    # No "UNDO": nothing in the scene changes, so pushing an undo step would
    # make the next Ctrl+Z swallow the user's last real edit instead.
    # "INTERNAL" hides it from the F3 search, where it would be called
    # without a value to copy.
    bl_options = {"REGISTER", "INTERNAL"}

    value: StringProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Value",
        default="",
    )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        # A `bpy.props` annotation is not a type, so pyright cannot tell what
        # the attribute resolves to; Blender turns it into a plain str at
        # register time.
        value = cast(str, self.value)  # pyright: ignore[reportUnknownMemberType]
        context.window_manager.clipboard = value
        self.report({"INFO"}, f"Copied {value}")
        return {"FINISHED"}
