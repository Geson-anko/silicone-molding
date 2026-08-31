"""Operator that branches an object's evaluated shape through Boolean."""

from typing import Final, override

import bpy

from ._operator import OperatorReturn

_OBJECT_SUFFIX: Final = ".inherit"
_MODIFIER_NAME: Final = "Inherit Shape"


def _active_mesh(context: bpy.types.Context) -> bpy.types.Object | None:
    """Return the active mesh object, if this context has one."""
    active = context.active_object
    return active if active is not None and active.type == "MESH" else None


class SILMOLD_OT_inherit_shape(bpy.types.Operator):
    """Create an empty mesh that inherits the active object's evaluated
    shape."""

    bl_idname = "silicone_molding.inherit_shape"
    bl_label = "Inherit Shape"
    bl_description = (
        "Create an empty mesh that references the active mesh through a Boolean "
        "modifier"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and _active_mesh(context) is not None

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        source = _active_mesh(context)
        if source is None:
            self.report({"ERROR"}, "Select an active mesh in Object Mode")
            return {"CANCELLED"}

        name = f"{source.name}{_OBJECT_SUFFIX}"
        mesh = bpy.data.meshes.new(name)
        inherited = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(inherited)
        inherited.matrix_world = source.matrix_world.copy()

        modifier = inherited.modifiers.new(_MODIFIER_NAME, "BOOLEAN")
        assert isinstance(modifier, bpy.types.BooleanModifier)
        modifier.operation = "UNION"
        modifier.operand_type = "OBJECT"
        modifier.solver = "EXACT"
        modifier.object = source

        for selected in context.selected_objects or ():
            selected.select_set(False)
        inherited.select_set(True)
        context.view_layer.objects.active = inherited

        self.report({"INFO"}, f"Inherited {source.name!r} as {inherited.name!r}")
        return {"FINISHED"}
