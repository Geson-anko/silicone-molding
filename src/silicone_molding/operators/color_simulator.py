"""Manage named silicone color profiles and their preview materials."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol, cast, override

import bpy

from ..core import (
    RGB,
    CalibratedColorant,
    SimulatedSiliconeAppearance,
    simulate_silicone_appearance,
)
from .solidify import OperatorReturn

_MATERIAL_PREFIX = "Silicone Mix - "
_SHADER_NODE_NAME = "Silicone Molding Shader"


class ColorantValues(Protocol):
    """RNA values needed to calculate one colorant contribution."""

    enabled: bool
    is_opacifier: bool
    colorant_name: str
    calibration_color: Sequence[float]
    calibration_drops_per_ml: float
    drops: float


class ColorantCollection(Protocol):
    """Mutable RNA collection containing colorant rows."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> ColorantValues: ...

    def __iter__(self) -> Iterator[ColorantValues]: ...

    def add(self) -> ColorantValues: ...

    def remove(self, index: int) -> None: ...


class ColorProfileValues(Protocol):
    """RNA values shared by the simulator UI and material updater."""

    profile_name: str
    base_volume_ml: float
    base_color: Sequence[float]
    transparency: float
    cloudiness: float
    colorants: ColorantCollection
    colorant_active_index: int
    preview_material: bpy.types.Material | None


class ColorProfileCollection(Protocol):
    """Mutable RNA collection containing named profiles."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> ColorProfileValues: ...

    def __iter__(self) -> Iterator[ColorProfileValues]: ...

    def add(self) -> ColorProfileValues: ...

    def remove(self, index: int) -> None: ...


class ColorSimulatorSettings(Protocol):
    """Scene-level container for named color profiles."""

    color_profiles: ColorProfileCollection
    color_profile_active_index: int
    mixture_parts: Sequence[object]


def active_color_profile(
    settings: ColorSimulatorSettings,
) -> ColorProfileValues | None:
    """Return the selected profile, or none when the collection is empty."""
    index = settings.color_profile_active_index
    if not 0 <= index < len(settings.color_profiles):
        return None
    return settings.color_profiles[index]


def calculate_profile_color(profile: ColorProfileValues) -> RGB:
    """Calculate the scene-linear preview color for one saved profile."""
    return calculate_profile_appearance(profile).color


def calculate_profile_appearance(
    profile: ColorProfileValues,
) -> SimulatedSiliconeAppearance:
    """Calculate color and optical appearance for one saved profile."""
    colorants = (
        CalibratedColorant(
            calibration_color=cast(RGB, tuple(colorant.calibration_color[:3])),
            calibration_drops_per_ml=colorant.calibration_drops_per_ml,
            drops=colorant.drops,
            enabled=colorant.enabled,
            is_opacifier=colorant.is_opacifier,
        )
        for colorant in profile.colorants
    )
    return simulate_silicone_appearance(
        cast(RGB, tuple(profile.base_color[:3])),
        profile.base_volume_ml,
        profile.transparency,
        profile.cloudiness,
        colorants,
    )


def _configure_material(
    material: bpy.types.Material,
    profile: ColorProfileValues,
) -> None:
    """Build or update the add-on-owned Principled material."""
    material.name = f"{_MATERIAL_PREFIX}{profile.profile_name}"
    material.use_nodes = True
    node_tree = material.node_tree
    assert node_tree is not None

    shader = node_tree.nodes.get(_SHADER_NODE_NAME)
    if shader is None or shader.bl_idname != "ShaderNodeBsdfPrincipled":
        node_tree.nodes.clear()
        output = node_tree.nodes.new("ShaderNodeOutputMaterial")
        shader = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        shader.name = _SHADER_NODE_NAME
        node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    appearance = calculate_profile_appearance(profile)
    rgba = (*appearance.color, 1.0)
    material.diffuse_color = rgba  # pyright: ignore[reportAttributeAccessIssue]
    cast(_ValueSocket, shader.inputs["Base Color"]).default_value = rgba
    cast(
        _ValueSocket, shader.inputs["Transmission Weight"]
    ).default_value = appearance.transparency
    cast(
        _ValueSocket, shader.inputs["Subsurface Weight"]
    ).default_value = appearance.cloudiness
    cast(_ValueSocket, shader.inputs["IOR"]).default_value = 1.41
    cast(_ValueSocket, shader.inputs["Roughness"]).default_value = 0.2
    cast(_ValueSocket, shader.inputs["Alpha"]).default_value = 1.0


def update_color_preview_material(profile: ColorProfileValues) -> None:
    """Refresh an existing preview material without creating hidden data."""
    material = profile.preview_material
    if material is not None:
        _configure_material(material, profile)


def ensure_color_preview_material(
    profile: ColorProfileValues,
) -> bpy.types.Material:
    """Create the profile's preview material when missing, then update it."""
    material = profile.preview_material
    if material is None:
        material = bpy.data.materials.new(f"{_MATERIAL_PREFIX}{profile.profile_name}")
        profile.preview_material = material
    _configure_material(material, profile)
    return material


class _ValueSocket(Protocol):
    """Typed value surface shared by the concrete shader socket classes."""

    default_value: object


