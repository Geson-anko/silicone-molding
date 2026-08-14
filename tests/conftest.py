"""Shared fixtures.

Tests run against the real ``bpy`` wheel from PyPI, so ``bmesh`` and the
data API behave exactly as they do inside Blender. Nothing here mocks
``bpy``. Mesh construction goes through :mod:`tests._helpers`, which owns
the ``bmesh`` import (see the note at the top of that module).
"""

from collections.abc import Iterator

import bpy
import pytest
from _helpers import make_cube_mesh

#: Edge length of the cube used across the geometry tests.
CUBE_SIZE = 2.0


@pytest.fixture
def cube_mesh() -> Iterator[bpy.types.Mesh]:
    """A closed 2x2x2 cube mesh datablock, spanning -1..1 on every axis."""
    mesh = make_cube_mesh(CUBE_SIZE, "TestCube")
    yield mesh
    bpy.data.meshes.remove(mesh)


@pytest.fixture
def empty_mesh() -> Iterator[bpy.types.Mesh]:
    """A mesh datablock with no geometry at all."""
    mesh = bpy.data.meshes.new("TestEmpty")
    yield mesh
    bpy.data.meshes.remove(mesh)
