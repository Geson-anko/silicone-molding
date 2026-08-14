"""Tier-2 integration checks, run inside a real Blender.

Invoked by ``just blender-test`` as::

    blender --background --python tests/blender/run.py

This runs *after* ``extension install-file``, so it verifies the parts the
``bpy`` wheel cannot: that the built zip installs, that Blender resolves
the add-on under its extension module path, and that the operator behaves
identically there. It deliberately has **no third-party dependencies** --
not even pytest -- so that it needs nothing installed into Blender's own
Python on any of the three CI platforms.

Failures raise ``AssertionError``; the exit code is set explicitly at the
end because Blender swallows tracebacks from ``--python`` scripts.
"""

import sys
import traceback
from pathlib import Path

import addon_utils
import bpy

# Blender exposes user-repository extensions under this module path.
ADDON_MODULE = "bl_ext.user_default.silicone_molding"

REPO_ROOT = Path(__file__).parents[2]
GOLDEN = REPO_ROOT / "tests" / "fixtures" / "cube_shell.obj"

CUBE_SIZE = 2.0
THICKNESS = 0.2
TOLERANCE = 1e-5


def read_golden_vertices(path: Path) -> list[tuple[float, float, float]]:
    """Read vertex positions from the golden OBJ written by the tier-1
    tests."""
    vertices: list[tuple[float, float, float]] = []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            x, y, z = (float(part) for part in line.split()[1:4])
            vertices.append((x, y, z))
    return vertices


def check_addon_is_enabled() -> None:
    """The installed extension must be importable and enabled."""
    enabled = {module.__name__ for module in addon_utils.modules() if module}
    assert (
        ADDON_MODULE in sys.modules or ADDON_MODULE in enabled
    ), f"{ADDON_MODULE} was not enabled; installed add-ons: {sorted(enabled)}"
    assert hasattr(bpy.ops, "silicone_molding"), "operator namespace is missing"
    assert hasattr(bpy.ops.silicone_molding, "make_shell"), "make_shell is missing"


def check_scene_properties() -> None:
    """The scene must carry the add-on's settings after registration."""
    bpy.context.scene.silicone_molding.thickness = THICKNESS
    actual = bpy.context.scene.silicone_molding.thickness
    assert abs(actual - THICKNESS) < TOLERANCE, f"thickness round-trip gave {actual}"


def check_operator_matches_golden() -> None:
    """Running the operator on a real cube must reproduce the golden mesh."""
    bpy.ops.mesh.primitive_cube_add(size=CUBE_SIZE, location=(0.0, 0.0, 0.0))
    source = bpy.context.active_object
    assert source is not None, "primitive_cube_add did not leave an active object"

    bpy.context.scene.silicone_molding.thickness = THICKNESS
    result = bpy.ops.silicone_molding.make_shell()
    assert result == {"FINISHED"}, f"operator returned {result}"

    shell = bpy.data.objects.get(f"{source.name}_Shell")
    assert shell is not None, "operator did not create a shell object"

    expected = sorted(read_golden_vertices(GOLDEN))
    actual = sorted(tuple(round(c, 6) for c in v.co) for v in shell.data.vertices)
    assert len(actual) == len(
        expected
    ), f"vertex count {len(actual)} != golden {len(expected)}"
    for index, (got, want) in enumerate(zip(actual, expected)):
        for axis, (a, e) in enumerate(zip(got, want)):
            assert (
                abs(a - e) <= TOLERANCE
            ), f"vertex {index} axis {axis}: {a} != {e} (tol {TOLERANCE})"


CHECKS = (
    check_addon_is_enabled,
    check_scene_properties,
    check_operator_matches_golden,
)


def main() -> int:
    """Run every check, printing one line per result.

    Returns an exit code.
    """
    print(f"blender {bpy.app.version_string} -- tier-2 integration checks")
    failures = 0
    for check in CHECKS:
        try:
            check()
        except Exception:
            failures += 1
            print(f"FAIL {check.__name__}")
            traceback.print_exc()
        else:
            print(f"ok   {check.__name__}")
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
