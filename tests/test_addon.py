import importlib
import importlib.util
import json
import runpy
import tempfile
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from freecad.makera_bridge import commands


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
        machines = root / tree.find('p:content/p:machine/p:subdirectory', ns).text
        posts = root / tree.find('p:content/p:postprocessor/p:subdirectory', ns).text
        profile = json.loads((machines / 'Makera_Z1_Bridge.fcm').read_text())
        template = json.loads((root / 'freecad/makera_bridge/resources/job_Makera_Z1.json').read_text())
        self.assertEqual(template['Machine'], profile['machine']['name'])
        self.assertEqual(set(profile['machine']['axes']), {'X', 'Y', 'Z'})
        self.assertTrue((posts / (profile['postprocessor']['file_name'] + '_post.py')).is_file())

    def test_z1_assets_install_into_cam_directory_and_preserve_user_edits(self):
        machine_module = types.SimpleNamespace(MachineFactory=Mock())
        root = Path(__file__).resolve().parents[1]
        profiles = sorted((root / 'Resources' / 'Machines').glob('*.fcm'))
        self.assertEqual(len(profiles), 2)
        for profile in profiles:
            data = json.loads(profile.read_text(encoding='utf-8'))
            self.assertEqual(set(data['machine']['axes']), {'X', 'Y', 'Z'})
            self.assertEqual(data['postprocessor']['file_name'], 'makera_z1_bridge')
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory) / 'custom'
            prefs = types.SimpleNamespace(getAssetPath=lambda: assets, addAddonPostPath=Mock())
            modules = {'Machine.models.machine': machine_module, 'Path': types.SimpleNamespace(Preferences=prefs),
                       'FreeCAD': types.SimpleNamespace(Console=Mock())}
            with patch.dict(sys.modules, modules):
                spec = importlib.util.spec_from_file_location(
                    'isolated_z1_asset_init', root / 'freecad' / 'makera_bridge' / 'init.py')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                paths = assets / 'Tools'
                library = json.loads((paths / 'Library' / 'makera_bridge_z1.fctl').read_text(encoding='utf-8'))
                self.assertEqual(len(library['tools']), 8)
                for entry in library['tools']:
                    self.assertTrue((paths / 'Bit' / entry['path']).is_file())
                modified = paths / 'Bit' / library['tools'][0]['path']
                modified.write_text('user data', encoding='utf-8')
                removed = paths / 'Bit' / library['tools'][1]['path']
                removed.unlink()
                module.register_z1_assets()
                self.assertEqual(modified.read_text(encoding='utf-8'), 'user data')
                self.assertTrue(removed.is_file())
                prefs.addAddonPostPath.assert_called_with(str(root / 'Resources' / 'Post'))

    def test_toolbar_is_scoped_to_cam_without_extra_workbench(self):
        gui = types.ModuleType('FreeCADGui')
        gui.addWorkbench = Mock()
        gui.addCommand = Mock()
        gui.addWorkbenchManipulator = Mock()
        gui.addPreferencePage = Mock()
        cam, part, path = object(), object(), object()
        gui.listWorkbenches = Mock(return_value={'CAMWorkbench': cam, 'PartWorkbench': part, 'PathWorkbench': path})
        gui.activeWorkbench = Mock(return_value=cam)
        with patch.dict(sys.modules, {'FreeCADGui': gui}):
            name = 'freecad.makera_bridge.init_gui'
            sys.modules.pop(name, None)
            module = importlib.import_module(name)
            gui.addWorkbench.assert_not_called()
            self.assertEqual([call.args[0] for call in gui.addCommand.call_args_list],
                             ['MakeraBridge_Prepare', 'MakeraBridge_SendOperation', 'MakeraBridge_NewZ1Job'])
            for call in gui.addCommand.call_args_list:
                icon = call.args[1].GetResources()['Pixmap']
                if call.args[0] == 'MakeraBridge_NewZ1Job':
                    self.assertEqual(icon, 'CAM_Job')
                else:
                    self.assertTrue(Path(icon).is_file())
            gui.addPreferencePage.assert_called_once_with(commands.OpenSpindlePreferences, 'Makera Bridge')
            gui.addWorkbenchManipulator.assert_called_once_with(module.manipulator)
            expected = [{'append': 'Makera Bridge', 'toolBar': ''},
                        {'append': 'MakeraBridge_NewZ1Job', 'toolBar': 'Makera Bridge'},
                        {'append': 'MakeraBridge_Prepare', 'toolBar': 'Makera Bridge'},
                        {'append': 'MakeraBridge_SendOperation', 'toolBar': 'Makera Bridge'}]
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            # Re-activation yields the same declarative tree, not growing UI state.
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            gui.activeWorkbench.return_value = part
            self.assertEqual(module.manipulator.modifyToolBars(), [])
            gui.activeWorkbench.return_value = path
            self.assertEqual(module.manipulator.modifyToolBars(), expected)
            gui.activeWorkbench.return_value = None
            self.assertEqual(module.manipulator.modifyToolBars(), [])

    def test_new_z1_job_uses_native_model_picker_and_bundled_template(self):
        gui = Mock()
        dialog = Mock()
        dialog.getModels.return_value = [types.SimpleNamespace(Name='Body')]
        cam = types.SimpleNamespace(Job=Mock(), JobDlg=Mock())
        cam.JobDlg.JobCreate.return_value = dialog
        with patch.dict(sys.modules, {'FreeCADGui': gui, 'Path.Main.Gui': cam}):
            module = importlib.import_module('freecad.makera_bridge.init_gui')
            dialog.exec_.return_value = 0
            module.NewZ1JobCommand().Activated()
            cam.Job.Create.assert_not_called()
            dialog.exec_.return_value = 1
            module.NewZ1JobCommand().Activated()
            models, template = cam.Job.Create.call_args.args
            self.assertEqual(models, ['Body'])
            self.assertEqual(json.loads(Path(template).read_text())['Machine'], 'Makera Z1 3-axis - Makera Bridge')

    def test_command_runs_from_the_installed_module(self):
        from freecad.makera_bridge.commands import PrepareCommand
        app = types.ModuleType('FreeCAD'); app.ActiveDocument = None
        with patch.dict(sys.modules, {'FreeCAD': app}):
            command = PrepareCommand()
            self.assertFalse(command.IsActive())
            app.ActiveDocument = object()
            self.assertTrue(command.IsActive())
        with patch('freecad.makera_bridge.commands.run') as run:
            command.Activated()
            run.assert_called_once_with()

    def test_operation_selection_requires_one_active_job_member(self):
        operation = object()
        job = types.SimpleNamespace(Machine='Z1', Operations=types.SimpleNamespace(Group=[operation]))
        doc = types.SimpleNamespace(Objects=[job, operation])
        for selection in ([], [job], [operation, job], [object()]):
            self.assertIsNone(commands.selected_operation(doc, selection, lambda _: True))
        self.assertIsNone(commands.selected_operation(doc, [operation], lambda _: False))
        self.assertEqual(commands.selected_operation(doc, [operation], lambda _: True), (job, operation))
        with patch.object(commands, 'run') as run:
            commands.SendOperationCommand().Activated()
        run.assert_called_once_with(operation_only=True)

    def test_configured_send_posts_requested_scope_without_dialog(self):
        first = types.SimpleNamespace(Name='Pocket', Label='Lomme')
        second = types.SimpleNamespace(Name='Profile', Label='Profil')
        doc = Mock(Label='Skilt', FileName='Skilt.FCStd')
        job = types.SimpleNamespace(Document=doc, Machine='Z1', Name='Job', Label='Finish',
                                    PropertiesList=['OpenSpindleSourceId'], OpenSpindleSourceId='source',
                                    Operations=types.SimpleNamespace(Group=[first, second]))
        doc.Objects = [job, first, second]
        for obj in doc.Objects:
            obj.State = []
        prefs = Mock()
        values = {'Executable': 'OpenSpindle.exe', 'Exports': 'Exports'}
        prefs.GetString.side_effect = lambda key, default: values.get(key, default)
        app = types.SimpleNamespace(ActiveDocument=doc, Version=lambda: ['26', '3'], ParamGet=lambda _: prefs)
        gui = types.SimpleNamespace(Selection=Mock(), getMainWindow=Mock())
        gui.Selection.getSelection.return_value = [second]
        util = types.SimpleNamespace(activeForOp=lambda _: True, toolControllerForOp=lambda _: None)
        qt = types.SimpleNamespace(QtWidgets=Mock(), QtCore=Mock(), QtGui=Mock())
        modules = {'FreeCAD': app, 'FreeCADGui': gui, 'PySide': qt,
                   'Path.Base': types.SimpleNamespace(Util=util)}
        for operation_only in (False, True):
            with (
                self.subTest(operation_only=operation_only), patch.dict(sys.modules, modules),
                patch.object(commands, 'receiver_path', return_value=Path('OpenSpindle.exe')),
                patch.object(commands, 'postprocess', return_value=('G1 X1', 'makera')) as post,
                patch.object(commands, 'publish', return_value=(Path('program.nc'), {})) as publish,
                patch('freecad.makera_bridge.reference.export_reference', return_value={'name': 'Finish', 'model': 'fixture'}) as reference,
                patch.object(commands, 'launch') as launch,
            ):
                commands.run(operation_only=operation_only)
                if operation_only:
                    post.assert_called_once_with(job, [second])
                else:
                    post.assert_called_once_with(job)
                reference.assert_called_once_with(job)
                self.assertEqual(publish.call_args.args[3], reference.return_value)
                source = publish.call_args.args[2]
                self.assertEqual(source['scope'], 'operation' if operation_only else 'job')
                self.assertEqual(commands.export_label(source), 'Profil' if operation_only else 'Finish')
                launch.assert_called_once_with('OpenSpindle.exe', Path('program.nc'))
                self.assertEqual(qt.QtWidgets.mock_calls, [])

    def test_cam_command_loads_when_only_commands_file_is_present(self):
        source = Path(__file__).resolve().parents[1] / 'freecad' / 'makera_bridge' / 'commands.py'
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / 'commands.py'
            installed.write_bytes(source.read_bytes())
            spec = importlib.util.spec_from_file_location('isolated_addon_command', installed)
            command_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(command_module)
            with patch.object(command_module, 'run') as run:
                command_module.PrepareCommand().Activated()
            run.assert_called_once_with()

    def test_macro_copied_to_macro_directory_uses_installed_addon(self):
        source = Path(__file__).resolve().parents[1] / 'FreeCAD_SendToOpenSpindle.FCMacro'
        with tempfile.TemporaryDirectory() as directory:
            macro = Path(directory) / source.name
            macro.write_bytes(source.read_bytes())
            app = types.ModuleType('FreeCAD')
            pyside = types.ModuleType('PySide')
            pyside.QtWidgets = Mock()
            with patch.dict(sys.modules, {'FreeCAD': app, 'PySide': pyside}), patch(
                'freecad.makera_bridge.commands.run'
            ) as run:
                runpy.run_path(str(macro), run_name='__main__')
            run.assert_called_once_with()
