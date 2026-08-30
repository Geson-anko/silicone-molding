"""Operator behaviour for separating selected mesh objects by loose parts."""

from collections.abc import Iterator

import bpy
import pytest

import silicone_molding
from silicone_molding.operators import SILMOLD_OT_separate_loose_parts

PART_VERTICES = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (3.0, 0.0, 0.0),
    (4.0, 0.0, 0.0),
    (3.0, 1.0, 0.0),
]
PART_FACES = [(0, 1, 2), (3, 4, 5)]


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    silicone_molding.register()
    yield
    silicone_molding.unregister()


@pytest.fixture
def loose_object(registered: None) -> Iterator[bpy.types.Object]:
    for existing in bpy.context.scene.objects:
        existing.select_set(False)
    bpy.context.view_layer.objects.active = None
    existing_objects = set(bpy.data.objects.keys())
    existing_meshes = set(bpy.data.meshes.keys())
    existing_collections = set(bpy.data.collections.keys())

    mesh = bpy.data.meshes.new("LooseTrianglesMesh")
    mesh.from_pydata(PART_VERTICES, [], PART_FACES)
    mesh.update()
    obj = bpy.data.objects.new("LooseTriangles", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    yield obj

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for created in tuple(bpy.data.objects):
        if created.name not in existing_objects:
            bpy.data.objects.remove(created)
    for created in tuple(bpy.data.meshes):
        if created.name not in existing_meshes and created.users == 0:
            bpy.data.meshes.remove(created)
    for created in tuple(bpy.data.collections):
        if created.name not in existing_collections:
            bpy.data.collections.remove(created)


def test_the_button_is_available_for_a_selected_mesh(
    loose_object: bpy.types.Object,
) -> None:
    assert SILMOLD_OT_separate_loose_parts.poll(bpy.context)


def test_the_button_is_disabled_outside_object_mode(
    loose_object: bpy.types.Object,
) -> None:
    bpy.ops.object.mode_set(mode="EDIT")

    assert not SILMOLD_OT_separate_loose_parts.poll(bpy.context)


def test_applied_parts_are_written_to_a_collection_and_the_source_is_hidden(
    loose_object: bpy.types.Object,
) -> None:
    source_mesh = loose_object.data
    solidify = loose_object.modifiers.new("Hidden Solidify", "SOLIDIFY")
    solidify.thickness = 0.25
    solidify.show_viewport = False

    result = bpy.ops.silicone_molding.separate_loose_parts()

    assert result == {"FINISHED"}
    assert loose_object.data == source_mesh
    assert len(loose_object.data.vertices) == 6
    assert len(loose_object.data.polygons) == 2
    assert len(loose_object.modifiers) == 1
    assert not solidify.show_viewport
    assert loose_object.hide_get()

    output = bpy.data.collections["LooseTriangles Parts"]
    parts = list(output.objects)
    assert len(parts) == 2
    assert all(len(part.modifiers) == 0 for part in parts)
    assert all(len(part.data.vertices) == 6 for part in parts)
    assert all(len(part.data.polygons) == 5 for part in parts)
    assert set(bpy.context.selected_objects) == set(parts)
    assert bpy.context.active_object in parts


@pytest.mark.api_contract
def test_the_operator_keeps_its_public_idname(registered: None) -> None:
    assert (
        SILMOLD_OT_separate_loose_parts.bl_idname
        == "silicone_molding.separate_loose_parts"
    )
