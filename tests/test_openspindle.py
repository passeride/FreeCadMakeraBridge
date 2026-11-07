import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import openspindle_bridge as bridge


class HandoffTests(unittest.TestCase):
    def test_snapshot_preserves_code_and_revision_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            code = '(tabs)\nG21\nG1X1Z0.5\nG1X2Z-1\n'
            source = {'job_label': '../Profil æ', 'id': 'stable-job'}
            a, ma = bridge.publish(folder, code, source)
            b, mb = bridge.publish(folder, code, source)
            self.assertNotEqual(a, b)
            self.assertEqual(a.read_text(), code)
            self.assertEqual(ma['program']['sha256'], mb['program']['sha256'])
            self.assertEqual(json.loads((a.parent/'handoff.json').read_text())['status'], 'exported_locally')
            self.assertEqual(a.parent.parent, Path(folder))
            self.assertFalse(list(Path(folder).glob('.export-*')))
            _, changed = bridge.publish(folder, code+'G1X3\n', source)
            self.assertNotEqual(ma['program']['sha256'], changed['program']['sha256'])

    def test_comments_and_empty_or_oversized_programs_are_rejected(self):
        for code in ['', '(G1 X1)\n;G0', 'G10L2P0X0', 'G1X1\n'+' '*bridge.MAX_BYTES]:
            with self.assertRaises(ValueError):
                bridge.validate_nc(code)

    def test_shell_characters_are_one_literal_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder)/'OpenSpindle app.exe'
            executable.touch()
            nc = Path(folder)/'job ; $(danger).nc'
            nc.write_text('G1X1')
            process = Mock()
            bridge.launch(executable, nc, platform='win32', popen=process)
            process.assert_called_once_with([str(executable), str(nc)], shell=False)

    def test_missing_app_keeps_export_available(self):
        with tempfile.TemporaryDirectory() as folder:
            nc, _ = bridge.publish(folder, 'G1X1', {'job_label': 'test'})
            with self.assertRaises(ValueError):
                bridge.launch(Path(folder)/'missing', nc)
            self.assertTrue(nc.exists())

    def test_failed_snapshot_write_leaves_no_partial_export(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path, 'write_text', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    bridge.publish(folder, 'G1X1', {'job_label': 'test'})
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_source_id_persists_and_copied_jobs_get_a_new_identity(self):
        from types import SimpleNamespace
        class Job:
            def addProperty(self, *args):
                self.PropertiesList.append(args[1])
                self.OpenSpindleSourceId = ''
        doc = SimpleNamespace(Label='part', FileName='', Objects=[])
        job = Job()
        job.Document = doc
        job.PropertiesList = []
        job.Name = 'Job'
        job.Label = 'Pocket'
        job.Operations = SimpleNamespace(Group=[])
        doc.Objects = [job]
        first = bridge.source_metadata(job, 'makera', ['26', '3'])
        self.assertEqual(first['id'], bridge.source_metadata(job, 'makera', [])['id'])
        self.assertFalse(first['document_saved'])
        duplicate = SimpleNamespace(OpenSpindleSourceId=first['id'])
        doc.Objects.append(duplicate)
        self.assertNotEqual(first['id'], bridge.source_metadata(job, 'makera', [])['id'])

    def test_mac_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder)/'OpenSpindle.app'
            app.mkdir()
            nc = Path(folder)/'job.nc'; nc.touch()
            process = Mock()
            bridge.launch(app, nc, platform='darwin', popen=process)
            process.assert_called_once_with(['/usr/bin/open', '-a', str(app), str(nc)], shell=False)

    def test_recompute_errors_block_export(self):
        obj = Mock(Label='Pocket', State=['Invalid'])
        job = Mock(); job.Document.Objects = [obj]
        with self.assertRaises(ValueError):
            bridge.check_job(job)
        job.Document.recompute.assert_called_once()


if __name__ == '__main__':
    unittest.main()
