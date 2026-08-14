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

    def test_both_measurement_operators_become_callable(self, registered: None) -> None:
        # AC-49 / AC-51 (volume_measurement spec). `dir` for the same reason
        # as above.
        operators = dir(bpy.ops.silicone_molding)
        assert "measure_volume" in operators
        assert "copy_value" in operators

    def test_the_sidebar_registers_as_a_parent_with_two_sub_panels(
        self, registered: None
    ) -> None:
        # AC-56 / FR-8: Blender resolves `bl_parent_id` while registering, so
        # a sub-panel registered before SILMOLD_PT_main raises RuntimeError
        # and takes the whole add-on down with it. The module fixture is what
        # actually detects that regression; this test names the guarantee and
        # confirms Blender resolved both children.
        types = dir(bpy.types)
        assert "SILMOLD_PT_main" in types
        assert "SILMOLD_PT_measurement" in types
        assert "SILMOLD_PT_processing" in types


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


class TestMeasurementSettings:
    """Where a measurement is stored (volume_measurement spec §5.7)."""

    @pytest.mark.api_contract
    def test_scene_settings_carry_the_measurement_properties(
        self, registered: None
    ) -> None:
        # Contract pin, not a behaviour test: AC-57 / NFR-4. These two names
        # are written into users' .blend files and read back from them, and
        # the panel addresses them by name.
        properties = bpy.context.scene.silicone_molding.bl_rna.properties
        assert "volume_cm3" in properties
        assert "volume_measured" in properties

    def test_the_volume_is_not_declared_as_a_volume_property(
        self, registered: None
    ) -> None:
        # AC-58 / FR-29: unit="VOLUME" would re-display the value in the
        # scene's unit settings, breaking "always shown in cm3" (FR-38). Same
        # reasoning as the millimetre thickness above.
        properties = bpy.context.scene.silicone_molding.bl_rna.properties
        assert properties["volume_cm3"].unit == "NONE"
