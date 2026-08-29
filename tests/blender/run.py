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

import struct
import sys
import tempfile
import traceback
from pathlib import Path

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

# STL export checks use a 2x2 plane, a one-unit Solidify modifier, and the
# operator's fixed 1000x scale. The exported bounds must therefore span 2000
# on X/Y and 1000 on Z.
STL_PLANE_HALF_SIZE = 1.0
STL_SOLIDIFY_THICKNESS = 1.0
STL_EXPORT_SCALE = 1000.0
STL_FAR_OBJECT_X = 10.0
STL_TOLERANCE = 1e-4

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
    for name in (
        "solidify",
        "apply_solidify",
        "measure_volume",
        "copy_value",
        "export_stl",
        "inherit_shape",
        "add_mixture_part",
        "remove_mixture_parts",
        "move_mixture_parts",
        "select_mixture_part",
    ):
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
        "solidify_even_thickness",
        "volume_ml",
        "volume_measured",
        "mixture_use_shared_density",
        "mixture_density_a_g_per_ml",
        "mixture_density_b_g_per_ml",
        "mixture_ratio_a",
        "mixture_ratio_b",
        "mixture_parts",
        "mixture_selection_anchor",
        "mixture_active_index",
    ):
        assert name in names, f"{name} is missing; scene settings have {sorted(names)}"


def check_mixture_part_operations() -> None:
    """The installed add-on must add, select, move, and remove rows."""
    settings = bpy.context.scene.silicone_molding
    settings.mixture_parts.clear()
    for name in ("A", "B", "C", "D"):
        result = bpy.ops.silicone_molding.add_mixture_part()
        assert result == {"FINISHED"}, f"add_mixture_part returned {result}"
        settings.mixture_parts[-1].part_name = name

    bpy.ops.silicone_molding.select_mixture_part(index=1, mode="REPLACE")
    bpy.ops.silicone_molding.select_mixture_part(index=3, mode="TOGGLE")
    result = bpy.ops.silicone_molding.move_mixture_parts(direction="UP")
    assert result == {"FINISHED"}, f"move_mixture_parts returned {result}"
    assert [part.part_name for part in settings.mixture_parts] == [
        "B",
        "A",
        "D",
        "C",
    ]

    result = bpy.ops.silicone_molding.remove_mixture_parts()
    assert result == {"FINISHED"}, f"remove_mixture_parts returned {result}"
    assert [part.part_name for part in settings.mixture_parts] == ["A", "C"]
    assert settings.mixture_selection_anchor == -1


def check_mixture_settings_survive_save_and_reload() -> None:
    """Every saved mixture input must round-trip through a .blend file."""
    settings = bpy.context.scene.silicone_molding
    settings.mixture_parts.clear()
    settings.mixture_use_shared_density = False
    settings.mixture_density_a_g_per_ml = 1.5
    settings.mixture_density_b_g_per_ml = 1.0
    settings.mixture_ratio_a = 3.0
    settings.mixture_ratio_b = 1.0

    body = settings.mixture_parts.add()
    body.enabled = True
    body.selected = False
    body.part_name = "Body"
    body.volume_ml = 60.0

    lid = settings.mixture_parts.add()
    lid.enabled = False
    lid.selected = True
    lid.part_name = "Lid"
    lid.volume_ml = 30.0
    settings.mixture_selection_anchor = 1
    settings.mixture_active_index = 1

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "mixture-round-trip.blend"
        result = bpy.ops.wm.save_as_mainfile(filepath=str(path))
        assert result == {"FINISHED"}, f"save_as_mainfile returned {result}"
        result = bpy.ops.wm.open_mainfile(filepath=str(path))
        assert result == {"FINISHED"}, f"open_mainfile returned {result}"

        loaded = bpy.context.scene.silicone_molding
        assert not loaded.mixture_use_shared_density
        assert abs(loaded.mixture_density_a_g_per_ml - 1.5) <= TOLERANCE
        assert abs(loaded.mixture_density_b_g_per_ml - 1.0) <= TOLERANCE
        assert abs(loaded.mixture_ratio_a - 3.0) <= TOLERANCE
        assert abs(loaded.mixture_ratio_b - 1.0) <= TOLERANCE
        assert [part.part_name for part in loaded.mixture_parts] == ["Body", "Lid"]
        assert [part.enabled for part in loaded.mixture_parts] == [True, False]
        assert [part.selected for part in loaded.mixture_parts] == [False, True]
        assert [part.volume_ml for part in loaded.mixture_parts] == [60.0, 30.0]
        assert loaded.mixture_selection_anchor == -1
        assert loaded.mixture_active_index == -1


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
    settings.solidify_even_thickness = True

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


