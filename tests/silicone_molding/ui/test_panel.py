"""Executable spec for the sidebar's panel structure.

Source of truth: ``memory/specs/volume_measurement.md`` §5.8, acceptance
criteria AC-60 -- AC-65.

The sidebar is one header-only parent panel with two collapsible children,
``Measurement`` above ``Processing`` (FR-3, FR-4). What a background run can
state about that structure is the class-level declaration: who the parent
is, in which order the children are drawn, and that neither child hides or
collapses itself. The contents of ``draw`` -- the two branches of the result
row and the fact that it measures nothing (FR-25, FR-48) -- cannot be
reached without a window, and are covered by the review checklist (§10.4)
and the manual checks AC-71 -- AC-74.

That registration actually accepts this parent/child arrangement (FR-8) is
asserted in ``tests/silicone_molding/test_register.py``.
"""

import pytest

from silicone_molding.ui import (
    SILMOLD_PT_main,
    SILMOLD_PT_measurement,
    SILMOLD_PT_processing,
)


class TestTheSubPanelsSitInsideTheMainPanel:
    def test_measurement_is_a_child_of_the_main_panel(self) -> None:
        # AC-62 / FR-3
        assert SILMOLD_PT_measurement.bl_parent_id == SILMOLD_PT_main.bl_idname

    def test_processing_is_a_child_of_the_main_panel(self) -> None:
        # AC-62 / FR-3
        assert SILMOLD_PT_processing.bl_parent_id == SILMOLD_PT_main.bl_idname

    def test_measurement_is_drawn_above_processing(self) -> None:
        # AC-63 / FR-4: the order is declared with `bl_order` so that it does
        # not depend on the order of `_CLASSES`. Only the relation is fixed
        # here; the literal values are free to change.
        assert SILMOLD_PT_measurement.bl_order < SILMOLD_PT_processing.bl_order


class TestTheSubPanelsAreOpenAndAlwaysVisible:
    def test_neither_sub_panel_starts_collapsed(self) -> None:
        # AC-64 / FR-6: both sections are open on first draw. `bl_options` is
        # read with a default because Blender leaves the attribute undefined
        # unless the class sets it, and undefined already means "open".
        measurement_options = getattr(SILMOLD_PT_measurement, "bl_options", frozenset())
        processing_options = getattr(SILMOLD_PT_processing, "bl_options", frozenset())

        assert "DEFAULT_CLOSED" not in measurement_options
        assert "DEFAULT_CLOSED" not in processing_options

    def test_neither_sub_panel_hides_itself(self) -> None:
        # AC-65 / FR-7: the panels stay visible in every mode, including edit
        # mode; it is the buttons inside them that grey out via the
        # operators' own `poll`. `bpy.types.Panel` defines no `poll` of its
        # own, so the attribute exists only if the add-on declared one.
        assert not hasattr(SILMOLD_PT_measurement, "poll")
        assert not hasattr(SILMOLD_PT_processing, "poll")


@pytest.mark.api_contract
class TestPublicSurface:
    """Contract pins, not behaviour tests.

    A panel's collapsed state is stored in the ``.blend``'s screen data
    under its ``bl_idname``, and the tab a panel appears in is addressed by
    ``bl_category`` (NFR-4). Renaming any of these silently resets the
    sidebar of every existing file, so a change here must be deliberate.
    """

    def test_the_main_panel_keeps_its_idname_and_tab(self) -> None:
        # AC-60 / FR-1: unchanged from before the split into sub-panels.
        assert SILMOLD_PT_main.bl_idname == "SILMOLD_PT_main"
        assert SILMOLD_PT_main.bl_category == "Silicone Molding"

    def test_the_measurement_panel_keeps_its_idname(self) -> None:
        # AC-61
        assert SILMOLD_PT_measurement.bl_idname == "SILMOLD_PT_measurement"

    def test_the_processing_panel_keeps_its_idname(self) -> None:
        # AC-61
        assert SILMOLD_PT_processing.bl_idname == "SILMOLD_PT_processing"
