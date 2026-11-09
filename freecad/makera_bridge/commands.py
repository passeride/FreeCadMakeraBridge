"""Lightweight command registered for the CAM toolbar."""
from pathlib import Path


class PrepareCommand:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).parent/'resources'/'bridge.svg'),
                'MenuText': 'Klargjør på Z1',
                'ToolTip': 'Eksporter en CAM Machine-jobb og åpne den i OpenSpindle'}

    def IsActive(self):
        import FreeCAD as App
        return App.ActiveDocument is not None

    def Activated(self):
        from .handoff import run

        run()


def register():
    import FreeCADGui as Gui
    Gui.addCommand('MakeraBridge_Prepare', PrepareCommand())
