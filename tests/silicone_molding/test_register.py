"""End-to-end path through registration, the scene properties and the operator.

This is the tier-1 counterpart of ``tests/blender/run.py``: it exercises
the same code against the ``bpy`` wheel, while the tier-2 script
exercises it after a real ``extension install-file``.
"""

from collections.abc import Iterator

import bpy
import pytest
from _helpers import make_cube_mesh, mesh_invariants

import silicone_molding
from silicone_molding.operators import SILMOLD_OT_make_shell

CUBE_SIZE = 2.0
THICKNESS = 0.2


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    silicone_molding.register()
    yield
    silicone_molding.unregister()


@pytest.fixture
def active_cube(registered: None) -> Iterator[bpy.types.Object]:
    """A cube object linked into the scene and made active."""
    mesh = make_cube_mesh(CUBE_SIZE, "OpCube")
    obj = bpy.data.objects.new("OpCube", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    yield obj

    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)


class TestRegistration:
    def test_scene_gains_the_settings_property_group(self, registered: None) -> None:
        bpy.context.scene.silicone_molding.thickness = THICKNESS

        assert bpy.context.scene.silicone_molding.thickness == pytest.approx(THICKNESS)

    def test_operator_is_reachable_through_bpy_ops(self, registered: None) -> None:
        assert hasattr(bpy.ops.silicone_molding, "make_shell")


class TestMakeShellOperator:
    def test_creates_a_shell_object_next_to_the_active_mesh(
        self, active_cube: bpy.types.Object
    ) -> None:
        bpy.context.scene.silicone_molding.thickness = THICKNESS

        result = bpy.ops.silicone_molding.make_shell()

        assert result == {"FINISHED"}
        shell = bpy.data.objects["OpCube_Shell"]
        invariants = mesh_invariants(shell.data)
        assert invariants.is_watertight
        assert invariants.bbox_max == pytest.approx((1.2, 1.2, 1.2), abs=1e-5)

        bpy.data.meshes.remove(shell.data)

    def test_is_unavailable_without_an_active_mesh(self, registered: None) -> None:
        bpy.context.view_layer.objects.active = None

        assert not SILMOLD_OT_make_shell.poll(bpy.context)
