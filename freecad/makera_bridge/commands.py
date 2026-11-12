"""CAM command and local OpenSpindle handoff. Imports only the standard library at startup."""
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import uuid

MAX_BYTES = 10 * 1024 * 1024
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Macro/SendToOpenSpindle"


def validate_nc(gcode):
    if not isinstance(gcode, str) or not gcode.strip():
        raise ValueError("Ingen G-kode ble generert.")
    data = gcode.encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("OpenSpindle-programmet overskrider 10 MiB.")
    # Comments alone must not make an empty program look like a toolpath.
    code = re.sub(r"\([^)]*\)|;[^\n]*", "", gcode)
    if not re.search(r"(?<![A-Z])G0?[0123](?![\d.])", code, re.I):
        raise ValueError("Fant ingen G0/G1/G2/G3-bevegelser.")
    return data


def export_label(source):
    job = source["job_label"].strip()
    document = source.get("document_label", "").strip()
    operations = source.get("operations", [])
    operation = operations[0]["label"].strip() if len(operations) == 1 else ""
    if source.get("scope") == "operation" and operation:
        return operation
    if job and not re.fullmatch(r"Job(?:\s*\(?\d+\)?)?", job, re.I):
        return job
    if document and operation and document.casefold() != operation.casefold():
        return f"{document} - {operation}"
    return document or operation or "CAM"


