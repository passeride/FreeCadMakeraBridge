import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET


class AddonTests(unittest.TestCase):
    def test_manifest_and_assets_match_registration(self):
        root = Path(__file__).resolve().parents[1]
        tree = ET.parse(root/'package.xml')
        ns = {'p': 'https://wiki.freecad.org/Package_Metadata'}
        self.assertEqual(tree.find('p:version', ns).text, (root/'VERSION').read_text().strip())
        self.assertIsNotNone(tree.find('p:content/p:other', ns))
        self.assertIsNone(tree.find('p:content/p:workbench', ns))
        self.assertTrue((root/tree.find('p:icon', ns).text).is_file())
        self.assertTrue((root/tree.find('p:license', ns).attrib['file']).is_file())

    def test_toolbar_is_scoped_to_cam_without_extra_workbench(self):
        gui = types.ModuleType('FreeCADGui')
        gui.addWorkbench = Mock()
        gui.addCommand = Mock()
        gui.addWorkbenchManipulator = Mock()
        cam, part, path = object(), object(), object()
        gui.listWorkbenches = Mock(return_value={'CAMWorkbench': cam, 'PartWorkbench': part, 'PathWorkbench': path})
        gui.activeWorkbench = Mock(return_value=cam)
        with patch.dict(sys.modules, {'FreeCADGui': gui}):
            name = 'freecad.makera_bridge.init_gui'
            sys.modules.pop(name, None)
            module = importlib.import_module(name)
            gui.addWorkbench.assert_not_called()
            gui.addCommand.assert_called_once()
            gui.addWorkbenchManipulator.assert_called_once_with(module.manipulator)
            expected = [{'append': 'Makera Bridge', 'toolBar': ''},
                        {'append': 'MakeraBridge_Prepare', 'toolBar': 'Makera Bridge'}]
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            # Re-activation yields the same declarative tree, not growing UI state.
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            gui.activeWorkbench.return_value = part
            self.assertEqual(module.manipulator.modifyToolBars(), [])
            gui.activeWorkbench.return_value = path
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            gui.activeWorkbench.return_value = None
            self.assertEqual(module.manipulator.modifyToolBars(), [])

    def test_command_uses_bundled_macro_without_installer(self):
        from freecad.makera_bridge.commands import PrepareCommand
        app = types.ModuleType('FreeCAD'); app.ActiveDocument = None
        with patch.dict(sys.modules, {'FreeCAD': app}):
            command = PrepareCommand()
            self.assertFalse(command.IsActive())
            app.ActiveDocument = object()
            self.assertTrue(command.IsActive())
        with patch('freecad.makera_bridge.commands.runpy.run_path') as run:
            command.Activated()
            path = Path(run.call_args.args[0])
            self.assertTrue(path.is_file())
            self.assertEqual(path.name, 'FreeCAD_SendToOpenSpindle.FCMacro')
            self.assertEqual(run.call_args.kwargs, {'run_name': '__main__'})
