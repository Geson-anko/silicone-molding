"""End-to-end path through registration, the scene properties and the operator.

This is the tier-1 counterpart of ``tests/blender/run.py``: it exercises
the same code against the ``bpy`` wheel, while the tier-2 script
exercises it after a real ``extension install-file``.
"""

from collections.abc import Iterator

import bpy
import pytest

import silicone_molding


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    silicone_molding.register()
    yield
    silicone_molding.unregister()


class TestRegistration:
    def test_scene_gains_the_settings_property_group(self, registered: None) -> None:
        assert bpy.context.scene.silicone_molding is not None