def _new_profile(settings: ColorSimulatorSettings) -> ColorProfileValues:
    """Append one profile and select it."""
    profile = settings.color_profiles.add()
    profile.profile_name = f"Profile {len(settings.color_profiles)}"
    profile.base_volume_ml = 100.0
    profile.base_color = (1.0, 1.0, 1.0)
    profile.transparency = 1.0
    profile.cloudiness = 0.0
    profile.colorant_active_index = -1
    settings.color_profile_active_index = len(settings.color_profiles) - 1
    return profile


class SILMOLD_OT_add_color_profile(bpy.types.Operator):
    """Add and select a named color profile."""

    bl_idname = "silicone_molding.add_color_profile"
    bl_label = "Add Color Profile"
    bl_options = {"REGISTER", "UNDO"}

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        profile = _new_profile(
            cast(ColorSimulatorSettings, context.scene.silicone_molding)
        )
        ensure_color_preview_material(profile)
        return {"FINISHED"}


class SILMOLD_OT_remove_color_profile(bpy.types.Operator):
    """Remove the active profile without deleting its applied material."""

    bl_idname = "silicone_molding.remove_color_profile"
    bl_label = "Remove Color Profile"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        settings = context.scene.silicone_molding
        return 0 <= settings.color_profile_active_index < len(settings.color_profiles)

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        settings = context.scene.silicone_molding
        index = settings.color_profile_active_index
        settings.color_profiles.remove(index)
        settings.color_profile_active_index = min(
            index, len(settings.color_profiles) - 1
        )
        profile = active_color_profile(cast(ColorSimulatorSettings, settings))
        if profile is not None:
            ensure_color_preview_material(profile)
        return {"FINISHED"}


class SILMOLD_OT_add_colorant(bpy.types.Operator):
    """Add a zero-dose colorant to the active profile."""

    bl_idname = "silicone_molding.add_colorant"
    bl_label = "Add Colorant"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        settings = cast(ColorSimulatorSettings, context.scene.silicone_molding)
        return active_color_profile(settings) is not None

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        settings = context.scene.silicone_molding
        profile = active_color_profile(cast(ColorSimulatorSettings, settings))
        if profile is None:
            return {"CANCELLED"}
        colorant = profile.colorants.add()
        colorant.enabled = True
        colorant.is_opacifier = False
        colorant.colorant_name = "Colorant"
        colorant.calibration_color = (1.0, 1.0, 1.0)
        colorant.calibration_drops_per_ml = 1.0
        colorant.drops = 0.0
        profile.colorant_active_index = len(profile.colorants) - 1
        update_color_preview_material(profile)
        return {"FINISHED"}


class SILMOLD_OT_remove_colorant(bpy.types.Operator):
    """Remove the active colorant from the active profile."""

    bl_idname = "silicone_molding.remove_colorant"
    bl_label = "Remove Colorant"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        profile = active_color_profile(
            cast(ColorSimulatorSettings, context.scene.silicone_molding)
        )
        return profile is not None and 0 <= profile.colorant_active_index < len(
            profile.colorants
        )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        profile = active_color_profile(
            cast(ColorSimulatorSettings, context.scene.silicone_molding)
        )
        if profile is None:
            return {"CANCELLED"}
        index = profile.colorant_active_index
        profile.colorants.remove(index)
        profile.colorant_active_index = min(index, len(profile.colorants) - 1)
        update_color_preview_material(profile)
        return {"FINISHED"}


class SILMOLD_OT_copy_mixture_volume_to_coloring(bpy.types.Operator):
    """Copy the enabled Mixture Calculator total to the active profile."""

    bl_idname = "silicone_molding.copy_mixture_volume_to_coloring"
    bl_label = "Use Mixture Total"
    bl_options = {"REGISTER", "UNDO"}

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        settings = context.scene.silicone_molding
        profile = active_color_profile(cast(ColorSimulatorSettings, settings))
        if profile is None:
            return {"CANCELLED"}
        total = sum(part.volume_ml for part in settings.mixture_parts if part.enabled)
        if total <= 0.0:
            self.report({"ERROR"}, "Mixture total must be greater than zero")
            return {"CANCELLED"}
        profile.base_volume_ml = total
        return {"FINISHED"}


def _selected_meshes(context: bpy.types.Context) -> list[bpy.types.Object]:
    selected = context.selected_objects or ()
    return [obj for obj in selected if obj.type == "MESH"]


class SILMOLD_OT_apply_color_material(bpy.types.Operator):
    """Assign the active profile's shared material to selected meshes."""

    bl_idname = "silicone_molding.apply_color_material"
    bl_label = "Apply to Selected"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    @override
    def poll(cls, context: bpy.types.Context) -> bool:
        profile = active_color_profile(
            cast(ColorSimulatorSettings, context.scene.silicone_molding)
        )
        return (
            context.mode == "OBJECT"
            and profile is not None
            and bool(_selected_meshes(context))
        )

    @override
    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        profile = active_color_profile(
            cast(ColorSimulatorSettings, context.scene.silicone_molding)
        )
        if profile is None:
            return {"CANCELLED"}
        material = ensure_color_preview_material(profile)
        objects = _selected_meshes(context)
        for obj in objects:
            mesh = cast(bpy.types.Mesh, obj.data)
            if len(mesh.materials) == 0:
                mesh.materials.append(material)
            else:
                mesh.materials[obj.active_material_index or 0] = material
        self.report({"INFO"}, f"Applied to {len(objects)} object(s)")
        return {"FINISHED"}
