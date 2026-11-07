"""Contribute one command to CAM, without registering another workbench."""
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
            {'append': 'MakeraBridge_Prepare', 'toolBar': 'Makera Bridge'},
        ]


register()
manipulator = CAMToolbar()
Gui.addWorkbenchManipulator(manipulator)
