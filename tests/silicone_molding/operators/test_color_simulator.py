"""Named color profiles, live material previews, and material assignment."""

from collections.abc import Iterator

import bpy
import pytest

import silicone_molding
from silicone_molding.operators.color_simulator import (
    _MATERIAL_PREFIX,
    _SHADER_NODE_NAME,
)


@pytest.fixture(scope="module")
def registered() -> Iterator[None]:
    silicone_molding.register()
    yield
    silicone_molding.unregister()


@pytest.fixture
def settings(registered: None) -> Iterator[bpy.types.PropertyGroup]:
    props = bpy.context.scene.silicone_molding
    props.color_profiles.clear()
    props.color_profile_active_index = -1
    props.mixture_parts.clear()
    yield props
    props.color_profiles.clear()
    props.color_profile_active_index = -1
    props.mixture_parts.clear()
    for material in tuple(bpy.data.materials):
        if material.name.startswith(_MATERIAL_PREFIX) and material.users == 0:
            bpy.data.materials.remove(material)


def _add_profile(settings: bpy.types.PropertyGroup) -> bpy.types.PropertyGroup:
    result = bpy.ops.silicone_molding.add_color_profile()
    assert result == {"FINISHED"}
    return settings.color_profiles[settings.color_profile_active_index]


class TestNamedProfiles:
    def test_profiles_have_independent_names_inputs_and_materials(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        warm = _add_profile(settings)
        warm.profile_name = "Warm Clear"
        warm.base_color = (1.0, 0.8, 0.5)

        cool = _add_profile(settings)
        cool.profile_name = "Cool Cloudy"
        cool.base_color = (0.5, 0.7, 1.0)
        cool.cloudiness = 0.75

        assert [profile.profile_name for profile in settings.color_profiles] == [
            "Warm Clear",
            "Cool Cloudy",
        ]
        assert warm.preview_material != cool.preview_material
        assert tuple(warm.preview_material.diffuse_color[:3]) == pytest.approx(
            (1.0, 0.8, 0.5)
        )
        assert tuple(cool.preview_material.diffuse_color[:3]) == pytest.approx(
            (0.5, 0.7, 1.0)
        )

    def test_removing_a_profile_keeps_its_applied_material_datablock(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        profile = _add_profile(settings)
        material = profile.preview_material

        result = bpy.ops.silicone_molding.remove_color_profile()

        assert result == {"FINISHED"}
        assert len(settings.color_profiles) == 0
        assert material.name in bpy.data.materials


class TestColorants:
    def test_add_creates_a_zero_dose_float_colorant(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        profile = _add_profile(settings)

        result = bpy.ops.silicone_molding.add_colorant()

        assert result == {"FINISHED"}
        colorant = profile.colorants[0]
        assert colorant.enabled
        assert not colorant.is_opacifier
        assert colorant.colorant_name == "Colorant"
        assert colorant.calibration_drops_per_ml == pytest.approx(1.0)
        assert colorant.drops == pytest.approx(0.0)
        drops = colorant.bl_rna.properties["drops"]
        assert drops.type == "FLOAT"
        assert drops.step == 100

    def test_changing_drops_updates_only_the_owning_profile_material(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        first = _add_profile(settings)
        first.base_volume_ml = 1.0
        bpy.ops.silicone_molding.add_colorant()
        first_colorant = first.colorants[0]
        first_colorant.calibration_color = (0.25, 0.5, 0.75)

        second = _add_profile(settings)
        second_before = tuple(second.preview_material.diffuse_color[:3])

        first_colorant.drops = 1.0

        assert tuple(first.preview_material.diffuse_color[:3]) == pytest.approx(
            (0.25, 0.5, 0.75)
        )
        assert tuple(second.preview_material.diffuse_color[:3]) == pytest.approx(
            second_before
        )

    def test_all_dyes_reduce_transmission_and_white_also_lightens_the_color(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        profile = _add_profile(settings)
        profile.base_volume_ml = 1.0
        profile.transparency = 0.8
        profile.cloudiness = 0.2
        bpy.ops.silicone_molding.add_colorant()
        blue = profile.colorants[0]
        blue.calibration_color = (0.2, 0.4, 0.8)
        blue.drops = 1.0

        shader = profile.preview_material.node_tree.nodes[_SHADER_NODE_NAME]

        assert tuple(profile.result_color) == pytest.approx((0.2, 0.4, 0.8))
        assert shader.inputs["Transmission Weight"].default_value == pytest.approx(0.0)

        bpy.ops.silicone_molding.add_colorant()
        white = profile.colorants[1]
        white.is_opacifier = True
        white.drops = 0.5

        shader = profile.preview_material.node_tree.nodes[_SHADER_NODE_NAME]

        assert shader.inputs["Transmission Weight"].default_value == pytest.approx(0.0)
        assert shader.inputs["Subsurface Weight"].default_value == pytest.approx(0.6)
        assert tuple(profile.result_color) == pytest.approx((0.6, 0.7, 0.9))


class TestMixtureVolumeCopy:
    def test_only_enabled_mixture_rows_are_copied(
        self, settings: bpy.types.PropertyGroup
    ) -> None:
        profile = _add_profile(settings)
        included = settings.mixture_parts.add()
        included.volume_ml = 40.0
        excluded = settings.mixture_parts.add()
        excluded.volume_ml = 60.0
        excluded.enabled = False

        result = bpy.ops.silicone_molding.copy_mixture_volume_to_coloring()

        assert result == {"FINISHED"}
        assert profile.base_volume_ml == pytest.approx(40.0)


class TestMaterialApplication:
    def test_active_material_slots_are_replaced_on_all_selected_meshes(
        self,
        settings: bpy.types.PropertyGroup,
        cube_object: bpy.types.Object,
        make_object,
    ) -> None:
        profile = _add_profile(settings)
        other_mesh = bpy.data.meshes.new("OtherColorMesh")
        other = make_object(other_mesh, "OtherColorObject")
        previous = bpy.data.materials.new("PreviousMaterial")
        other_mesh.materials.append(previous)
        for obj in bpy.context.selected_objects or ():
            obj.select_set(False)
        cube_object.select_set(True)
        other.select_set(True)
        bpy.context.view_layer.objects.active = cube_object

        result = bpy.ops.silicone_molding.apply_color_material()

        assert result == {"FINISHED"}
        assert cube_object.active_material == profile.preview_material
        assert other.active_material == profile.preview_material
        bpy.data.materials.remove(previous)
