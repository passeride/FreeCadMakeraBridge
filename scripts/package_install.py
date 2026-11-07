"""Build the self-contained offline installation ZIP from this checkout."""
from pathlib import Path
import zipfile

base = Path(__file__).resolve().parents[1]
files = ['Install_FreeCADMakeraBridge.FCMacro', 'bridge_installer.py', 'VERSION',
         'FreeCAD_SendToCommunity.FCMacro', 'FreeCAD_SendToOpenSpindle.FCMacro',
         'openspindle_bridge.py', 'README.md', 'docs/installation.md']
output = base/'dist'/'FreeCADMakeraBridge-install.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(base/name, 'FreeCADMakeraBridge/'+name)
print(output)
