"""Contribute OpenSpindle commands to the CAM workbench."""
from pathlib import Path

import FreeCADGui as Gui
from .commands import register


def active_workbench_name():
    # .name() may be unavailable during a core workbench's first activation.
    active = Gui.activeWorkbench()
    for name, handler in Gui.listWorkbenches().items():
        if handler is active:
            return name
    return ''


class CAMToolbar:
    def modifyToolBars(self):
        if active_workbench_name() not in ('CAMWorkbench', 'PathWorkbench'):
            return []
        return [
            {'append': 'Makera Bridge', 'toolBar': ''},
            {'append': 'MakeraBridge_NewZ1Job', 'toolBar': 'Makera Bridge'},
            {'append': 'MakeraBridge_Prepare', 'toolBar': 'Makera Bridge'},
            {'append': 'MakeraBridge_SendOperation', 'toolBar': 'Makera Bridge'},
        ]


class NewZ1JobCommand:
    def GetResources(self):
        return {"Pixmap": "CAM_Job", "MenuText": "Ny Z1-jobb",
                "ToolTip": "Opprett en CAM-jobb med Makera Z1-maskin og postprosessor"}

    def IsActive(self):
        import FreeCAD as App
        return App.ActiveDocument is not None

    def Activated(self):
        from Path.Main.Gui import Job, JobDlg

        template = Path(__file__).parent / "resources" / "job_Makera_Z1.json"
        dialog = JobDlg.JobCreate()
        dialog.setupTitle("Ny Makera Z1-jobb")
        dialog.setupModel()
        if dialog.exec_() == 1:
            models = dialog.getModels()
            if models:
                Job.Create([model.Name for model in models], str(template))


register()
Gui.addCommand("MakeraBridge_NewZ1Job", NewZ1JobCommand())
manipulator = CAMToolbar()
Gui.addWorkbenchManipulator(manipulator)
