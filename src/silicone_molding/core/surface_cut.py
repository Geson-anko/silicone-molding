"""A Geometry Nodes modifier that cuts a mesh with a thin surface."""

from typing import Final, cast

import bpy

SURFACE_CUT_MODIFIER_NAME: Final = "Surface Cut"

# The cap copied from the source surface has duplicate boundary vertices with
# the extruded sides. Weld those exact pairs without collapsing the two faces
# of the thin cutter into each other.
_MERGE_DISTANCE_FACTOR: Final = 0.49


def _input(node: bpy.types.Node, name: str) -> bpy.types.NodeSocket:
    """Return a node input through the non-optional base API."""
    return node.inputs[name]


def _output(node: bpy.types.Node, name: str) -> bpy.types.NodeSocket:
    """Return a node output through the non-optional base API."""
    return node.outputs[name]


def create_surface_cut(
    target: bpy.types.Object,
    surface: bpy.types.Object,
    thickness: float,
) -> bpy.types.NodesModifier:
    """Add one integrated Surface Cut modifier to *target*.

    A dedicated Geometry Nodes group turns *surface* into a closed cutter by
    extruding it along its normals, then subtracts that cutter from the input
    geometry with Blender's Manifold Boolean solver. The surface object itself
    is only referenced and remains unchanged.

    Args:
        target: Mesh object that receives the modifier.
        surface: Mesh object used as the live cutting surface.
        thickness: Positive cutter thickness in Blender units.

    Returns:
        The newly added Geometry Nodes modifier.
    """
    node_group = cast(
        bpy.types.GeometryNodeTree,
        bpy.data.node_groups.new(SURFACE_CUT_MODIFIER_NAME, "GeometryNodeTree"),
    )
    node_group.is_modifier = True
    interface = node_group.interface
    assert interface is not None
    interface.new_socket(
        name="Geometry",
        in_out="INPUT",
        socket_type="NodeSocketGeometry",  # pyright: ignore[reportArgumentType]
    )
    interface.new_socket(
        name="Geometry",
        in_out="OUTPUT",
        socket_type="NodeSocketGeometry",  # pyright: ignore[reportArgumentType]
    )

    group_input = node_group.nodes.new("NodeGroupInput")
    group_output = node_group.nodes.new("NodeGroupOutput")
    object_info = cast(
        bpy.types.GeometryNodeObjectInfo,
        node_group.nodes.new("GeometryNodeObjectInfo"),
    )
    object_info.transform_space = "RELATIVE"
    object_socket = cast(bpy.types.NodeSocketObject, _input(object_info, "Object"))
    object_socket.default_value = surface

    normal = node_group.nodes.new("GeometryNodeInputNormal")
    extrude = cast(
        bpy.types.GeometryNodeExtrudeMesh,
        node_group.nodes.new("GeometryNodeExtrudeMesh"),
    )
    extrude.mode = "FACES"
    offset_scale = cast(
        bpy.types.NodeSocketFloat,
        _input(extrude, "Offset Scale"),
    )
    offset_scale.default_value = -thickness
    individual = cast(bpy.types.NodeSocketBool, _input(extrude, "Individual"))
    individual.default_value = False

    flip = node_group.nodes.new("GeometryNodeFlipFaces")
    join = node_group.nodes.new("GeometryNodeJoinGeometry")
    merge = node_group.nodes.new("GeometryNodeMergeByDistance")
    merge_distance = cast(
        bpy.types.NodeSocketFloat,
        _input(merge, "Distance"),
    )
    merge_distance.default_value = thickness * _MERGE_DISTANCE_FACTOR

    boolean = cast(
        bpy.types.GeometryNodeMeshBoolean,
        node_group.nodes.new("GeometryNodeMeshBoolean"),
    )
    boolean.operation = "DIFFERENCE"
    boolean.solver = "MANIFOLD"

    links = node_group.links
    links.new(_output(group_input, "Geometry"), _input(boolean, "Mesh 1"))
    links.new(_output(object_info, "Geometry"), _input(extrude, "Mesh"))
    links.new(_output(normal, "Normal"), _input(extrude, "Offset"))
    links.new(_output(extrude, "Mesh"), _input(flip, "Mesh"))
    links.new(_output(object_info, "Geometry"), _input(join, "Geometry"))
    links.new(_output(flip, "Mesh"), _input(join, "Geometry"))
    links.new(_output(join, "Geometry"), _input(merge, "Geometry"))
    links.new(_output(merge, "Geometry"), _input(boolean, "Mesh 2"))
    links.new(_output(boolean, "Mesh"), _input(group_output, "Geometry"))

    modifier = cast(
        bpy.types.NodesModifier,
        target.modifiers.new(SURFACE_CUT_MODIFIER_NAME, "NODES"),
    )
    modifier.node_group = node_group
    return modifier
