from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import bridge_installer as installer


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'source'; self.source.mkdir()
        for name in installer.FILES:
            (self.source/name).parent.mkdir(parents=True, exist_ok=True)
            (self.source/name).write_text('x = 1\n')
        (self.source/'VERSION').write_text('0.1')
        self.target = self.base/'Macro'

    def test_install_update_and_rollback_preserve_unrelated_files(self):
        self.target.mkdir()
        (self.target/'Mine.FCMacro').write_text('mine')
        first = installer.install(self.source, self.target)
        self.assertIsNone(first['previous'])
        self.assertEqual(installer.install(self.source, self.target), first)
        (self.source/installer.FILES[0]).write_text('x = 2\n')
        (self.source/'VERSION').write_text('0.2')
        second = installer.install(self.source, self.target)
        self.assertEqual(second['previous'], first['active'])
        self.assertEqual(installer.rollback(self.target)['active'], first['active'])
        self.assertEqual(installer.rollback(self.target)['active'], second['active'])
        self.assertEqual((self.target/'Mine.FCMacro').read_text(), 'mine')

    def test_update_preserves_rollback_to_legacy_flat_layout(self):
        import hashlib

        version = '0.2.0'
        content = b'x = 1\n'
        digest = hashlib.sha256(version.encode() + b'\0')
        for name in sorted(installer.LEGACY_FILES):
            digest.update(name.encode() + b'\0' + content + b'\0')
        legacy_id = digest.hexdigest()
        root = self.target / installer.ROOT
        legacy = root / 'versions' / legacy_id
        legacy.mkdir(parents=True)
        for name in installer.LEGACY_FILES:
            (legacy / name).write_bytes(content)
        (legacy / 'VERSION').write_text(version)
        installer.atomic_json(root / 'active.json', {
            'version': version, 'active': legacy_id, 'previous': None,
        })
        new = installer.install(self.source, self.target)
        self.assertEqual(new['previous'], legacy_id)
        self.assertEqual(installer.rollback(self.target)['active'], legacy_id)

    def test_failure_to_activate_keeps_previous_version(self):
        first = installer.install(self.source, self.target)
        (self.source/installer.FILES[0]).write_text('x = 2\n')
        with patch.object(installer, 'atomic_json', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                installer.install(self.source, self.target)
        self.assertEqual(installer.current(self.target), first)

    def test_conflicting_launcher_is_not_overwritten(self):
        self.target.mkdir()
        (self.target/installer.LAUNCHER).write_text('personal macro')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.target)
        self.assertEqual((self.target/installer.LAUNCHER).read_text(), 'personal macro')

    def test_modified_install_blocks_update_and_rollback(self):
        first = installer.install(self.source, self.target)
        installed = self.target/installer.ROOT/'versions'/first['active']
        (installed/installer.FILES[0]).write_text('custom = True')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.target)

    def test_missing_or_invalid_package_does_not_change_install(self):
        first = installer.install(self.source, self.target)
        (self.source/installer.FILES[1]).write_text('invalid syntax !')
        with self.assertRaises(SyntaxError):
            installer.install(self.source, self.target)
        self.assertEqual(installer.current(self.target), first)

    def test_extracted_distribution_installs_without_checkout_dependencies(self):
        import subprocess
        import sys
        import zipfile
        import runpy
        base = Path(__file__).resolve().parents[1]
        subprocess.run([sys.executable, str(base/'scripts'/'package_install.py')], check=True, capture_output=True)
        with zipfile.ZipFile(base/'dist'/'FreeCADMakeraBridge-install.zip') as archive:
            archive.extractall(self.base/'download')
        source = self.base/'download'/'FreeCADMakeraBridge'
        api = runpy.run_path(str(source/'bridge_installer.py'), run_name='package_test')
        state = api['install'](source, self.target)
        self.assertEqual(api['verify_revision'](self.target/installer.ROOT, state['active']), (source/'VERSION').read_text().strip())

    def test_fresh_install_requires_no_rollback(self):
        with self.assertRaises(ValueError):
            installer.rollback(self.target)


if __name__ == '__main__':
    unittest.main()