def publish(folder, gcode, source, reference=None):
    """Publish a complete snapshot directory atomically."""
    data = validate_nc(gcode)
    base = Path(folder).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    revision = hashlib.sha256(data).hexdigest()
    label = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", export_label(source))
    label = label[:50].strip(" ._-") or "CAM"
    if re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", label, re.I):
        label = "_" + label
    snapshot_id = uuid.uuid4().hex
    staging = Path(tempfile.mkdtemp(prefix=".export-", dir=base))
    final = base / (label + "_" + revision[:12] + "_" + snapshot_id[:8])
    manifest = {
        "schema": "freecad-openspindle-handoff/1",
        "snapshot_id": snapshot_id,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": source,
        "program": {"filename": label + ".nc", "sha256": revision, "bytes": len(data)},
        "status": "exported_locally",
        "verification": {"machine": "not_checked", "setup": "not_checked", "collision": "not_checked"},
    }
    try:
        (staging / (label + ".nc")).write_bytes(data)
        if reference is not None:
            model, stock, material = reference
            bundle = {"schema": "freecad-openspindle-job/1",
                      "program": {"name": label + ".nc", "nc": gcode, "sha256": revision},
                      "reference": model, "stock": stock, "material": material}
            encoded = json.dumps(bundle, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            if len(encoded) > 64 * 1024 * 1024:
                raise ValueError("Modellpakken overskrider 64 MiB.")
            (staging / (label + ".ospjob")).write_bytes(encoded)
            manifest["display_bundle"] = {"filename": label + ".ospjob", "bytes": len(encoded),
                                          "sha256": hashlib.sha256(encoded).hexdigest()}
        (staging / "handoff.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.rename(staging, final)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return final / (label + (".ospjob" if reference is not None else ".nc")), manifest


DOWNLOAD_URL = "https://github.com/openspindle/openspindle/releases"


def receiver_path(executable, platform=None):
    """Check local availability only, not app identity/version or import support."""
    platform = platform or sys.platform
    if not str(executable).strip():
        raise ValueError("OpenSpindle er ikke konfigurert.")
    app = Path(executable).expanduser().resolve()
    if platform == "darwin" and app.suffix.lower() == ".app" and app.is_dir():
        if not (app/'Contents'/'MacOS').is_dir():
            raise ValueError("Velg en gyldig OpenSpindle.app-pakke.")
        return app
    if not app.is_file() or (platform != 'win32' and not os.access(app, os.X_OK)):
        raise ValueError("OpenSpindle-programfilen finnes ikke eller kan ikke kjøres.")
    return app


def discover_receiver(platform=None, environ=None):
    platform = platform or sys.platform
    environ = os.environ if environ is None else environ
    candidates = []
    if platform == 'win32':
        for key, suffix in [('LOCALAPPDATA', 'Programs/openspindle/OpenSpindle.exe'),
                            ('PROGRAMFILES', 'OpenSpindle/OpenSpindle.exe')]:
            if environ.get(key):
                candidates.append(Path(environ[key])/suffix)
    elif platform == 'darwin':
        candidates = [Path('/Applications/OpenSpindle.app'), Path.home()/'Applications/OpenSpindle.app']
    for name in ('openspindle', 'OpenSpindle'):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        try:
            return str(receiver_path(candidate, platform))
        except ValueError:
            pass
    return ''


def configure_receiver(executable, opening, decide, find, download, platform=None):
    """Resolve a missing receiver before export; None means no export allowed.

    Callbacks keep UI separate and never install software or start a machine.
    """
    if not opening:
        return executable, False
    while True:
        try:
            return str(receiver_path(executable, platform)), True
        except ValueError as exc:
            action = decide(str(exc))
        if action == 'export':
            return executable, False
        if action == 'find':
            executable = find() or executable
        elif action == 'download':
            download(DOWNLOAD_URL)
        else:
            return None


def launch(executable, nc_path, platform=None, popen=subprocess.Popen):
    """Ask the app to open one NC file; launch is not an import acknowledgement."""
    platform = platform or sys.platform
    app = receiver_path(executable, platform)
    nc = Path(nc_path).resolve(strict=True)
    if nc.suffix.lower() not in (".nc", ".ospjob"):
        raise ValueError("Velg en .nc- eller .ospjob-fil.")
    if platform == "darwin" and app.suffix.lower() == ".app":
        args = ["/usr/bin/open", "-a", str(app), str(nc)]
    else:
        args = [str(app), str(nc)]
    return popen(args, shell=False)


def check_job(job):
    """Recompute and reject document errors before requesting post output."""
    job.Document.recompute()
    invalid = [obj.Label for obj in job.Document.Objects
               if set(getattr(obj, "State", [])) & {"Invalid", "Error", "Touched"}]
    if invalid:
        raise ValueError("Dokumentet har feil eller uoppdaterte objekter: " + ", ".join(invalid))


def with_tool_comments(gcode, controllers):
    """Keep native Makera descriptors and supply the same format for older posts."""
    if re.search(r"^\s*(?:\(|;)\s*@FC\|TOOL\|", gcode, re.I | re.M):
        return gcode
    comments = {}
    for controller in controllers:
        number = getattr(controller, "ToolNumber", None)
        tool = getattr(controller, "Tool", None)
        if tool is None or not isinstance(number, int) or not 0 < number <= 999999:
            continue
        # These are FreeCAD's internal units. They do not depend on G20/G21.
        shape = re.sub(r"[^a-zA-Z0-9_-]", "", str(getattr(tool, "ShapeType", "")))
        fields = [f"number={number}", "unit=mm", f"type={shape or 'unknown'}"]
        name = re.sub(r"[\x00-\x1f\x7f()|;]", " ", str(tool.Label))[:120].strip()
        if name:
            fields.append(f"name={name}")
        for key, properties in (("diameter", ("Diameter",)), ("tipdiameter", ("TipDiameter",)),
                                ("tipangle", ("TipAngle",)), ("cuttingedgeangle", ("CuttingEdgeAngle",)),
                                ("flutelength", ("CuttingEdgeHeight", "CuttingEdgeLength"))):
            quantity = next((getattr(tool, prop) for prop in properties if hasattr(tool, prop)), None)
            value = getattr(quantity, "Value", quantity)
            if isinstance(value, (float, int)) and math.isfinite(value):
                fields.append(f"{key}={value:.9g}")
        comments["(@FC|TOOL|" + "|".join(fields) + ")"] = None
    if not comments:
        return gcode
    newline = "\r\n" if "\r\n" in gcode else "\n"
    # Keep a leading delimiter first for posts that use one.
    first, separator, rest = gcode.partition(newline)
    header = newline.join(comments) + newline
    if first.strip() == "%" and separator:
        return first + separator + header + rest
    return header + gcode


def source_metadata(job, postprocessor, freecad_version, operations):
    # This property is saved with the CAM Job. Copying a job must give a new ID.
    if "OpenSpindleSourceId" not in job.PropertiesList:
        job.addProperty("App::PropertyString", "OpenSpindleSourceId", "OpenSpindle",
                        "Persistent source identity for local handoff")
    if not job.OpenSpindleSourceId:
        job.OpenSpindleSourceId = uuid.uuid4().hex
    peers = [o for o in job.Document.Objects if o is not job
             and getattr(o, "OpenSpindleSourceId", None) == job.OpenSpindleSourceId]
    if peers:
        job.OpenSpindleSourceId = uuid.uuid4().hex
    return {
        "id": job.OpenSpindleSourceId, "document_label": job.Document.Label,
        "job_name": job.Name, "job_label": job.Label,
        "document_saved": bool(job.Document.FileName),
        "freecad_version": list(freecad_version), "postprocessor": postprocessor,
        "operations": [{"name": o.Name, "label": o.Label}
                       for o in operations],
    }


def cam_jobs(doc):
    return [obj for obj in doc.Objects if hasattr(obj, "Operations") and hasattr(obj, "Machine")]


def operation_owner(jobs, operation):
    return next((job for job in jobs if operation in job.Operations.Group), None)


def get_job(doc, selection):
    jobs = cam_jobs(doc)
    if selection:
        selected = selection[0]
        if selected in jobs:
            return selected
        owner = operation_owner(jobs, selected)
        if owner is not None:
            return owner
    if len(jobs) == 1:
        return jobs[0]
    if not jobs:
        raise RuntimeError("Fant ingen Machine-basert CAM-jobb i dokumentet.")
    raise RuntimeError("Velg riktig CAM-jobb i modelltreet (flere jobber funnet).")


def selected_operation(doc, selection, is_active):
    if doc is None or len(selection) != 1:
        return None
    operation = selection[0]
    job = operation_owner(cam_jobs(doc), operation)
    if job is None or not is_active(operation):
        return None
    return job, operation


_NC_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
_Z1_TOOL_CHANGE = re.compile(r"(?:T\d+\s+M0*6|M0*6\s+T\d+)")
_Z1_SPINDLE_START = re.compile(rf"M0*3(?:\s+S{_NC_NUMBER})?")
_Z1_APPROACH_MODES = r"G(?:17|21|54|90|94)(?:\s+G(?:17|21|54|90|94))*"
_Z1_APPROACH_SETUP = re.compile(
    rf"(?:M0*[345789](?:\s+S{_NC_NUMBER})?|S{_NC_NUMBER}|{_Z1_APPROACH_MODES})"
)
_Z1_APPROACH_Z = re.compile(rf"G0+\s+Z(?P<z>{_NC_NUMBER})")
_Z1_APPROACH_XY = re.compile(
    rf"G0+\s+X(?P<x>{_NC_NUMBER})\s+Y(?P<y>{_NC_NUMBER})"
    rf"(?:\s+Z(?P<z>{_NC_NUMBER}))?"
)
_Z1_MACHINE_XY = re.compile(rf"G53\s+G0+\s+X({_NC_NUMBER})\s+Y({_NC_NUMBER})")


def _z1_center_script(blocks):
    if len(blocks) != 5 or blocks[:3] != ["G21 G90", "G53 G0 Z-3", "M400"]:
        return False
    xy = _Z1_MACHINE_XY.fullmatch(blocks[3])
    return (
        xy is not None
        and all(-200 <= float(axis) <= -1 for axis in xy.groups())
        and blocks[4] == "M400"
    )


def z1_clearance_retract(gcode):
    """Keep a recognized tool approach at machine clearance until XY is in position."""
    lines = gcode.splitlines(keepends=True)
    blocks = [re.sub(r"\([^)]*\)|;[^\r\n]*", "", line).strip().upper() for line in lines]
    if any(re.search(r"[ABC]\s*[+\-\d.]", block) for block in blocks):
        return gcode

    metric = absolute = False
    setup_start = None
    at_clearance = False
    for index, block in enumerate(blocks):
        for mode in re.findall(r"G(20|21|90|91)(?![\d.])", block):
            if mode in ("20", "21"):
                metric = mode == "21"
            else:
                absolute = mode == "90"
        if _Z1_TOOL_CHANGE.fullmatch(block):
            setup_start = index + 1
            at_clearance = _z1_center_script(blocks[setup_start:setup_start + 5])
            if at_clearance:
                setup_start += 5
            continue
        if (
            setup_start is None or index < setup_start
            or not block or _Z1_APPROACH_SETUP.fullmatch(block)
        ):
            continue
        setup = [j for j in range(setup_start, index) if blocks[j]]
        setup_start = None
        if not (metric and absolute):
            continue

        # A Z-only rapid followed by XY, or one XYZ rapid, is the post's first approach.
        first_z = _Z1_APPROACH_Z.fullmatch(lines[index].strip().upper())
        xy_index = index
        if first_z:
            xy_index = next(
                (j for j in range(index + 1, len(blocks)) if blocks[j]), len(blocks)
            )
            if xy_index == len(blocks):
                continue
        xy = _Z1_APPROACH_XY.fullmatch(lines[xy_index].strip().upper())
        if not xy:
            continue

        newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
        retract = "" if at_clearance else newline.join(("G53 G0 Z-3", "M400", ""))
        z = xy["z"]
        if first_z and z is None:
            z = first_z["z"]
        if z is None or (first_z and float(first_z["z"]) != float(z)):
            lines[index] = retract + lines[index]
            continue

        traverse = newline.join((f'G0 X{xy["x"]} Y{xy["y"]}', "M400", ""))
        # Move the post's standalone M3 past the traverse. Only move it across
        # modal setup and comments, so auxiliary and spindle command order stays intact.
        if setup and _Z1_SPINDLE_START.fullmatch(blocks[setup[0]]) and all(
            re.fullmatch(_Z1_APPROACH_MODES, blocks[j]) for j in setup[1:]
        ):
            traverse += lines[setup[0]]
            lines[setup[0]] = ""
        traverse += f"G0 Z{z}"
        if lines[xy_index].endswith(("\r", "\n")):
            traverse += newline
        if first_z:
            lines[index] = retract
            lines[xy_index] = traverse
        else:
            lines[index] = retract + traverse
    return "".join(lines)


def postprocess(job, operations=None):
    from Path.Post.Processor import PostProcessorFactory
    from Machine.models.machine import MachineFactory
    machine = MachineFactory.get_machine(job.Machine)
    if machine is None:
        raise RuntimeError("Ingen gyldig CAM Machine er valgt.")
    name = machine.postprocessor_file_name
    if not name:
        raise RuntimeError("CAM Machine mangler valgt postprosessor.")
    if not any(s in name.lower() for s in ("makera", "z1", "carvera")):
        raise RuntimeError("Postprosessoren '%s' ser ikke ut som en Makera-postprosessor." % name)
    if operations is not None and not operations:
        raise ValueError("Ingen CAM-operasjon er valgt for eksport.")
    # The same filtered job argument FreeCAD uses for Post Selected. An empty
    # selection would make its post fall back to the entire job.
    job_arg = job if operations is None else {"job": job, "operations": operations}
    post = PostProcessorFactory.get_post_processor(job_arg, name)
    if post is None or not hasattr(post, "export2"):
        raise RuntimeError("Machine-postprosessoren '%s' er ikke tilgjengelig." % name)
    # The unified FreeCAD dialog applies the bundle before export2. The base
    # post may initialize toolhead limits to None when the machine omits them,
    # even when the Makera post declares a numeric minimum in its own schema.
    apply_bundle = getattr(post, "apply_configuration_bundle", None)
    if callable(apply_bundle):
        post._machine = machine
        apply_bundle()
        for property_name in ("min_spindle_speed", "min_feed_rate"):
            if property_name not in machine.postprocessor_properties:
                continue
            key = property_name.upper()
            if post.values.get(key) is not None:
                continue
            value = machine.postprocessor_properties[property_name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"Postprosessorens {property_name} må være et gyldig tall.")
            post.values[key] = value
        post._bundle_applied = True
    result = post.export2()
    if not result:
        raise RuntimeError("Postprosessoren returnerte ingen G-kode.")
    if not isinstance(result, (tuple, list)) or len(result) != 1:
        raise RuntimeError("Velg samlet utdata i CAM-jobben før eksport.")
    section = result[0]
    if not isinstance(section, (tuple, list)) or len(section) != 2:
        raise RuntimeError("Ukjent svar fra FreeCAD-postprosessoren.")
    gcode = section[1]
    if isinstance(gcode, str) and name.casefold() in ("makera_z1_named", "makera_z1"):
        gcode = z1_clearance_retract(gcode)
    validate_nc(gcode)
    return gcode, name


def preferences():
    import FreeCAD as App
    return App.ParamGet(PREFERENCES_PATH)


def default_export_folder():
    return str(Path.home() / "Documents" / "FreeCAD-OpenSpindle")


def browse_receiver(parent):
    from PySide import QtWidgets
    if sys.platform == "darwin":
        return QtWidgets.QFileDialog.getExistingDirectory(parent, "Velg OpenSpindle.app")
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, "Velg OpenSpindle-programfil")
    return path


def resolve_receiver(executable, parent):
    from PySide import QtCore, QtGui, QtWidgets

    def decide(reason):
        prompt = QtWidgets.QMessageBox(parent)
        prompt.setWindowTitle("OpenSpindle er ikke tilgjengelig")
        prompt.setText(reason)
        prompt.setInformativeText("Finn installasjonen, åpne nedlastingssiden eller lagre bare NC-filen.")
        find = prompt.addButton("Finn OpenSpindle…", QtWidgets.QMessageBox.ActionRole)
        download = prompt.addButton("Åpne nedlastingsside", QtWidgets.QMessageBox.ActionRole)
        export = prompt.addButton("Eksporter bare fil", QtWidgets.QMessageBox.AcceptRole)
        prompt.addButton(QtWidgets.QMessageBox.Cancel)
        prompt.exec_()
        return {find: "find", download: "download", export: "export"}.get(
            prompt.clickedButton(), "cancel"
        )

    def download(url):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
            QtWidgets.QMessageBox.warning(parent, "OpenSpindle", "Kunne ikke åpne " + url)

    return configure_receiver(
        executable, True, decide, lambda: discover_receiver() or browse_receiver(parent), download
    )


def run(operation_only=False):
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui, QtWidgets

    title = "Send operasjon til OpenSpindle" if operation_only else "Send jobb til OpenSpindle"
    parent = Gui.getMainWindow()
    try:
        from Path.Base import Util as PathUtil
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("Åpne et dokument med CAM-jobb først.")
        selection = Gui.Selection.getSelection()
        operation = None
        if operation_only:
            selected = selected_operation(doc, selection, PathUtil.activeForOp)
            if selected is None:
                raise RuntimeError("Velg én aktiv operasjon under CAM-jobben.")
            job, operation = selected
        else:
            job = get_job(doc, selection)

        prefs = preferences()
        saved_executable = prefs.GetString("Executable", "").strip()
        receiver = resolve_receiver(saved_executable, parent)
        if receiver is None:
            return
        executable, should_open = receiver
        if should_open and executable != saved_executable:
            prefs.SetString("Executable", executable)
        folder = prefs.GetString("Exports", "").strip() or default_export_folder()

        check_job(job)
        operations = [op for op in job.Operations.Group if PathUtil.activeForOp(op)]
        if operation_only:
            if operation not in operations:
                raise RuntimeError("Den valgte operasjonen er ikke lenger aktiv i CAM-jobben.")
            operations = [operation]
        gcode, post = postprocess(job, operations) if operation_only else postprocess(job)
        check_job(job)
        source = source_metadata(job, post, App.Version(), operations)
        source["scope"] = "operation" if operation_only else "job"
        controllers = (PathUtil.toolControllerForOp(op) for op in operations)
        from .reference import export_reference
        reference = export_reference(job)
        path, _ = publish(folder, with_tool_comments(gcode, controllers), source, reference)
        if should_open:
            try:
                launch(executable, path)
            except (OSError, ValueError) as exc:
                raise RuntimeError(f"Kunne ikke åpne OpenSpindle: {exc}\nÅpne filen manuelt: {path}") from exc
        elif not QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path.parent))):
            QtWidgets.QMessageBox.warning(parent, title, f"Filen er lagret her: {path}")
    except Exception as exc:
        App.Console.PrintError("OpenSpindle: " + traceback.format_exc())
        QtWidgets.QMessageBox.critical(parent, title, str(exc))


