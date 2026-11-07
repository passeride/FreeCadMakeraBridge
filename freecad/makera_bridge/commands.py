"""Commands owned by the Makera Bridge workbench."""
from pathlib import Path
import runpy


class PrepareCommand:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).parent/'resources'/'bridge.svg'),
                'MenuText': 'Klargjør på Z1',
                'ToolTip': 'Eksporter en CAM Machine-jobb og åpne den i OpenSpindle'}

    def IsActive(self):
        import FreeCAD as App
        return App.ActiveDocument is not None

    def Activated(self):
        root = Path(__file__).resolve().parents[2]
        runpy.run_path(str(root/'FreeCAD_SendToOpenSpindle.FCMacro'), run_name='__main__')


def register():
    import FreeCADGui as Gui
    Gui.addCommand('MakeraBridge_Prepare', PrepareCommand())
