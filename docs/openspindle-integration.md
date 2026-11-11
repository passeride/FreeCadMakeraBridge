# OpenSpindle integration: delivery status

This PR realizes the first local handoff milestone of the design vision.
It does not implement OpenSpindle's future machine panel or claim physical
validation. The Community inbox callback defects are in a different repository
and remain a prerequisite for using that receiver; this new path bypasses it.

| Design capability | Status |
|---|---|
| Direct handoff from CAM | Send a job or one selected operation from the toolbar |
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

## Z1 approach after a tool change

The bundled `makera_z1_bridge` post is used for **Ny Z1-jobb** and can also be
selected through its Machine on an existing three-axis job. In absolute,
metric three-axis output it separates a recognized first rapid approach
after a tool change into a machine-coordinate move to Z-3, an XY move to the
first point, and then a descent to the programmed work Z. M400 waits for
the lift and XY moves to finish. When the post emits a standalone M3 after
the tool change followed only by modal setup or comments before the rapid,
the spindle starts after the XY move and before the descent. The same
sequence is exported by **Post** and by the OpenSpindle handoff for the
bundled post. Use an OpenSpindle build with support for
`G53 G0 Z-3` in cutting operations.

A combined XYZ rapid or a Z-only rapid followed by XY at the same height
can be split this way. Other recognized approaches keep their programmed
moves with a machine-clearance move inserted before them. Rotary programs
and unrelated postprocessors retain their own output. The OpenSpindle
handoff applies the same approach to jobs using the older `makera_z1_named`
and `makera_z1` posts. Review the tool, clamps and workpiece in the actual
setup before running.

## Manual acceptance before using on a machine

1. Install via Addon Manager and restart FreeCAD. Select CAM and use **Send jobb
   til OpenSpindle** on the Makera Bridge toolbar. The standalone macro also
   sends the full job.
2. Use a Machine-based CAM Job with the intended Makera post. Include profile
   tabs, a pocket, drilling and multiple tools in representative test jobs.
3. For the bundled Machine, compare the handed-off NC with the normal post export, including tabs
   and tool changes. Then select one active operation and use **Send operasjon
   til OpenSpindle**. Compare it with FreeCAD's **Post Selected** for the same
   operation and verify that the other operations are absent. Inspect
   handoff.json and verify the byte count and SHA-256. The source ID property
   makes the document modified.
4. Export the same job twice: distinct folders, identical program hash. Modify
   a toolpath and export again: the program hash must change.
5. Select a compatible OpenSpindle build. Verify cold launch and an already
   running instance on Windows. On macOS enter the .app path. Import must show
   the intended file. A custom CAM job label names the file. For a default Job
   label the file uses the document name and, for a single active operation,
   its label. Sending one operation uses that operation's label. A normal send
   opens the export directly, without a FreeCAD confirmation dialog.
6. Try a missing executable before export: Find installation, Open download page,
   Export only and Cancel must be offered. Cancel (or closing the prompt) must
   create no export/source property. Download opens the official page only and
   returns to the choice; it must not imply installation. Canceling the file
   picker also returns to the choice. Export only opens the NC snapshot folder.
   Test a launch failure after export and check that the error includes the
   saved path for manual import.
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


## Finished model and material package

Send job and Send operation publish a self-contained `.ospjob` alongside the original `.nc` and `handoff.json`, then open the package in OpenSpindle. This requires the matching model/material branch of OpenSpindle; older releases can open the plain NC manually. The package uses schema `freecad-openspindle-job/1`. Its NC hash is checked by the receiver; geometry/material metadata is validated and never becomes executable NC.

The reference is the CAM Job's `Model.Group` resource clones, not the original body's unplaced shape. Tessellation is 0.05 mm, with parent placement baked relative to `Shape.Placement` once. Coordinates are mm/Z-up in the job's work frame with no centring or translation by the stock minimum. The stock's work-coordinate bounds accompany it. Models exceeding 100,000 triangles, 32 objects, ±10,000 mm, or a 64 MiB package fail with an explanation; no misaligned substitute is silently sent. These limits apply to display geometry only. Current work-plane/rotary limitations remain subject to the receiver's NC capability checks.

Material dictionaries or linked material objects on the authored body are read where available. Name, view colour, known shininess/transparency, convertible density and selected physical-property strings are transferred. Bare density numbers are not assigned guessed units. When a single body's stock has no material, its material is used for the stock. Unknown names remain unknown and can be edited in OpenSpindle. No physical metadata supplies machining parameters. Live FreeCAD tessellation, linked/container placements, material-card variants and cross-app alignment need desktop verification before merging.

## Shared tool library

The CAM toolbar's **Felles OpenSpindle-verktøy** command imports `.osptools` into a new immutable ToolBit/library directory or exports the active CAM job's ToolControllers. Register the returned library directory in FreeCAD's tool-library manager. Imported definitions carry shared UUID, revision and the exchanged entry as ToolBit attributes. Export retains them on the ToolBit; unchanged entries preserve their incoming revision, while edited geometry creates a new revision. Machine T numbers are local and are not cutter identity. Existing job tool objects are never silently replaced by importing a library.

The shared schema supports explicit millimetre flat, ball, V-bit and drill geometry and full included point angles. Incomplete/unsupported tools are reported. Machine offsets, holders, presets and measured lengths are not synchronized. This file workflow requires the matching shared-tool branches on both sides; networking is a later layer over the same representation.


## Remote host

Preferences can set a host root URL and access key. With a host configured, Send job/operation retains the local `.ospjob`/NC snapshot, sends the package to the authenticated inbox and checks a receipt containing the matching package hash and `received_not_started`. Opening the monitor never includes the key in its URL and never starts the job. Credentials are local FreeCAD settings, not document/project fields. HTTPS verification remains enabled, redirects are refused, and plain HTTP is only accepted for localhost/tunnel addresses. A failure leaves the local package available and does not retry an upload automatically.

The shared-tools command can import a library from the host into a new FreeCAD library revision or publish the job's tools. Publication uses ETag/If-Match, merges untouched IDs and asks before replacing changed host definitions. Concurrent edits reject the write instead of overwriting the other revision. This requires OpenSpindle's `feat/always-on-host` branch; the first browser release monitors jobs, while Run/Stop remain with the explicit local owner. USB is separate ADR work.
