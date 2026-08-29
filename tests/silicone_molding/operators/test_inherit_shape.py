"""Executable spec for creating a live, modifier-based shape branch.

The tests run against the real ``bpy`` wheel.  They exercise Blender's
actual object selection, modifier stack, depsgraph, and Boolean modifier;
nothing here mocks Blender APIs.
"""

from collections.abc import Callable, Iterator

import bpy
import pytest
from _helpers import make_cube_mesh

import silicone_molding
from silicone_molding.operators import SILMOLD_OT_inherit_shape

CUBE_SIZE = 2.0
SOLIDIFY_THICKNESS = 0.2

AddObject = Callable[..., bpy.types.Object]


def _leave_edit_mode() -> None:
    """Return to object mode so test-created objects can be removed."""
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    """Register the add-on so the operator is callable through ``bpy.ops``."""
    silicone_molding.register()
    yield
    silicone_molding.unregister()


@pytest.fixture
def add_object(registered: None) -> Iterator[AddObject]:
    """Create active scene objects and remove every test-created datablock."""
    del registered
    for existing in bpy.context.scene.objects:
        existing.select_set(False)
    bpy.context.view_layer.objects.active = None

    original_objects = {obj.as_pointer() for obj in bpy.data.objects}
    original_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}
    original_cameras = {camera.as_pointer() for camera in bpy.data.cameras}

    def add(name: str, data: bpy.types.ID | None = None) -> bpy.types.Object:
        mesh = data if data is not None else make_cube_mesh(CUBE_SIZE, f"{name}Mesh")
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return obj

    yield add

    _leave_edit_mode()
    for obj in list(bpy.data.objects):
        if obj.as_pointer() not in original_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.as_pointer() not in original_meshes:
            bpy.data.meshes.remove(mesh)
    for camera in list(bpy.data.cameras):
        if camera.as_pointer() not in original_cameras:
            bpy.data.cameras.remove(camera)


def _evaluated_mesh(obj: bpy.types.Object) -> bpy.types.Mesh:
    """Copy *obj*'s evaluated mesh for inspection by the caller."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    return bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))


class TestWhenTheInheritShapeButtonIsClickable:
    @pytest.mark.usefixtures("add_object")
    def test_the_button_is_not_clickable_without_an_active_object(self) -> None:
        assert not SILMOLD_OT_inherit_shape.poll(bpy.context)

    def test_the_button_is_not_clickable_for_an_active_non_mesh(
        self, add_object: AddObject
    ) -> None:
        add_object("Camera", bpy.data.cameras.new("CameraData"))

        assert not SILMOLD_OT_inherit_shape.poll(bpy.context)

    def test_the_button_is_clickable_for_the_active_mesh(
        self, add_object: AddObject
    ) -> None:
        add_object("Master")

        assert SILMOLD_OT_inherit_shape.poll(bpy.context)

    def test_the_button_is_not_clickable_outside_object_mode(
        self, add_object: AddObject
    ) -> None:
        add_object("Master")
        bpy.ops.object.mode_set(mode="EDIT")

        assert not SILMOLD_OT_inherit_shape.poll(bpy.context)


class TestInheritShapeOperator:
    def test_it_creates_an_empty_mesh_with_a_union_reference_to_the_source(
        self, add_object: AddObject
    ) -> None:
        source = add_object("Master")
        source.location = (3.0, -2.0, 5.0)
        source.rotation_euler = (0.1, 0.2, 0.3)
        source.scale = (1.5, 0.75, 2.0)
        bpy.context.view_layer.update()

        result = bpy.ops.silicone_molding.inherit_shape()

        inherited = bpy.context.active_object
        assert result == {"FINISHED"}
        assert inherited is not None
        assert inherited.name == "Master.inherit"
        assert inherited.type == "MESH"
        assert len(inherited.data.vertices) == 0
        assert tuple(value for row in inherited.matrix_world for value in row) == (
            pytest.approx(
                tuple(value for row in source.matrix_world for value in row),
                abs=1e-6,
            )
        )
        assert list(bpy.context.selected_objects) == [inherited]

        assert len(inherited.modifiers) == 1
        modifier = inherited.modifiers[0]
        assert isinstance(modifier, bpy.types.BooleanModifier)
        assert modifier.operation == "UNION"
        assert modifier.operand_type == "OBJECT"
        assert modifier.solver == "EXACT"
        assert modifier.object == source

    def test_the_inherited_result_includes_modifiers_without_baking_the_source(
        self, add_object: AddObject
    ) -> None:
        source = add_object("Master")
        source_mesh = source.data
        source_vertex_count = len(source_mesh.vertices)
        source_modifier = source.modifiers.new("Source Solidify", "SOLIDIFY")
        assert isinstance(source_modifier, bpy.types.SolidifyModifier)
        source_modifier.thickness = SOLIDIFY_THICKNESS
        source_modifier.offset = 1.0

        bpy.ops.silicone_molding.inherit_shape()

        inherited = bpy.context.active_object
        assert inherited is not None
        evaluated_source = _evaluated_mesh(source)
        evaluated_inherited = _evaluated_mesh(inherited)

        assert len(source.data.vertices) == source_vertex_count
        assert source.data == source_mesh
        assert source_modifier.name in source.modifiers
        assert len(evaluated_source.vertices) > source_vertex_count
        assert len(evaluated_inherited.vertices) == len(evaluated_source.vertices)
        assert len(evaluated_inherited.polygons) == len(evaluated_source.polygons)


@pytest.mark.api_contract
def test_inherit_shape_operator_keeps_its_idname() -> None:
    """The identifier is addressed by Blender UI, keymaps, and ``.blend``
    files."""
    assert SILMOLD_OT_inherit_shape.bl_idname == "silicone_molding.inherit_shape"
