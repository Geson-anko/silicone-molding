"""End-to-end path through registration, the scene properties and the
operators.

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

    def test_both_solidify_operators_become_callable(self, registered: None) -> None:
        # `dir` lists the operators Blender actually resolved; `hasattr` on
        # a `bpy.ops` namespace is always true, so it would prove nothing.
        operators = dir(bpy.ops.silicone_molding)
        assert "solidify" in operators
        assert "apply_solidify" in operators


class TestSolidifySettings:
    @pytest.mark.api_contract
    def test_scene_settings_carry_the_solidify_properties(
        self, registered: None
    ) -> None:
        # Contract pin, not a behaviour test: these names are written into
        # users' .blend files and read back from them (NFR-4).
        properties = bpy.context.scene.silicone_molding.bl_rna.properties
        assert "solidify_thickness_mm" in properties
        assert "solidify_flip" in properties

    def test_thickness_is_not_declared_as_a_length_property(
        self, registered: None
    ) -> None:
        # FR-2: unit="LENGTH" would re-display and re-interpret the value
        # in the scene's length unit, breaking "always entered in mm".
        properties = bpy.context.scene.silicone_molding.bl_rna.properties
        assert properties["solidify_thickness_mm"].unit == "NONE"
