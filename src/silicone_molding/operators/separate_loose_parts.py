"""Operator that separates selected meshes by disconnected components."""

from typing import override

import bpy

from ..core import separate_loose_parts
from .solidify import OperatorReturn


def _selected_meshes(context: bpy.types.Context) -> list[bpy.types.Object]:
    """Return a stable snapshot of the selected mesh objects."""
    return [obj for obj in (context.selected_objects or ()) if obj.type == "MESH"]


class SILMOLD_OT_separate_loose_parts(bpy.types.Operator):
    """Separate each selected mesh into one object per loose part."""

    bl_idname = "silicone_molding.separate_loose_parts"
    bl_label = "Separate Loose Parts"
    bl_description = "Separate selected meshes into one object per loose part"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and len(_selected_meshes(context)) > 0

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        objects = _selected_meshes(context)
        created = 0
        for obj in objects:
            parts = separate_loose_parts(obj)
            created += len(parts) - 1
            for part in parts:
                part.select_set(True)

        self.report(
            {"INFO"},
            f"Separated {len(objects)} mesh(es), created {created} object(s)",
        )
        return {"FINISHED"}
