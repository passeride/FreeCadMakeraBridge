"""Offline per-user installation, atomic activation and one-version rollback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

LEGACY_FILES = ('FreeCAD_SendToCommunity.FCMacro', 'FreeCAD_SendToOpenSpindle.FCMacro',
                'openspindle_bridge.py')
FILES = ('FreeCAD_SendToOpenSpindle.FCMacro',
         'freecad/makera_bridge/__init__.py',
         'freecad/makera_bridge/bridge.py',
         'freecad/makera_bridge/cam.py',
         'freecad/makera_bridge/handoff.py')
ROOT = 'FreeCADMakeraBridge'
LAUNCHER = 'Klargjor_pa_Z1.FCMacro'
WRAPPER = '''# Managed by FreeCADMakeraBridge installer; do not edit.
from pathlib import Path
import json
import runpy
import FreeCAD as App
from PySide import QtWidgets
try:
    root = Path(__file__).resolve().parent / "FreeCADMakeraBridge"
    state = json.loads((root / "active.json").read_text(encoding="utf-8"))
    revision = state["active"]
    if len(revision) != 64 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Invalid installed revision")
    runpy.run_path(str(root / "versions" / revision / "FreeCAD_SendToOpenSpindle.FCMacro"), run_name="__main__")
except Exception as exc:
    QtWidgets.QMessageBox.critical(None, "Klargjør på Z1", str(exc))
'''


def atomic_json(path, data):
    fd, name = tempfile.mkstemp(prefix='.activate-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def payload(source, files=FILES):
    source = Path(source)
    data = {name: (source/name).read_bytes() for name in files}
    for name, content in data.items():
        compile(content, name, 'exec')
    version = (source/'VERSION').read_text().strip()
    if not version or len(version) > 100:
        raise ValueError('Invalid version')
    digest = hashlib.sha256(version.encode() + b"\0")
    for name, content in sorted(data.items()):
        digest.update(name.encode() + b'\0' + content + b'\0')
    return version, digest.hexdigest(), data


def current(macro_dir):
    path = Path(macro_dir)/ROOT/'active.json'
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def verify_revision(root, revision):
    if not isinstance(revision, str) or len(revision) != 64 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Invalid revision')
    directory = root/'versions'/revision
    # Earlier standalone versions used three flat files. Keep them roll-backable.
    files = LEGACY_FILES if (directory/'openspindle_bridge.py').is_file() else FILES
    version, actual, _ = payload(directory, files)
    if actual != revision:
        raise ValueError('Installed files were modified; installation has not been changed.')
    return version


def install(source, macro_dir):
    version, revision, data = payload(source)
    macro_dir = Path(macro_dir).expanduser().resolve()
    macro_dir.mkdir(parents=True, exist_ok=True)
    launcher = macro_dir/LAUNCHER
    if launcher.exists() and launcher.read_text(encoding='utf-8') != WRAPPER:
        raise ValueError('A different Klargjor_pa_Z1.FCMacro exists. Move or rename it first.')
    root = macro_dir/ROOT
    versions = root/'versions'
    versions.mkdir(parents=True, exist_ok=True)
    old = current(macro_dir)
    if old:
        verify_revision(root, old['active'])
    destination = versions/revision
    if destination.exists():
        verify_revision(root, revision)
    else:
        stage = Path(tempfile.mkdtemp(prefix='.install-', dir=versions))
        try:
            for name, content in data.items():
                target = stage/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            (stage/'VERSION').write_text(version, encoding='utf-8')
            os.rename(stage, destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    # The stable launcher is never replaced during updates. All runtime files
    # are complete before one atomic pointer makes the new version visible.
    if not launcher.exists():
        with launcher.open('x', encoding='utf-8', newline='') as stream:
            stream.write(WRAPPER)
    if old and old['active'] == revision:
        return old
    state = {'version': version, 'active': revision,
             'previous': old['active'] if old else None}
    atomic_json(root/'active.json', state)
    return state


def rollback(macro_dir):
    macro_dir = Path(macro_dir).expanduser().resolve()
    root = macro_dir/ROOT
    state = current(macro_dir)
    if not state or not state.get('previous'):
        raise ValueError('No previous version is available.')
    version = verify_revision(root, state['previous'])
    replacement = {'version': version, 'active': state['previous'], 'previous': state['active']}
    atomic_json(root/'active.json', replacement)
    return replacement


def gui(source):
    import FreeCAD as App
    from PySide import QtWidgets
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle('Installer FreeCAD → OpenSpindle')
    layout = QtWidgets.QFormLayout(dialog)
    default = App.ParamGet('User parameter:BaseApp/Preferences/Macro').GetString('MacroPath', App.getUserMacroDir())
    target = QtWidgets.QLineEdit(default)
    layout.addRow('FreeCADs makromappe:', target)
    status = QtWidgets.QLabel()
    def refresh():
        try:
            state = current(target.text())
            status.setText('Installert: ' + state['version'] if state else 'Ikke installert i denne mappen')
        except Exception as exc:
            status.setText(str(exc))
    target.textChanged.connect(refresh)
    refresh()
    layout.addRow(status)
    note = QtWidgets.QLabel('Installer eller oppdater fra denne utpakkede pakken. Innstillinger og eksporterte jobber beholdes.\n'
                           'Lukk andre FreeCAD-vinduer før oppdatering. Start makroen på nytt etterpå.')
    note.setWordWrap(True)
    layout.addRow(note)
    def action(fn):
        try:
            if not target.text().strip():
                raise ValueError('Velg en makromappe.')
            result = fn()
            refresh()
            QtWidgets.QMessageBox.information(dialog, 'Ferdig', 'Aktiv versjon: ' + result['version'] + '\nKjør Klargjor_pa_Z1 fra Makro → Makroer.')
        except Exception as exc:
            QtWidgets.QMessageBox.critical(dialog, 'Installasjonen kunne ikke fullføres', str(exc))
    update = QtWidgets.QPushButton('Installer / oppdater')
    update.clicked.connect(lambda: action(lambda: install(source, target.text())))
    back = QtWidgets.QPushButton('Gå tilbake til forrige versjon')
    back.clicked.connect(lambda: action(lambda: rollback(target.text())))
    close = QtWidgets.QPushButton('Lukk')
    close.clicked.connect(dialog.accept)
    layout.addRow(update)
    layout.addRow(back)
    layout.addRow(close)
    dialog.exec_()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--macro-dir', required=True)
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    result = rollback(args.macro_dir) if args.rollback else install(Path(__file__).parent, args.macro_dir)
    print(json.dumps(result, indent=2))