class OpenSpindlePreferences:
    def __init__(self, parent=None):
        from PySide import QtWidgets
        self.form = QtWidgets.QWidget(parent)
        self.form.setWindowTitle("OpenSpindle")
        layout = QtWidgets.QFormLayout(self.form)
        self.executable = QtWidgets.QLineEdit()
        self.folder = QtWidgets.QLineEdit()
        for label, field, pick in (
            ("OpenSpindle-program", self.executable, lambda: browse_receiver(self.form)),
            ("Eksportmappe", self.folder, lambda: QtWidgets.QFileDialog.getExistingDirectory(
                self.form, "Velg eksportmappe", self.folder.text()
            )),
        ):
            row = QtWidgets.QHBoxLayout()
            button = QtWidgets.QPushButton("Bla gjennom…")
            button.clicked.connect(lambda checked=False, edit=field, choose=pick: self.browse(edit, choose))
            row.addWidget(field)
            row.addWidget(button)
            layout.addRow(label, row)

    @staticmethod
    def browse(field, choose):
        path = choose()
        if path:
            field.setText(path)

    def loadSettings(self):
        prefs = preferences()
        self.executable.setText(prefs.GetString("Executable", ""))
        self.folder.setText(prefs.GetString("Exports", "") or default_export_folder())

    def saveSettings(self):
        prefs = preferences()
        prefs.SetString("Executable", self.executable.text().strip())
        prefs.SetString("Exports", self.folder.text().strip())


