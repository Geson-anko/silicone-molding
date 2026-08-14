"""Operator wrapping :func:`silicone_molding.core.build_shell_mesh`."""

from typing import Literal, override

import bpy

from ..core import build_shell_mesh

#: Blender's ``OperatorReturnItems`` RNA enum, spelled out so the module
#: stays importable at runtime (the stub-only alias is not).
OperatorReturn = set[
    Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]
]


class SILMOLD_OT_make_shell(bpy.types.Operator):
    """Create an outward offset shell around the active mesh."""

    bl_idname = "silicone_molding.make_shell"
    bl_label = "Make Shell"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        obj = context.active_object
        if obj is None or not isinstance(obj.data, bpy.types.Mesh):
            self.report({"ERROR"}, "Active object is not a mesh")
            return {"CANCELLED"}

        thickness = context.scene.silicone_molding.thickness
        try:
            shell_mesh = build_shell_mesh(
                obj.data, thickness, name=f"{obj.data.name}_Shell"
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        shell_obj = bpy.data.objects.new(f"{obj.name}_Shell", shell_mesh)
        context.collection.objects.link(shell_obj)
        shell_obj.matrix_world = obj.matrix_world.copy()

        self.report({"INFO"}, f"Created {shell_obj.name}")
        return {"FINISHED"}
