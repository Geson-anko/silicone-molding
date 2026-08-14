"""Behaviour of the offset-shell builder.

The expected numbers are derived analytically from a 2x2x2 cube so that
the test states what the geometry *should* be; the golden fixture on top
of that pins the exact vertex layout against silent regressions.
"""

import bpy
import pytest
from _helpers import assert_matches_golden, mesh_invariants

from silicone_molding.core import MIN_THICKNESS, build_shell_mesh

#: Wall thickness used by the golden fixture (see tests/generate_fixtures.py).
THICKNESS = 0.2

#: A 2x2x2 cube grown outward by 0.2 becomes 2.4x2.4x2.4 with a 2x2x2 void.
EXPECTED_VOLUME = 2.4**3 - 2.0**3


class TestBuildShellMesh:
    def test_shell_grows_outward_leaving_the_source_surface_as_inner_wall(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        shell = build_shell_mesh(cube_mesh, THICKNESS, name="Shell")

        invariants = mesh_invariants(shell)
        assert invariants.bbox_min == pytest.approx((-1.2, -1.2, -1.2), abs=1e-5)
        assert invariants.bbox_max == pytest.approx((1.2, 1.2, 1.2), abs=1e-5)
        assert invariants.volume == pytest.approx(EXPECTED_VOLUME, abs=1e-4)

    def test_shell_of_a_closed_source_is_two_watertight_walls(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        shell = build_shell_mesh(cube_mesh, THICKNESS, name="Shell")

        invariants = mesh_invariants(shell)
        assert invariants.is_watertight
        # A closed source has no rim to bridge the two walls across, so the
        # result is a hollow solid: an outer wall plus the cavity wall that
        # the master will occupy. Both are needed for a printable mold.
        assert invariants.loose_part_count == 2

    def test_shell_doubles_the_source_vertex_and_face_counts(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        shell = build_shell_mesh(cube_mesh, THICKNESS, name="Shell")

        invariants = mesh_invariants(shell)
        assert invariants.vertex_count == len(cube_mesh.vertices) * 2
        assert invariants.face_count == len(cube_mesh.polygons) * 2

    def test_source_mesh_is_left_untouched(self, cube_mesh: bpy.types.Mesh) -> None:
        before = mesh_invariants(cube_mesh)

        build_shell_mesh(cube_mesh, THICKNESS, name="Shell")

        assert mesh_invariants(cube_mesh) == before

    def test_returned_mesh_carries_the_requested_name(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        shell = build_shell_mesh(cube_mesh, THICKNESS, name="MyShell")

        assert shell.name == "MyShell"
        assert shell.name in bpy.data.meshes

    @pytest.mark.golden
    def test_cube_shell_matches_the_golden_mesh(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        shell = build_shell_mesh(cube_mesh, THICKNESS, name="Shell")

        assert_matches_golden(shell, "cube_shell.obj")


class TestBuildShellMeshRejectsBadInput:
    def test_face_less_mesh_is_rejected(self, empty_mesh: bpy.types.Mesh) -> None:
        with pytest.raises(ValueError, match="no faces"):
            build_shell_mesh(empty_mesh, THICKNESS, name="Shell")

    def test_thickness_below_the_minimum_is_rejected(
        self, cube_mesh: bpy.types.Mesh
    ) -> None:
        with pytest.raises(ValueError, match="thickness"):
            build_shell_mesh(cube_mesh, MIN_THICKNESS / 2, name="Shell")

    def test_negative_thickness_is_rejected(self, cube_mesh: bpy.types.Mesh) -> None:
        with pytest.raises(ValueError, match="thickness"):
            build_shell_mesh(cube_mesh, -THICKNESS, name="Shell")
