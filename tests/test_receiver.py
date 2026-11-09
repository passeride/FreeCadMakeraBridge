from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from freecad.makera_bridge import commands as bridge


class ReceiverTests(unittest.TestCase):
    def test_cancel_missing_receiver_prevents_handoff(self):
        find, download = Mock(), Mock()
        result = bridge.configure_receiver('', True, lambda reason: 'cancel', find, download)
        self.assertIsNone(result)
        find.assert_not_called(); download.assert_not_called()

    def test_explicit_export_needs_no_receiver(self):
        decide = Mock()
        self.assertEqual(bridge.configure_receiver('', False, decide, Mock(), Mock()), ('', False))
        decide.assert_not_called()
        self.assertEqual(bridge.configure_receiver('', True, lambda _: 'export', Mock(), Mock()), ('', False))

    def test_download_is_explicit_and_does_not_imply_installation(self):
        actions = iter(['download', 'cancel'])
        download = Mock()
        result = bridge.configure_receiver('', True, lambda _: next(actions), Mock(), download)
        self.assertIsNone(result)
        download.assert_called_once_with(bridge.DOWNLOAD_URL)

    def test_find_repairs_missing_path_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder)/'OpenSpindle.exe'; app.touch()
            result = bridge.configure_receiver('', True, lambda _: 'find', lambda: str(app), Mock(), platform='win32')
            self.assertEqual(result, (str(app), True))

    def test_cancel_file_picker_returns_to_choice(self):
        actions = iter(['find', 'export'])
        result = bridge.configure_receiver('', True, lambda _: next(actions), lambda: '', Mock())
        self.assertEqual(result, ('', False))

    def test_windows_discovery_and_unexecutable_linux_file(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder)/'Programs/openspindle/OpenSpindle.exe'
            app.parent.mkdir(parents=True); app.touch()
            with patch.object(bridge.shutil, 'which', return_value=None):
                self.assertEqual(bridge.discover_receiver('win32', {'LOCALAPPDATA': folder}), str(app))
            with patch.object(bridge.os, 'access', return_value=False):
                with self.assertRaises(ValueError):
                    bridge.receiver_path(app, 'linux')
