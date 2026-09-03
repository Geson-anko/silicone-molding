"""Contract pins on the extension manifest.

``blender_manifest.toml`` is the single source of truth for the released
artefact's identity: the id becomes the import path
(``bl_ext.<repo>.<id>``) and the version is what the release workflow
matches the git tag against. These are pins, not behaviour tests.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

MANIFEST_PATH = (
    Path(__file__).parents[2] / "src" / "silicone_casting" / ("blender_manifest.toml")
)


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return tomllib.loads(MANIFEST_PATH.read_text())


@pytest.mark.api_contract
class TestManifest:
    def test_id_matches_the_package_directory(self, manifest: dict[str, Any]) -> None:
        assert manifest["id"] == MANIFEST_PATH.parent.name

    def test_declares_itself_an_add_on(self, manifest: dict[str, Any]) -> None:
        assert manifest["type"] == "add-on"
        assert manifest["schema_version"] == "1.0.0"

    def test_minimum_blender_is_5_1(self, manifest: dict[str, Any]) -> None:
        # 5.0 ships Python 3.11; 5.1+ ships 3.13, which the toolchain targets.
        assert manifest["blender_version_min"] == "5.1.0"

    def test_license_is_gpl_compatible(self, manifest: dict[str, Any]) -> None:
        assert manifest["license"] == ["SPDX:GPL-3.0-or-later"]

    def test_version_is_a_three_part_number(self, manifest: dict[str, Any]) -> None:
        parts = manifest["version"].split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)
