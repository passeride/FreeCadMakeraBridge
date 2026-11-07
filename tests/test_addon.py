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
        self.assertEqual(tree.find('p:content/p:workbench/p:classname', ns).text, 'MakeraBridgeWorkbench')
        self.assertTrue((root/tree.find('p:icon', ns).text).is_file())
        self.assertTrue((root/tree.find('p:license', ns).attrib['file']).is_file())

    def test_registration_is_lazy_and_creates_own_toolbar(self):
        gui = types.ModuleType('FreeCADGui')
        gui.Workbench = type('Workbench', (), {'appendToolbar': Mock(), 'appendMenu': Mock()})
        gui.addWorkbench = Mock(); gui.addCommand = Mock()
        with patch.dict(sys.modules, {'FreeCADGui': gui}):
            name = 'freecad.makera_bridge.init_gui'
            sys.modules.pop(name, None)
            module = importlib.import_module(name)
            gui.addWorkbench.assert_called_once()
            gui.addCommand.assert_not_called()
            wb = module.MakeraBridgeWorkbench()
            wb.Initialize()
            gui.addCommand.assert_called_once()
            self.assertEqual(gui.addCommand.call_args.args[0], 'MakeraBridge_Prepare')
            self.assertEqual(wb.GetClassName(), 'Gui::PythonWorkbench')

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
