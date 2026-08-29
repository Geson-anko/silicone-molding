"""Operators that add, update, and bake the add-on's Solidify modifier."""

from typing import Literal, override

import bpy

from ..core import apply_solidify, ensure_solidify, find_solidify, mm_to_units

#: Blender's ``OperatorReturnItems`` RNA enum, spelled out so the module
#: stays importable at runtime (the stub-only alias is not).
OperatorReturn = set[
    Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]
]


def _selected_meshes(context: bpy.types.Context) -> list[bpy.types.Object]:
    """Return the selected mesh objects, silently skipping other types."""
    # `Context.selected_objects` is typed optional because space types without
    # an object selection do not provide it; that is the same as none selected.
    selected = context.selected_objects or ()
    return [obj for obj in selected if obj.type == "MESH"]


class SILMOLD_OT_solidify(bpy.types.Operator):
    """Add or update the add-on's Solidify modifier on every selected mesh."""

    bl_idname = "silicone_molding.solidify"
    bl_label = "Solidify"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and len(_selected_meshes(context)) > 0

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        props = context.scene.silicone_molding
        thickness = mm_to_units(
            props.solidify_thickness_mm,
            context.scene.unit_settings.scale_length,
        )
        objects = _selected_meshes(context)
        for obj in objects:
            ensure_solidify(
                obj,
                thickness,
                flip=props.solidify_flip,
                even_thickness=props.solidify_even_thickness,
            )

        self.report({"INFO"}, f"Solidified {len(objects)} object(s)")
        return {"FINISHED"}


class SILMOLD_OT_apply_solidify(bpy.types.Operator):
    """Bake the add-on's Solidify modifier into every selected mesh."""

    bl_idname = "silicone_molding.apply_solidify"
    # Spelled out because the F3 search menu shows the label on its own,
    # where a bare "Apply" says nothing about what is applied.
    bl_label = "Apply Solidify"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and any(
            find_solidify(obj) is not None for obj in _selected_meshes(context)
        )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        depsgraph = context.evaluated_depsgraph_get()
        applied = 0
        for obj in _selected_meshes(context):
            try:
                apply_solidify(obj, depsgraph)
            except ValueError as exc:
                # `core.apply_solidify` already names the object in its
                # message, so prefixing it here would repeat the name.
                self.report({"WARNING"}, str(exc))
                continue
            applied += 1

        if applied == 0:
            return {"CANCELLED"}

        self.report({"INFO"}, f"Applied to {applied} object(s)")
        return {"FINISHED"}
