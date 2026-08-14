"""Regenerate the golden meshes under ``tests/fixtures/``.

Run via ``just fixtures``. Only run this when a geometry change is
*intended* -- the whole point of the fixtures is that they do not move on
their own.
"""

from _helpers import FIXTURES_DIR, make_cube_mesh, mesh_data, write_obj

from silicone_molding.core import build_shell_mesh

CUBE_SIZE = 2.0
SHELL_THICKNESS = 0.2


def main() -> None:
    """Write every golden fixture, reporting each path as it is written."""
    FIXTURES_DIR.mkdir(exist_ok=True)

    cube = make_cube_mesh(CUBE_SIZE, "FixtureCube")
    shell = build_shell_mesh(cube, SHELL_THICKNESS, name="FixtureCubeShell")
    path = FIXTURES_DIR / "cube_shell.obj"
    write_obj(path, mesh_data(shell))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
