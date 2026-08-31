"""Build and update color simulator preview materials."""

from typing import Protocol, cast

import bpy

from ._color_adapter import ColorProfileValues, calculate_profile_appearance

_MATERIAL_PREFIX = "Silicone Mix - "
_SHADER_NODE_NAME = "Silicone Molding Shader"


class _ValueSocket(Protocol):
    """Typed value surface shared by the concrete shader socket classes."""

    default_value: object


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
    cast(_ValueSocket, shader.inputs["Subsurface Weight"]).default_value = 0.0
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
