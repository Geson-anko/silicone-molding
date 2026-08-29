"""Executable spec for adding configured Boolean modifiers.

The tests use Blender's real object and modifier data APIs. Nothing in
``bpy`` is mocked.
"""

from collections.abc import Callable, Iterator

import bpy
import pytest
from _helpers import make_cube_mesh

import silicone_molding
from silicone_molding.operators import SILMOLD_OT_add_boolean

CUBE_SIZE = 2.0

AddObject = Callable[..., bpy.types.Object]


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    silicone_molding.register()
    yield
    silicone_molding.unregister()


@pytest.fixture
def settings(registered: None) -> Iterator[bpy.types.PropertyGroup]:
    props = bpy.context.scene.silicone_molding
    props.boolean_operand = None
    props.boolean_solver = "EXACT"
    yield props
    props.boolean_operand = None


@pytest.fixture
def add_object(registered: None) -> Iterator[AddObject]:
    for existing in bpy.context.scene.objects:
        existing.select_set(False)
    bpy.context.view_layer.objects.active = None

    created: list[bpy.types.Object] = []

    def add(
        name: str, data: bpy.types.ID | None = None, *, select: bool = True
    ) -> bpy.types.Object:
        mesh = data if data is not None else make_cube_mesh(CUBE_SIZE, f"{name}Mesh")
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(select)
        created.append(obj)
        return obj

    yield add

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    datablocks = {(type(obj.data).__name__, obj.data.name): obj.data for obj in created}
    for obj in created:
        bpy.data.objects.remove(obj)
    bpy.data.batch_remove([data for data in datablocks.values() if data.users == 0])


def _set_inputs(
    settings: bpy.types.PropertyGroup,
    add_object: AddObject,
    *,
    operand_selected: bool = False,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    target = add_object("Target")
    operand = add_object("Operand", select=operand_selected)
    bpy.context.view_layer.objects.active = target
    settings.boolean_operand = operand
    return target, operand


class TestWhenTheButtonIsClickable:
    def test_a_selected_active_mesh_and_a_different_mesh_operand_are_required(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target, _operand = _set_inputs(settings, add_object)

        assert target.select_get()
        assert SILMOLD_OT_add_boolean.poll(bpy.context)

    def test_the_button_is_disabled_without_an_operand(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target = add_object("Target")
        bpy.context.view_layer.objects.active = target

        assert not SILMOLD_OT_add_boolean.poll(bpy.context)

    def test_the_button_is_disabled_when_target_and_operand_are_the_same(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target = add_object("Target")
        bpy.context.view_layer.objects.active = target
        settings.boolean_operand = target

        assert not SILMOLD_OT_add_boolean.poll(bpy.context)

    def test_the_button_is_disabled_when_the_active_target_is_not_selected(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target, _operand = _set_inputs(settings, add_object)
        target.select_set(False)

        assert not SILMOLD_OT_add_boolean.poll(bpy.context)

    def test_the_button_is_disabled_for_a_non_mesh_operand(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target = add_object("Target")
        camera = add_object("Camera", bpy.data.cameras.new("CameraData"), select=False)
        bpy.context.view_layer.objects.active = target
        settings.boolean_operand = camera

        assert not SILMOLD_OT_add_boolean.poll(bpy.context)

    def test_the_button_is_disabled_outside_object_mode(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        _set_inputs(settings, add_object)
        bpy.ops.object.mode_set(mode="EDIT")

        assert not SILMOLD_OT_add_boolean.poll(bpy.context)


class TestAddingABooleanModifier:
    @pytest.mark.parametrize("operation", ("DIFFERENCE", "UNION", "INTERSECT"))
    def test_each_operation_reaches_a_new_modifier(
        self,
        operation: str,
        settings: bpy.types.PropertyGroup,
        add_object: AddObject,
    ) -> None:
        target, operand = _set_inputs(settings, add_object)

        result = bpy.ops.silicone_molding.add_boolean(operation=operation)

        assert result == {"FINISHED"}
        assert len(target.modifiers) == 1
        modifier = target.modifiers[0]
        assert modifier.type == "BOOLEAN"
        assert modifier.operation == operation
        assert modifier.operand_type == "OBJECT"
        assert modifier.object == operand

    @pytest.mark.parametrize("solver", ("MANIFOLD", "EXACT", "FLOAT"))
    def test_each_solver_reaches_the_modifier(
        self,
        solver: str,
        settings: bpy.types.PropertyGroup,
        add_object: AddObject,
    ) -> None:
        target, _operand = _set_inputs(settings, add_object)
        settings.boolean_solver = solver

        result = bpy.ops.silicone_molding.add_boolean(operation="DIFFERENCE")

        assert result == {"FINISHED"}
        assert target.modifiers[0].solver == solver

    def test_repeating_the_action_adds_another_modifier(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target, _operand = _set_inputs(settings, add_object)

        bpy.ops.silicone_molding.add_boolean(operation="DIFFERENCE")
        bpy.ops.silicone_molding.add_boolean(operation="DIFFERENCE")

        assert [modifier.type for modifier in target.modifiers] == [
            "BOOLEAN",
            "BOOLEAN",
        ]

    def test_only_the_active_target_receives_the_modifier(
        self, settings: bpy.types.PropertyGroup, add_object: AddObject
    ) -> None:
        target, operand = _set_inputs(settings, add_object, operand_selected=True)
        other = add_object("OtherSelected")

        bpy.ops.silicone_molding.add_boolean(operation="UNION")

        assert len(target.modifiers) == 1
        assert len(operand.modifiers) == 0
        assert len(other.modifiers) == 0


@pytest.mark.api_contract
def test_boolean_operator_keeps_its_public_surface(registered: None) -> None:
    assert SILMOLD_OT_add_boolean.bl_idname == "silicone_molding.add_boolean"
    properties = bpy.ops.silicone_molding.add_boolean.get_rna_type().properties
    identifiers = {item.identifier for item in properties["operation"].enum_items}
    assert identifiers == {"DIFFERENCE", "UNION", "INTERSECT"}
