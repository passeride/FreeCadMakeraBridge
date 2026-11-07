"""Lazy workbench registration; no network or machine access at startup."""
from pathlib import Path
import FreeCADGui as Gui

ICON = str(Path(__file__).parent/'resources'/'bridge.svg')


class MakeraBridgeWorkbench(Gui.Workbench):
    MenuText = 'Makera Bridge'
    ToolTip = 'Klargjør FreeCAD CAM-jobber i OpenSpindle'
    Icon = ICON

    def Initialize(self):
        from .commands import register
        register()
        self.appendToolbar('Makera Bridge', ['MakeraBridge_Prepare'])
        self.appendMenu('Makera Bridge', ['MakeraBridge_Prepare'])

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


Gui.addWorkbench(MakeraBridgeWorkbench())
