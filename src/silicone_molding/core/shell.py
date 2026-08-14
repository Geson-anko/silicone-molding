"""Offset-shell construction, the blank a mold is carved out of.

Everything here is pure ``bmesh`` / data API: no ``bpy.ops``, no scene,
no depsgraph. That keeps it callable from a background Blender and from
the PyPI ``bpy`` wheel without a window manager context.
"""

import bmesh
import bpy

# Below this, ``bmesh.ops.solidify`` produces degenerate self-intersecting
# geometry rather than a usable wall.
MIN_THICKNESS = 1e-6


def build_shell_mesh(
    source: bpy.types.Mesh, thickness: float, *, name: str
) -> bpy.types.Mesh:
    """Build an outward offset shell around *source*.

    The source surface becomes the inner wall of the shell and the outer
    wall sits *thickness* away along the surface normals -- the shape a
    mold takes around its master model.

    For a closed source the result is a hollow solid: two watertight
    walls with no geometry bridging them, the inner one bounding the
    cavity the master will occupy.

    Args:
        source: Mesh to wrap. Must have at least one face.
        thickness: Outward wall thickness in Blender units (metres by
            default). Must be at least :data:`MIN_THICKNESS`.
        name: Name for the newly created mesh datablock.

    Returns:
        A newly created mesh datablock owned by ``bpy.data.meshes``. The
        caller is responsible for linking it to an object.

    Raises:
        ValueError: If *source* has no faces, or *thickness* is below
            :data:`MIN_THICKNESS`.
    """
    if not source.polygons:
        raise ValueError("source mesh has no faces to offset")
    if thickness < MIN_THICKNESS:
        raise ValueError(f"thickness must be >= {MIN_THICKNESS}, got {thickness}")

    bm = bmesh.new()
    try:
        bm.from_mesh(source)
        # `geom` is typed as the invariant union list, so a plain
        # `list[BMFace]` would not be assignable to it.
        geom: list[bmesh.types.BMVert | bmesh.types.BMEdge | bmesh.types.BMFace] = list(
            bm.faces
        )
        # bmesh.ops.solidify grows along -normal for positive thickness, so
        # the sign is flipped to get the outward wall documented above.
        bmesh.ops.solidify(bm, geom=geom, thickness=-thickness)
        bm.normal_update()
        shell = bpy.data.meshes.new(name)
        bm.to_mesh(shell)
    finally:
        bm.free()
    return shell
