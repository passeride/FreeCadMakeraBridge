"""Local, immutable NC handoff. No machine connection or execution commands."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

MAX_BYTES = 10 * 1024 * 1024


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


def publish(folder, gcode, source):
    """Publish a complete snapshot directory atomically; preserve NC bytes."""
    data = validate_nc(gcode)
    base = Path(folder).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    revision = hashlib.sha256(data).hexdigest()
    label = re.sub(r"[^a-zA-Z0-9_.-]+", "_", source["job_label"]).strip("._-")[:50] or "Job"
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
        (staging / "handoff.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.rename(staging, final)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return final / (label + ".nc"), manifest


def launch(executable, nc_path, platform=None, popen=subprocess.Popen):
    """Ask the app to open one NC file, without a shell or run flags.

    Process launch is not an import acknowledgement. macOS bundles use `open`.
    """
    platform = platform or sys.platform
    app = Path(executable).expanduser().resolve()
    nc = Path(nc_path).resolve(strict=True)
    if nc.suffix.lower() != ".nc":
        raise ValueError("Velg en .nc-fil.")
    if platform == "darwin" and app.suffix.lower() == ".app" and app.is_dir():
        args = ["/usr/bin/open", "-a", str(app), str(nc)]
    else:
        if not app.is_file():
            raise ValueError("Velg OpenSpindle-programfilen først.")
        args = [str(app), str(nc)]
    return popen(args, shell=False)


def check_job(job):
    """Recompute and reject document errors before requesting post output."""
    job.Document.recompute()
    invalid = [obj.Label for obj in job.Document.Objects
               if set(getattr(obj, "State", [])) & {"Invalid", "Error", "Touched"}]
    if invalid:
        raise ValueError("Dokumentet har feil eller uoppdaterte objekter: " + ", ".join(invalid))


def source_metadata(job, postprocessor, freecad_version):
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
                       for o in job.Operations.Group],
    }
