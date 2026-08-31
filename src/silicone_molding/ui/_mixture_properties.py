"""Mixture-table rows and their selection-state type boundary."""

from collections.abc import Sequence
from typing import Protocol

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty


class SelectableMixturePart(Protocol):
    """Typed view used by the active-row update callback."""

    selected: bool


class MixtureSelectionState(Protocol):
    """Typed view of dynamic RNA fields unavailable to static analysis."""

    mixture_active_index: int
    mixture_selection_anchor: int
    mixture_parts: Sequence[SelectableMixturePart]


class SiliconeMoldingMixturePart(bpy.types.PropertyGroup):
    """One manually entered part in the silicone mixture table."""

    enabled: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Enabled",
        description="Include this part in mixture totals",
        default=True,
    )

    selected: BoolProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Selected",
        description="Include this part in the selected subtotal",
        default=False,
    )

    part_name: StringProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Name",
        default="Part",
    )

    # Deliberately no ``unit="VOLUME"``: mixture inputs are always mL.
    volume_ml: FloatProperty(  # pyright: ignore[reportInvalidTypeForm]
        name="Volume (mL)",
        default=0.0,
        min=0.0,
        precision=2,
    )
