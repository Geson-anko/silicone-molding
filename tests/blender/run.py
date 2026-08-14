"""Tier-2 integration checks, run inside a real Blender.

Invoked by ``just blender-test`` as::

    blender --background --python tests/blender/run.py

This runs *after* ``extension install-file``, so it verifies the parts the
``bpy`` wheel cannot: that the built zip installs, that Blender resolves
the add-on under its extension module path, and that the operators behave
identically there. It deliberately has **no third-party dependencies** --
not even pytest -- so that it needs nothing installed into Blender's own
Python on any of the three CI platforms. It also imports nothing from
``tests/``, which is not on Blender's path.

Failures raise ``AssertionError``; the exit code is set explicitly at the
end because Blender swallows tracebacks from ``--python`` scripts.
"""

import sys
import traceback

import addon_utils
import bpy

# Blender exposes user-repository extensions under this module path.
ADDON_MODULE = "bl_ext.user_default.silicone_molding"

# Mirrors silicone_molding.core.MODIFIER_NAME, which tier 1 pins as public
# API. Spelled out here because the add-on is imported by Blender, not by
# this script.
MODIFIER_NAME = "Silicone Molding Solidify"

CUBE_SIZE = 2.0
THICKNESS_MM = 3.0

# THICKNESS_MM in Blender units, with the default scene scale of 1 unit = 1 m.
THICKNESS = 0.003

# A 2x2x2 cube solidified outwards: the original 8 vertices plus 8 on the
# outer shell, still 12 quads. Half the extent grows by the wall thickness.
EXPECTED_VERTEX_COUNT = 16
EXPECTED_FACE_COUNT = 12
EXPECTED_EXTENT = CUBE_SIZE / 2 + THICKNESS
TOLERANCE = 1e-5


def check_addon_is_enabled() -> None:
    """The installed extension must be importable and enabled."""
    enabled = {module.__name__ for module in addon_utils.modules() if module}
    assert (
        ADDON_MODULE in sys.modules or ADDON_MODULE in enabled
    ), f"{ADDON_MODULE} was not enabled; installed add-ons: {sorted(enabled)}"
    # `dir` lists the operators Blender actually resolved; `hasattr` on a
    # `bpy.ops` namespace is always true, so it would prove nothing.
    operators = dir(bpy.ops.silicone_molding)
    for name in ("solidify", "apply_solidify"):
        assert (
            name in operators
        ), f"operator {name} is missing; silicone_molding has {sorted(operators)}"


def check_scene_properties() -> None:
    """The scene must carry the add-on's settings after registration."""
    settings = bpy.context.scene.silicone_molding
    assert settings is not None, "scene settings are missing"
    names = set(settings.bl_rna.properties.keys())
    for name in ("solidify_thickness_mm", "solidify_flip"):
        assert name in names, f"{name} is missing; scene settings have {sorted(names)}"


def check_solidify_then_apply_gives_a_double_walled_cube() -> None:
    """Both operators must produce the geometry tier 1 asserts.

    A 2x2x2 cube walled 3 mm outwards becomes two shells: 16 vertices, 12
    faces, reaching 1.003 on every axis. The extent depends on Even
    Thickness being on -- without it the corners would only reach
    1 + 0.003/sqrt(3).
    """
    for existing in bpy.context.scene.objects:
        existing.select_set(False)

    bpy.ops.mesh.primitive_cube_add(size=CUBE_SIZE, location=(0.0, 0.0, 0.0))
    cube = bpy.context.active_object
    assert cube is not None, "primitive_cube_add did not leave an active object"
    cube.select_set(True)

    bpy.context.scene.unit_settings.scale_length = 1.0
    settings = bpy.context.scene.silicone_molding
    settings.solidify_thickness_mm = THICKNESS_MM
    settings.solidify_flip = False

    result = bpy.ops.silicone_molding.solidify()
    assert result == {"FINISHED"}, f"solidify returned {result}"
    stack = [modifier.name for modifier in cube.modifiers]
    assert MODIFIER_NAME in stack, f"{MODIFIER_NAME!r} not added; stack is {stack}"

    result = bpy.ops.silicone_molding.apply_solidify()
    assert result == {"FINISHED"}, f"apply_solidify returned {result}"
    stack = [modifier.name for modifier in cube.modifiers]
    assert MODIFIER_NAME not in stack, f"{MODIFIER_NAME!r} survived apply; got {stack}"

    mesh = cube.data
    assert (
        len(mesh.vertices) == EXPECTED_VERTEX_COUNT
    ), f"{len(mesh.vertices)} vertices, expected {EXPECTED_VERTEX_COUNT}"
    assert (
        len(mesh.polygons) == EXPECTED_FACE_COUNT
    ), f"{len(mesh.polygons)} faces, expected {EXPECTED_FACE_COUNT}"

    for axis, label in enumerate("xyz"):
        coordinates = [vertex.co[axis] for vertex in mesh.vertices]
        low, high = min(coordinates), max(coordinates)
        assert (
            abs(low + EXPECTED_EXTENT) <= TOLERANCE
        ), f"{label} min is {low}, expected {-EXPECTED_EXTENT} (tol {TOLERANCE})"
        assert (
            abs(high - EXPECTED_EXTENT) <= TOLERANCE
        ), f"{label} max is {high}, expected {EXPECTED_EXTENT} (tol {TOLERANCE})"


CHECKS = (
    check_addon_is_enabled,
    check_scene_properties,
    check_solidify_then_apply_gives_a_double_walled_cube,
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
