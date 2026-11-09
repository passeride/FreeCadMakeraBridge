"""Register the bundled Z1 assets with CAM at FreeCAD startup."""
from pathlib import Path


def install_tool_library(resources, asset_path):
    """Install namespaced bits before their library without replacing user files."""
    for folder, extension in (("Bit", "fctb"), ("Library", "fctl")):
        source = resources / "Tools" / folder
        target = Path(asset_path) / "Tools" / folder
        target.mkdir(parents=True, exist_ok=True)
        for file in sorted(source.glob(f"*.{extension}")):
            data = file.read_bytes()
            try:
                output = (target / file.name).open("xb")
            except FileExistsError:
                continue
            try:
                with output:
                    output.write(data)
            except OSError:
                (target / file.name).unlink(missing_ok=True)
                raise


def register_z1_assets():
    import FreeCAD
    from Machine.models.machine import MachineFactory
    from Path import Preferences

    resources = Path(__file__).resolve().parents[2] / "Resources"
    # 26.3 can look up machines and posts before its addon pickers are opened.
    # Register here so both paths work even on builds with lazy discovery.
    MachineFactory.register_addon_machine_dir(resources / "Machines", namespace="Makera Bridge")
    Preferences.addAddonPostPath(str(resources / "Post"))
    try:
        install_tool_library(resources, Preferences.getAssetPath())
    except OSError as error:
        FreeCAD.Console.PrintWarning(f"Makera Bridge: could not install the Z1 tool library: {error}\n")


register_z1_assets()
