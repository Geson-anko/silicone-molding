"""Behaviour of the integrated Geometry Nodes Surface Cut modifier."""

from collections.abc import Iterator

import bpy
import pytest
from _helpers import make_cube_mesh, mesh_invariants

from silicone_molding.core import (
    SURFACE_CUT_MODIFIER_NAME,
    create_surface_cut,
)

THICKNESS = 1e-6
SURFACE_VERTICES = [
    (-2.0, -2.0, 0.0),
    (2.0, -2.0, 0.0),
    (2.0, 2.0, 0.0),
    (-2.0, 2.0, 0.0),
]
SURFACE_FACES = [(0, 1, 2, 3)]


@pytest.fixture
def surface_cut_objects(
    make_object,
) -> Iterator[tuple[bpy.types.Object, bpy.types.Object]]:
    existing_node_groups = set(bpy.data.node_groups.keys())
    target = make_object(make_cube_mesh(2.0, "TargetMesh"), "Target")
    surface_mesh = bpy.data.meshes.new("SurfaceMesh")
    surface_mesh.from_pydata(SURFACE_VERTICES, [], SURFACE_FACES)
    surface_mesh.update()
    surface = make_object(surface_mesh, "Surface")
    yield target, surface
    for node_group in tuple(bpy.data.node_groups):
        if node_group.name not in existing_node_groups:
            bpy.data.node_groups.remove(node_group)


def test_one_modifier_performs_the_solidify_and_manifold_difference(
    surface_cut_objects: tuple[bpy.types.Object, bpy.types.Object],
) -> None:
    target, surface = surface_cut_objects

    modifier = create_surface_cut(target, surface, THICKNESS)

    assert modifier.name == SURFACE_CUT_MODIFIER_NAME
    assert modifier.type == "NODES"
    assert len(target.modifiers) == 1
    assert len(surface.modifiers) == 0

    evaluated = target.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = bpy.data.meshes.new_from_object(evaluated)
    try:
        invariants = mesh_invariants(result)
    finally:
        bpy.data.meshes.remove(result)

    assert invariants.vertex_count == 16
    assert invariants.face_count == 12
    assert invariants.loose_part_count == 2
    assert invariants.is_watertight
    assert invariants.volume == pytest.approx(8.0 - 4.0 * THICKNESS, abs=1e-6)
    assert invariants.bbox_min == pytest.approx((-1.0, -1.0, -1.0))
    assert invariants.bbox_max == pytest.approx((1.0, 1.0, 1.0))