def command_icon(name):
    resources = Path(__file__).parent / "resources"
    icon = resources / name
    return str(icon if icon.is_file() else resources / "bridge.svg")


class PrepareCommand:
    def GetResources(self):
        return {"Pixmap": command_icon("send-job.svg"),
                "MenuText": "Send jobb til OpenSpindle",
                "ToolTip": "Eksporter hele CAM-jobben og åpne den i OpenSpindle"}

    def IsActive(self):
        import FreeCAD as App
        return App.ActiveDocument is not None

    def Activated(self):
        run()


class SendOperationCommand:
    def GetResources(self):
        return {"Pixmap": command_icon("send-operation.svg"),
                "MenuText": "Send operasjon til OpenSpindle",
                "ToolTip": "Eksporter én valgt, aktiv CAM-operasjon og åpne den i OpenSpindle"}

    def IsActive(self):
        import FreeCAD as App
        import FreeCADGui as Gui
        if App.ActiveDocument is None:
            return False
        from Path.Base import Util as PathUtil
        return selected_operation(App.ActiveDocument, Gui.Selection.getSelection(), PathUtil.activeForOp) is not None

    def Activated(self):
        run(operation_only=True)


def register():
    import FreeCADGui as Gui
    Gui.addCommand("MakeraBridge_Prepare", PrepareCommand())
    Gui.addCommand("MakeraBridge_SendOperation", SendOperationCommand())
    Gui.addPreferencePage(OpenSpindlePreferences, "Makera Bridge")
