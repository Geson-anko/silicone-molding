"""Operator that adds a configured Boolean modifier to the active mesh."""

from typing import Literal, Protocol, cast, override

import bpy
from bpy.props import EnumProperty

from .solidify import OperatorReturn

_BooleanOperation = Literal["DIFFERENCE", "UNION", "INTERSECT"]
_BooleanSolver = Literal["MANIFOLD", "EXACT", "FLOAT"]

_OPERATIONS = (
    ("DIFFERENCE", "Difference", "Subtract the operand from the active mesh"),
    ("UNION", "Union", "Combine the active mesh and operand"),
    ("INTERSECT", "Intersect", "Keep only the volume shared with the operand"),
)


class _BooleanSettings(Protocol):
    """Typed view of the Boolean fields stored on the scene."""

    boolean_operand: bpy.types.Object | None
    boolean_solver: _BooleanSolver


def _boolean_inputs(
    context: bpy.types.Context,
) -> tuple[bpy.types.Object, bpy.types.Object] | None:
    """Return a valid active target and distinct mesh operand."""
    target = context.active_object
    if (
        context.mode != "OBJECT"
        or target is None
        or target.type != "MESH"
        or not target.select_get()
    ):
        return None

    props = cast(_BooleanSettings, context.scene.silicone_molding)
    operand = props.boolean_operand
    if operand is None or operand.type != "MESH" or operand == target:
        return None
    return target, operand


class SILMOLD_OT_add_boolean(bpy.types.Operator):
    """Add one Boolean modifier to the active selected mesh."""

    bl_idname = "silicone_molding.add_boolean"
    bl_label = "Add Boolean Modifier"
    bl_options = {"REGISTER", "UNDO"}

    operation: EnumProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Operation",
        items=_OPERATIONS,
        default="DIFFERENCE",
        options={"SKIP_SAVE"},
    )

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        return _boolean_inputs(context) is not None

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        inputs = _boolean_inputs(context)
        if inputs is None:
            self.report(
                {"ERROR"},
                "Select an active mesh and choose a different mesh operand",
            )
            return {"CANCELLED"}

        target, operand = inputs
        props = cast(_BooleanSettings, context.scene.silicone_molding)
        operation = cast(
            _BooleanOperation,
            self.operation,  # pyright: ignore[reportUnknownMemberType]
        )
        modifier = cast(
            bpy.types.BooleanModifier,
            target.modifiers.new(name="Boolean", type="BOOLEAN"),
        )
        modifier.operand_type = "OBJECT"
        modifier.object = operand
        modifier.operation = operation
        modifier.solver = props.boolean_solver

        self.report({"INFO"}, f"Added {operation.title()} Boolean to {target.name}")
        return {"FINISHED"}
