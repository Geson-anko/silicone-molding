"""Millimetre to Blender-unit conversion.

The expected values are derived from the definition in the spec
(``mm / 1000 / scale_length``), not read off a run: 3 mm is 0.003 m, and
``scale_length`` says how many metres one Blender unit is worth.
"""

import ast
import inspect
from types import ModuleType

import pytest

from silicone_molding.core import mm_to_units, units as units_module


def _imported_module_names(module: ModuleType) -> set[str]:
    """Top-level names of every module imported anywhere in *module*."""
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return {name.split(".")[0] for name in names}


class TestMmToUnits:
    def test_three_millimetres_is_three_thousandths_of_a_unit_by_default(self) -> None:
        # scale_length 1.0 is Blender's default: 1 unit is 1 metre.
        assert mm_to_units(3.0, 1.0) == pytest.approx(0.003, rel=1e-12)

    def test_three_millimetres_is_three_units_when_a_unit_is_a_millimetre(self) -> None:
        # Spec S-7: with scale_length 0.001 a unit *is* a millimetre, so
        # the same physical wall must come out as 3.0 units. The value the
        # user typed never changes; only its unit expression does.
        assert mm_to_units(3.0, 0.001) == pytest.approx(3.0, rel=1e-12)

    def test_zero_millimetres_is_zero_units(self) -> None:
        assert mm_to_units(0.0, 1.0) == 0.0


class TestUnitsModuleStandsAloneFromBlender:
    def test_the_conversion_module_does_not_import_bpy(self) -> None:
        # NFR-1 / FR-5: the conversion is pure arithmetic over a
        # scale_length the caller passes in. Importing bpy here would let
        # the scene leak back into a function that must not read it.
        assert "bpy" not in _imported_module_names(units_module)
