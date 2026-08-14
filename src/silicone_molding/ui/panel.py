"""Sidebar panel for the add-on."""

from typing import override

import bpy

from ..operators import SILMOLD_OT_make_shell


class SILMOLD_PT_main(bpy.types.Panel):
    """Entry point for the add-on in the 3D View sidebar."""

    bl_label = "Silicone Molding"
    bl_idname = "SILMOLD_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Silicone Molding"

    @override
    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        # `Panel.layout` is typed optional because it is unset outside a draw
        # call; Blender always populates it before invoking draw().
        assert layout is not None
        layout.prop(context.scene.silicone_molding, "thickness")
        layout.operator(SILMOLD_OT_make_shell.bl_idname, icon="MOD_SOLIDIFY")
