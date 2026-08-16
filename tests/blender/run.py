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

# A 2 cm cube for the volume checks: 0.02 BU on a side with the default scene
# scale of 1 BU = 1 m, which is 8 mL.
MEASURED_CUBE_SIZE = 0.02
EXPECTED_VOLUME_ML = 8.0
# Mesh coordinates and the scene's FloatProperty are both float32, so the
# volume lands within about 1e-5 relative of the analytic value.
VOLUME_TOLERANCE = 1e-4

# A value in the shape the panel produces: two decimals, no unit, no commas.
DISPLAYED_VALUE = "8.00"

_HALF = MEASURED_CUBE_SIZE / 2.0
# A cube with its top face left off: the four edges around the hole are
# boundary edges, so this mesh has no defined volume.
OPEN_CUBE_VERTICES = [
    (-_HALF, -_HALF, -_HALF),
    (_HALF, -_HALF, -_HALF),
    (_HALF, _HALF, -_HALF),
    (-_HALF, _HALF, -_HALF),
    (-_HALF, -_HALF, _HALF),
    (_HALF, -_HALF, _HALF),
    (_HALF, _HALF, _HALF),
    (-_HALF, _HALF, _HALF),
]
OPEN_CUBE_FACES = [
    (0, 1, 2, 3),
    (0, 4, 5, 1),
    (1, 5, 6, 2),
    (2, 6, 7, 3),
    (3, 7, 4, 0),
]


def check_addon_is_enabled() -> None:
    """The installed extension must be importable and enabled."""
    enabled = {module.__name__ for module in addon_utils.modules() if module}
    assert (
        ADDON_MODULE in sys.modules or ADDON_MODULE in enabled
    ), f"{ADDON_MODULE} was not enabled; installed add-ons: {sorted(enabled)}"
    # `dir` lists the operators Blender actually resolved; `hasattr` on a
    # `bpy.ops` namespace is always true, so it would prove nothing.
    operators = dir(bpy.ops.silicone_molding)
    for name in ("solidify", "apply_solidify", "measure_volume", "copy_value"):
        assert (
            name in operators
        ), f"operator {name} is missing; silicone_molding has {sorted(operators)}"


def check_scene_properties() -> None:
    """The scene must carry the add-on's settings after registration."""
    settings = bpy.context.scene.silicone_molding
    assert settings is not None, "scene settings are missing"
    names = set(settings.bl_rna.properties.keys())
    for name in (
        "solidify_thickness_mm",
        "solidify_flip",
        "volume_ml",
        "volume_measured",
    ):
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


def _deselect_everything() -> None:
    """Clear the selection, which the startup file leaves on its cube."""
    for existing in bpy.context.scene.objects:
        existing.select_set(False)


def check_measuring_a_closed_cube_stores_its_millilitres() -> None:
    """Measuring a 2 cm cube must store the 8 ml that tier 1 asserts.

    This is the value the sidebar shows as "8.00", produced by a real
    Blender's own depsgraph and mesh evaluation rather than by the
    wheel.
    """
    _deselect_everything()
    bpy.ops.mesh.primitive_cube_add(size=MEASURED_CUBE_SIZE, location=(0.0, 0.0, 0.0))
    cube = bpy.context.active_object
    assert cube is not None, "primitive_cube_add did not leave an active object"
    cube.select_set(True)
    bpy.context.scene.unit_settings.scale_length = 1.0

    result = bpy.ops.silicone_molding.measure_volume()
    assert result == {"FINISHED"}, f"measure_volume returned {result}"

    settings = bpy.context.scene.silicone_molding
    assert settings.volume_measured, "volume_measured stayed false after a good run"
    difference = abs(settings.volume_ml - EXPECTED_VOLUME_ML)
    assert difference <= VOLUME_TOLERANCE, (
        f"volume_ml is {settings.volume_ml}, expected {EXPECTED_VOLUME_ML} "
        f"(tol {VOLUME_TOLERANCE})"
    )


def check_an_open_mesh_clears_the_stored_measurement() -> None:
    """A selection whose volume is undefined must cancel and store nothing.

    The operator reports an ERROR, which Blender turns into a RuntimeError at
    the ``bpy.ops`` boundary, so the spec's ``{"CANCELLED"}`` surfaces here as
    that exception. ``volume_measured`` is seeded true first: a ``poll``
    failure never reaches ``execute``, so without the seed it could pass this
    check by accident.
    """
    _deselect_everything()
    mesh = bpy.data.meshes.new("OpenCube")
    mesh.from_pydata(OPEN_CUBE_VERTICES, [], OPEN_CUBE_FACES)
    mesh.update()
    open_cube = bpy.data.objects.new("OpenCube", mesh)
    bpy.context.scene.collection.objects.link(open_cube)
    open_cube.select_set(True)

    settings = bpy.context.scene.silicone_molding
    settings.volume_measured = True

    try:
        result = bpy.ops.silicone_molding.measure_volume()
    except RuntimeError as exc:
        cancelled, outcome = True, f"raised {exc}"
    else:
        cancelled, outcome = result == {"CANCELLED"}, f"returned {result}"

    assert cancelled, f"measure_volume {outcome} for a mesh with a hole"
    assert not settings.volume_measured, "the stale result was not cleared"


def check_copying_a_value_finishes() -> None:
    """The clipboard operator must run inside a real Blender too.

    Only the return value is checked. A background Blender's clipboard
    accepts the write but reads back empty, so what actually got copied
    cannot be verified from a script here either -- that is the manual
    check.
    """
    result = bpy.ops.silicone_molding.copy_value(value=DISPLAYED_VALUE)
    assert result == {"FINISHED"}, f"copy_value returned {result}"


CHECKS = (
    check_addon_is_enabled,
    check_scene_properties,
    check_solidify_then_apply_gives_a_double_walled_cube,
    check_measuring_a_closed_cube_stores_its_millilitres,
    check_an_open_mesh_clears_the_stored_measurement,
    check_copying_a_value_finishes,
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