def _binary_stl_vertices(path: Path) -> list[tuple[float, float, float]]:
    """Read triangle vertices from Blender's default binary STL output."""
    payload = path.read_bytes()
    triangle_count = struct.unpack_from("<I", payload, 80)[0]
    assert len(payload) == 84 + triangle_count * 50, "malformed binary STL"

    vertices: list[tuple[float, float, float]] = []
    for index in range(triangle_count):
        coordinates = struct.unpack_from("<9f", payload, 84 + index * 50 + 12)
        vertices.extend(
            [
                (coordinates[0], coordinates[1], coordinates[2]),
                (coordinates[3], coordinates[4], coordinates[5]),
                (coordinates[6], coordinates[7], coordinates[8]),
            ]
        )
    return vertices


def check_export_stl_uses_the_fixed_settings() -> None:
    """The installed operator must export selection, modifiers, and 1000x."""
    _deselect_everything()
    vertices = [
        (-STL_PLANE_HALF_SIZE, -STL_PLANE_HALF_SIZE, 0.0),
        (STL_PLANE_HALF_SIZE, -STL_PLANE_HALF_SIZE, 0.0),
        (STL_PLANE_HALF_SIZE, STL_PLANE_HALF_SIZE, 0.0),
        (-STL_PLANE_HALF_SIZE, STL_PLANE_HALF_SIZE, 0.0),
    ]
    faces = [(0, 1, 2, 3)]

    selected_mesh = bpy.data.meshes.new("ExportSelectedMesh")
    selected_mesh.from_pydata(vertices, [], faces)
    selected_mesh.update()
    selected = bpy.data.objects.new("ExportSelected", selected_mesh)
    bpy.context.scene.collection.objects.link(selected)
    selected.select_set(True)
    bpy.context.view_layer.objects.active = selected
    modifier = selected.modifiers.new("Export Solidify", "SOLIDIFY")
    modifier.thickness = STL_SOLIDIFY_THICKNESS
    modifier.offset = 1.0

    unselected_mesh = bpy.data.meshes.new("ExportUnselectedMesh")
    unselected_mesh.from_pydata(vertices, [], faces)
    unselected_mesh.update()
    unselected = bpy.data.objects.new("ExportUnselected", unselected_mesh)
    bpy.context.scene.collection.objects.link(unselected)
    unselected.location.x = STL_FAR_OBJECT_X
    unselected.select_set(False)

    with tempfile.TemporaryDirectory() as directory:
        requested_path = Path(directory) / "ExportSelected"
        result = bpy.ops.silicone_molding.export_stl(filepath=str(requested_path))
        output_path = requested_path.with_suffix(".stl")
        assert result == {"FINISHED"}, f"export_stl returned {result}"
        assert output_path.is_file(), f"STL was not written to {output_path}"

        exported = _binary_stl_vertices(output_path)

    x_coordinates = [vertex[0] for vertex in exported]
    y_coordinates = [vertex[1] for vertex in exported]
    z_coordinates = [vertex[2] for vertex in exported]
    expected_min = -STL_EXPORT_SCALE
    expected_max = STL_EXPORT_SCALE
    assert abs(min(x_coordinates) - expected_min) <= STL_TOLERANCE
    assert abs(max(x_coordinates) - expected_max) <= STL_TOLERANCE
    assert abs(min(y_coordinates) - expected_min) <= STL_TOLERANCE
    assert abs(max(y_coordinates) - expected_max) <= STL_TOLERANCE
    z_extent = max(z_coordinates) - min(z_coordinates)
    assert abs(z_extent - STL_EXPORT_SCALE) <= STL_TOLERANCE
    assert modifier.name in selected.modifiers, "export applied the source modifier"


CHECKS = (
    check_addon_is_enabled,
    check_scene_properties,
    check_mixture_part_operations,
    check_solidify_then_apply_gives_a_double_walled_cube,
    check_measuring_a_closed_cube_stores_its_millilitres,
    check_an_open_mesh_clears_the_stored_measurement,
    check_copying_a_value_finishes,
    check_export_stl_uses_the_fixed_settings,
    # This opens a saved .blend, so it must stay last.
    check_mixture_settings_survive_save_and_reload,
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
