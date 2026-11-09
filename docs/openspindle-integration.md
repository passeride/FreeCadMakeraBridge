# OpenSpindle integration: delivery status

This PR realizes the first local handoff milestone of the design vision.
It does not implement OpenSpindle's future machine panel or claim physical
validation. The Community inbox callback defects are in a different repository
and remain a prerequisite for using that receiver; this new path bypasses it.

| Design capability | Status |
|---|---|
| One command to export and request opening | Implemented: new FreeCAD macro |
| Recompute/error gate | Implemented, conservative document-wide gate |
| Immutable export, source ID, program hash, local operation metadata | Implemented |
| OS-level open without shell interpolation | Implemented; mocked Windows/macOS tests |
| Honest handoff status and recoverable launch failure | Implemented |
| Import acknowledgement, paired local API | Future OpenSpindle adapter work |
| Updating existing operations from FreeCAD | Future; current import can create another plate/operation |
| Tool identification | FreeCAD tool descriptors can match cutters already in the OpenSpindle library |
| Stock, WCS and fixture geometry | Configure and inspect in OpenSpindle |
| Post version verification and machine capability binding | Future; current guard checks configured post name only |
| Machine panel, collision verification, job history | Future; controlled by receiver implementation |
| Physical machine validation | Required; not performed |

## Manual acceptance before using on a machine

1. Install via Addon Manager or the complete standalone ZIP. Restart FreeCAD,
   select CAM, and click **Klargjør på Z1** on the Makera Bridge toolbar.
2. Use a Machine-based CAM Job with the intended Makera post. Include profile
   tabs, a pocket, drilling and multiple tools in representative test jobs.
3. Run the new macro with opening disabled. Compare the executable NC blocks
   against the normal post export, including tabs and tool changes. Inspect
   handoff.json and verify the byte count and SHA-256. The source ID property
   makes the document modified.
4. Export the same job twice: distinct folders, identical program hash. Modify
   a toolpath and export again: the program hash must change.
5. Select a compatible OpenSpindle build. Verify cold launch and an already
   running instance on Windows. On macOS enter the .app path. Import must show
   the intended file. A custom CAM job label names the file. For a default Job
   label the file uses the document name and, for a single active operation,
   its label. The macro reports when it has requested opening the file.
6. Try a missing executable before export: Find installation, Open download page,
   Export only and Cancel must be offered. Cancel (or closing the prompt) must
   create no export/source property. Download opens the official page only and
   returns to the choice; it must not imply installation. Canceling the file
   picker also returns to the choice. Export only must produce an NC snapshot
   without trying to start OpenSpindle. Also test a launch failure after export:
   the saved path remains available for manual import.
7. In OpenSpindle check stock, work origin, tool assignment and the exact NC.
   Unknown or omitted movements in a preview must be investigated. Do not infer
   validation of machine geometry from the local manifest's existence.
8. First exercise the receiver with its simulator. Hardware acceptance must
   separately record FreeCAD, post, receiver and firmware versions and results
   for start, tool changes, pause/resume, stop and disconnect. No hardware test
   has been performed for this PR.

## Integration boundary

The bridge's handoff.json is schema freecad-openspindle-handoff/1. Status is
always exported_locally; it must not be used to authorize machining. Program
revision covers NC bytes only. Operation names have no NC line mapping yet.
The export keeps native Makera FreeCAD tool descriptors. If the post emits none,
the addon adds `@FC|TOOL` comments from the tool controllers of active operations.
OpenSpindle can match supported cutters with compatible geometry in its active
library. Review the assigned tools before running a job. Missing, incompatible
or ambiguous cutters need a manual assignment.
No stock/WCS comments are injected because coordinates cannot safely be inferred
from an arbitrary document-space bounding box. Future geometry transfer must
explicitly transform to the Job's postprocessor coordinate system.

The existing Fusion pairing service runs in Fusion and is queried by OpenSpindle;
it is not a generic NC upload endpoint. A future FreeCAD adapter should negotiate
capabilities and confirm the imported revision before showing an Imported badge.
It must bind replies to source/revision/session and never replay machine start.
