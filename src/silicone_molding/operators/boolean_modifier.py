"""Operators that add Boolean modifiers to the active mesh."""

from typing import Final, Literal, Protocol, cast, override

import bpy
from bpy.props import EnumProperty

from ..core import ensure_solidify, mm_to_units
from .solidify import OperatorReturn

_BooleanOperation = Literal["DIFFERENCE", "UNION", "INTERSECT"]
_BooleanSolver = Literal["MANIFOLD", "EXACT", "FLOAT"]

# The working prototype used 1e-6 BU in a metre-scale scene. Expressing the
# same physical thickness in millimetres keeps the cut stable when a scene
# uses a different unit scale.
_SURFACE_CUT_THICKNESS_MM: Final = 0.001

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


def _add_boolean_modifier(
    target: bpy.types.Object,
    operand: bpy.types.Object,
    operation: _BooleanOperation,
    solver: _BooleanSolver,
) -> bpy.types.BooleanModifier:
    """Add and configure one object-operand Boolean modifier."""
    modifier = cast(
        bpy.types.BooleanModifier,
        target.modifiers.new(name="Boolean", type="BOOLEAN"),
    )
    modifier.operand_type = "OBJECT"
    modifier.object = operand
    modifier.operation = operation
    modifier.solver = solver
    return modifier


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
        _add_boolean_modifier(target, operand, operation, props.boolean_solver)

        self.report({"INFO"}, f"Added {operation.title()} Boolean to {target.name}")
        return {"FINISHED"}


class SILMOLD_OT_add_surface_cut(bpy.types.Operator):
    """Turn the operand into a thin cutter and subtract it from the target."""

    bl_idname = "silicone_molding.add_surface_cut"
    bl_label = "Add Surface Cut"
    bl_description = (
        "Solidify the operand into a thin cutting surface and add a Manifold "
        "Difference modifier to the active mesh"
    )
    bl_options = {"REGISTER", "UNDO"}

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

        target, surface = inputs
        thickness = mm_to_units(
            _SURFACE_CUT_THICKNESS_MM,
            context.scene.unit_settings.scale_length,
        )
        ensure_solidify(
            surface,
            thickness,
            flip=True,
            even_thickness=False,
        )
        _add_boolean_modifier(target, surface, "DIFFERENCE", "MANIFOLD")

        self.report(
            {"INFO"},
            f"Added surface cut from {surface.name} to {target.name}",
        )
        return {"FINISHED"}
