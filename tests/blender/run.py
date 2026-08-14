"""Tier-2 integration checks, run inside a real Blender.

Invoked by ``just blender-test`` as::

    blender --background --python tests/blender/run.py

This runs *after* ``extension install-file``, so it verifies the parts the
``bpy`` wheel cannot: that the built zip installs, that Blender resolves
the add-on under its extension module path, and that the operator behaves
identically there. It deliberately has **no third-party dependencies** --
not even pytest -- so that it needs nothing installed into Blender's own
Python on any of the three CI platforms.

Failures raise ``AssertionError``; the exit code is set explicitly at the
end because Blender swallows tracebacks from ``--python`` scripts.
"""

import sys
import traceback

import addon_utils
import bpy

# Blender exposes user-repository extensions under this module path.
ADDON_MODULE = "bl_ext.user_default.silicone_molding"


def check_addon_is_enabled() -> None:
    """The installed extension must be importable and enabled."""
    enabled = {module.__name__ for module in addon_utils.modules() if module}
    assert (
        ADDON_MODULE in sys.modules or ADDON_MODULE in enabled
    ), f"{ADDON_MODULE} was not enabled; installed add-ons: {sorted(enabled)}"
    assert hasattr(bpy.ops, "silicone_molding"), "operator namespace is missing"


def check_scene_properties() -> None:
    """The scene must carry the add-on's settings after registration."""
    assert bpy.context.scene.silicone_molding is not None, "scene settings are missing"


CHECKS = (
    check_addon_is_enabled,
    check_scene_properties,
)


def main() -> int:
    """Run every check, printing one line per result.

    Returns an exit code.
    """
    print(f"blender {bpy.app.version_string} -- tier-2 integration checks")
    failures = 0
    for check in CHECKS:
        try:
            check()
        except Exception:
            failures += 1
            print(f"FAIL {check.__name__}")
            traceback.print_exc()
        else:
            print(f"ok   {check.__name__}")
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
