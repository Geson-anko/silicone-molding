"""Mesh processing that does not depend on ``bpy.ops`` or an interactive
context."""

from .shell import MIN_THICKNESS, build_shell_mesh

__all__ = ["MIN_THICKNESS", "build_shell_mesh"]
