"""Register the bundled Z1 assets with CAM at FreeCAD startup."""
from pathlib import Path


def register_z1_assets():
    from Machine.models.machine import MachineFactory
    from Path import Preferences

    resources = Path(__file__).resolve().parents[2] / "Resources"
    # 26.3 can look up machines and posts before its addon pickers are opened.
    # Register here so both paths work even on builds with lazy discovery.
    MachineFactory.register_addon_machine_dir(resources / "Machines", namespace="Makera Bridge")
    Preferences.addAddonPostPath(str(resources / "Post"))


register_z1_assets()
