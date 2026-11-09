"""Build the self-contained offline installation ZIP from this checkout."""
from pathlib import Path
import zipfile
import runpy

base = Path(__file__).resolve().parents[1]
runtime = runpy.run_path(str(base/'bridge_installer.py'))['FILES']
files = ['Install_FreeCADMakeraBridge.FCMacro', 'bridge_installer.py', 'VERSION',
         'README.md', 'docs/installation.md', *runtime]
output = base/'dist'/'FreeCADMakeraBridge-install.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(base/name, 'FreeCADMakeraBridge/'+name)
print(output)
