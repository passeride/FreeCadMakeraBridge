"""FreeCAD CAM selection and Machine postprocessing for the addon."""
from .bridge import validate_nc


def get_job():
    import FreeCAD as App
    import FreeCADGui as Gui
    doc = App.ActiveDocument
    if not doc:
        raise RuntimeError("Åpne et dokument med CAM-jobb først.")
    selected = Gui.Selection.getSelection()
    if selected:
        obj = selected[0]
        if hasattr(obj, "Operations") and hasattr(obj, "Machine"):
            return obj
        try:
            from PathScripts.PathUtils import findParentJob
            job = findParentJob(obj)
            if job:
                return job
        except (ImportError, AttributeError):
            pass
    jobs = [o for o in doc.Objects if hasattr(o, "Operations") and hasattr(o, "Machine")]
    if len(jobs) == 1:
        return jobs[0]
    if not jobs:
        raise RuntimeError("Fant ingen Machine-basert CAM-jobb i dokumentet.")
    raise RuntimeError("Velg riktig CAM-jobb i modelltreet (flere jobber funnet).")


def postprocess(job):
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
    post = PostProcessorFactory.get_post_processor(job, name)
    if post is None or not hasattr(post, "export2"):
        raise RuntimeError("Machine-postprosessoren '%s' er ikke tilgjengelig." % name)
    result = post.export2()
    if not result:
        raise RuntimeError("Postprosessoren returnerte ingen G-kode.")
    if not isinstance(result, (tuple, list)) or len(result) != 1:
        raise RuntimeError("Velg samlet utdata i CAM-jobben før eksport.")
    section = result[0]
    if not isinstance(section, (tuple, list)) or len(section) != 2:
        raise RuntimeError("Ukjent svar fra FreeCAD-postprosessoren.")
    gcode = section[1]
    validate_nc(gcode)
    return gcode, name
