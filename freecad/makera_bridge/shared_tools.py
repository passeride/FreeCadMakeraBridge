"""Versioned, portable cutter geometry. Machine T slots are deliberately local."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import uuid

SCHEMA = "openspindle-shared-tools/1"
KINDS = {"EndMill": "flat", "BallEnd": "ball", "VBit": "v-bit", "Drill": "drill"}
SHAPES = {"flat": ("endmill.fcstd", "EndMill"), "ball": ("ballend.fcstd", "BallEnd"),
          "v-bit": ("v-bit.fcstd", "VBit"), "drill": ("drill.fcstd", "Drill")}


def validate_entry(entry):
    uuid.UUID(entry["id"])
    if len(entry.get("revision", "")) != 64 or any(c not in "0123456789abcdef" for c in entry["revision"]):
        raise ValueError("Ugyldig verktøyrevisjon.")
    if entry.get("kind") not in SHAPES or not isinstance(entry.get("name"), str) or not 0 < len(entry["name"]) <= 200:
        raise ValueError("Ustøttet verktøytype eller navn.")
    for key, maximum in (("diameter", 1000), ("shankDiameter", 1000), ("fluteLength", 10000), ("overallLength", 10000)):
        value = entry.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError("Verktøyet mangler gyldig " + key)
    flutes = entry.get("flutes")
    if isinstance(flutes, bool) or not isinstance(flutes, int) or not 1 <= flutes <= 100:
        raise ValueError("Ugyldig antall skjær.")
    for key, maximum in (("tipDiameter", 1000), ("pointAngle", 180)):
        value = entry.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > maximum):
            raise ValueError("Ugyldig " + key)
    if entry["kind"] == "v-bit" and (entry.get("tipDiameter") is None or not entry.get("pointAngle")):
        raise ValueError("V-bits må ha spissdiameter og full spissvinkel.")
    if entry["fluteLength"] > entry["overallLength"] or (entry.get("tipDiameter") or 0) > entry["diameter"]:
        raise ValueError("Verktøydimensjonene stemmer ikke overens.")
    for key in ("manufacturer", "productId"):
        if entry.get(key) is not None and (not isinstance(entry[key], str) or len(entry[key]) > 200):
            raise ValueError("Ugyldig " + key)
    return entry


def read_library(path):
    path = Path(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Biblioteket overskrider 16 MiB.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or data.get("units") != "mm":
        raise ValueError("Ukjent bibliotekformat eller enhet.")
    tools = data.get("tools")
    if not isinstance(tools, list) or len(tools) > 10000:
        raise ValueError("Ugyldig verktøyliste.")
    for tool in tools:
        validate_entry(tool)
    if len({tool["id"] for tool in tools}) != len(tools):
        raise ValueError("Dupliserte verktøy-ID-er.")
    return tools


def install_library(entries, destination):
    """Create an immutable new library revision; loaded CAM tools are never replaced."""
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="OpenSpindle-", dir=destination))
    try:
        bits = root / "Bit"
        libraries = root / "Library"
        bits.mkdir()
        libraries.mkdir()
        library = {"version": 1, "label": "OpenSpindle shared tools", "tools": []}
        for index, entry in enumerate(entries):
            validate_entry(entry)
            shape, shape_type = SHAPES[entry["kind"]]
            parameters = {"Diameter": f'{entry["diameter"]} mm', "ShankDiameter": f'{entry["shankDiameter"]} mm',
                          "CuttingEdgeHeight": f'{entry["fluteLength"]} mm', "Length": f'{entry["overallLength"]} mm', "Units": "Metric"}
            if entry["tipDiameter"] is not None:
                parameters["TipDiameter"] = f'{entry["tipDiameter"]} mm'
            if entry["pointAngle"] is not None:
                key = "CuttingEdgeAngle" if entry["kind"] == "v-bit" else "TipAngle"
                parameters[key] = f'{entry["pointAngle"]} °'
            bit = {"version": 2, "name": entry["name"], "shape": shape, "shape-type": shape_type,
                   "parameter": parameters, "attribute": {"Flutes": str(entry["flutes"]),
                   "OpenSpindleSharedId": entry["id"], "OpenSpindleSharedRevision": entry["revision"],
                   "OpenSpindleSharedEntry": json.dumps(entry, ensure_ascii=False, separators=(",", ":"))}}
            name = entry["id"] + ".fctb"
            (bits / name).write_text(json.dumps(bit, ensure_ascii=False, indent=2), encoding="utf-8")
            library["tools"].append({"nr": index + 1, "path": name})
        target = libraries / "OpenSpindle.fctl"
        target.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
    except Exception:
        import shutil
        shutil.rmtree(root)
        raise


def _value(tool, name):
    value = getattr(tool, name, None)
    return getattr(value, "Value", value)


def from_controller(controller):
    tool = controller.Tool
    kind = KINDS.get(str(getattr(tool, "ShapeType", "")))
    if kind is None:
        raise ValueError(tool.Label + ": ustøttet form " + str(getattr(tool, "ShapeType", "")))
    identity = str(getattr(tool, "OpenSpindleSharedId", "")) or str(uuid.uuid4())
    entry = {"id": identity, "name": tool.Label, "kind": kind,
             "diameter": _value(tool, "Diameter"), "shankDiameter": _value(tool, "ShankDiameter"),
             "fluteLength": _value(tool, "CuttingEdgeHeight"), "overallLength": _value(tool, "Length"),
             "flutes": int(_value(tool, "Flutes") or 0),
             "tipDiameter": _value(tool, "TipDiameter") if kind == "v-bit" else None,
             "pointAngle": None, "manufacturer": None, "productId": None}
    if kind == "v-bit":
        entry["pointAngle"] = _value(tool, "CuttingEdgeAngle")
    elif kind == "drill":
        entry["pointAngle"] = _value(tool, "TipAngle")
    try:
        previous = json.loads(str(getattr(tool, "OpenSpindleSharedEntry", "")))
    except (ValueError, TypeError):
        previous = {}
    entry["manufacturer"] = previous.get("manufacturer")
    entry["productId"] = previous.get("productId")
    before = {key: value for key, value in previous.items() if key != "revision"}
    if before == entry:
        entry["revision"] = previous["revision"]
    else:
        entry["revision"] = hashlib.sha256(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    validate_entry(entry)
    for name, value in (("OpenSpindleSharedId", identity), ("OpenSpindleSharedRevision", entry["revision"]),
                        ("OpenSpindleSharedEntry", json.dumps(entry, ensure_ascii=False, separators=(",", ":")))):
        if name not in tool.PropertiesList:
            tool.addProperty("App::PropertyString", name, "OpenSpindle")
        setattr(tool, name, value)
    return entry


class SharedToolsCommand:
    def GetResources(self):
        return {"Pixmap": "CAM_ToolLibraryEdit", "MenuText": "Felles OpenSpindle-verktøy",
                "ToolTip": "Importer et nytt bibliotek eller eksporter verktøyene fra CAM-jobben"}

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCAD as App
        import FreeCADGui as Gui
        from PySide import QtWidgets
        from .commands import get_job
        parent = Gui.getMainWindow()
        try:
            action, ok = QtWidgets.QInputDialog.getItem(parent, "Felles verktøybibliotek", "Handling", ["Importer fra OpenSpindle", "Eksporter jobbens verktøy", "Importer fra vert", "Publiser jobbens verktøy til vert"], 0, False)
            if not ok:
                return
            if "vert" in action:
                from .remote import settings, request
                from .commands import preferences
                address, key = settings(preferences())
                remote, etag = request(address, key, "/api/tools")
                if remote.get("schema") != SCHEMA or remote.get("units") != "mm" or not isinstance(remote.get("tools"), list) or len(remote["tools"]) > 10000:
                    raise ValueError("Ukjent bibliotekformat fra verten.")
                for tool in remote["tools"]:
                    validate_entry(tool)
                if action.startswith("Importer"):
                    destination = QtWidgets.QFileDialog.getExistingDirectory(parent, "Velg mappe for ny biblioteksrevisjon")
                    if not destination:
                        return
                    target = install_library(remote["tools"], destination)
                    QtWidgets.QMessageBox.information(parent, "Felles verktøy", "Legg til biblioteket i FreeCAD:\n" + str(target))
                    return
                job = get_job(App.ActiveDocument, Gui.Selection.getSelection())
                merged = {tool["id"]: tool for tool in remote["tools"]}
                for controller in job.Tools.Group:
                    entry = from_controller(controller)
                    previous = merged.get(entry["id"])
                    if previous and previous != entry:
                        answer = QtWidgets.QMessageBox.question(parent, "Endret verktøy", "Erstatt vertsdefinisjonen for " + entry["name"] + "?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
                        if answer != QtWidgets.QMessageBox.Yes:
                            continue
                    merged[entry["id"]] = entry
                payload = json.dumps({"schema": SCHEMA, "units": "mm", "tools": list(merged.values())}, ensure_ascii=False, separators=(",", ":")).encode()
                request(address, key, "/api/tools", "PUT", payload, etag)
                return
            if action.startswith("Importer"):
                source, _ = QtWidgets.QFileDialog.getOpenFileName(parent, "Velg bibliotek", "", "OpenSpindle (*.osptools)")
                if not source:
                    return
                destination = QtWidgets.QFileDialog.getExistingDirectory(parent, "Velg FreeCAD-verktøymappe for en ny biblioteksrevisjon")
                if not destination:
                    return
                target = install_library(read_library(source), destination)
                QtWidgets.QMessageBox.information(parent, "Felles verktøy", "Nytt bibliotek er lagret. Legg til denne mappen i FreeCADs verktøybibliotek:\n" + str(target))
            else:
                if App.ActiveDocument is None:
                    raise ValueError("Åpne en CAM-jobb først.")
                job = get_job(App.ActiveDocument, Gui.Selection.getSelection())
                entries = []
                failures = []
                for controller in job.Tools.Group:
                    try:
                        entry = from_controller(controller)
                        if not any(item["id"] == entry["id"] for item in entries):
                            entries.append(entry)
                    except (ValueError, AttributeError, TypeError) as exc:
                        failures.append(str(exc))
                if not entries:
                    raise ValueError("Ingen støttede verktøy.\n" + "\n".join(failures))
                destination, _ = QtWidgets.QFileDialog.getSaveFileName(parent, "Eksporter bibliotek", "OpenSpindle.osptools", "OpenSpindle (*.osptools)")
                if not destination:
                    return
                if not destination.lower().endswith(".osptools"):
                    destination += ".osptools"
                from .commands import atomic_text
                atomic_text(Path(destination), json.dumps({"schema": SCHEMA, "units": "mm", "tools": entries}, ensure_ascii=False, indent=2))
                if failures:
                    QtWidgets.QMessageBox.warning(parent, "Ikke eksportert", "\n".join(failures))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(parent, "Felles verktøybibliotek", str(exc))
