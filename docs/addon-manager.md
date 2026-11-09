# Addon Manager installation and publication

## Install and start a Z1 job

1. Open **Tools → Addon Manager**. Under **Custom repositories**, add
   `https://github.com/passeride/FreeCadMakeraBridge` on `main`.
2. Refresh the list, install **FreeCADMakeraBridge** and restart FreeCAD.
   Use FreeCAD 26.3 or later.
3. In **CAM**, open the **Makera Bridge** toolbar and click **Ny Z1-jobb**.
   Select the model in the standard FreeCAD dialog. The job uses the bundled
   **Makera Z1 3-axis - Makera Bridge** machine, metric output, G54 and the
   `makera_z1_bridge` post. Set the stock and work origin and select the tool
   for your operation.
4. Click **Send jobb til OpenSpindle** or select an operation and click
   **Send operasjon til OpenSpindle**. Install OpenSpindle separately. On the
   first send, the bridge can locate it or offer to export the file. Set its
   path and the export folder under **Edit → Preferences → Makera Bridge →
   OpenSpindle**.

The machine and post are registered directly from the addon's files. Updates
replace those bundled files through Addon Manager. FreeCAD's standard **Post**
command uses the same post when the job uses the bundled machine. To migrate
an existing three-axis job, select **Makera Z1 3-axis - Makera Bridge** in the
job's Machine settings. Existing jobs keep their chosen machine until you
change it. The bundled machine is for three-axis milling.

## Machine profiles and tool library

The Machines list includes three-axis profiles for **Makera Z1** and
**Makera Z1 Pro**. Both select the bundled `makera_z1_bridge` post.
**Ny Z1-jobb** defaults to Z1. For the Pro, select the Pro profile in the
job's Machine settings. Rotary machining requires a separate setup.

On restart after installation, the addon adds **Makera Bridge - Z1** to
CAM's Tool Bit Library. It includes the Makera 90°, 60° and 30° engraving
profiles, three O-flute sizes, a 2 mm drill and a 2 mm ball nose. The
definitions use FreeCAD's built-in shapes. Check the geometry against your
physical bit and set feeds and speeds for the job.

The tool library and bits go into the CAM asset directory configured in
FreeCAD, under `Tools/Library` and `Tools/Bit`. Only missing files are
installed. Existing tool files, including your changes to these bits, are
kept on update and after removing the addon. Restart after changing the
CAM asset directory to install the library in the new location.

For updates use Addon Manager's update operation and restart FreeCAD. If a
previous installation still reports a missing `FreeCAD_SendToOpenSpindle.FCMacro`
or `freecad.makera_bridge.handoff`, update to the latest version and restart FreeCAD.
If the update does not appear, check that the custom repository uses `main`.
This version is also available on `feat/openspindle-handoff` for existing
installs. Use the CAM toolbar button after restarting. Addon Manager may copy a launcher macro
to a different FreeCAD Macro directory. The toolbar loads the Python command
from `commands.py` in its own addon package. The current launcher also works with the installed
addon when it is copied by itself. Preferences
and exported jobs live outside the addon checkout. Do not use the standalone
installer to update this checkout: choose one installation method. If migrating
from the macro installer, remove its launcher and private runtime directory after
verifying the addon works; your preferences and exports are shared and retained.

Removing the addon through Addon Manager removes the CAM toolbar on the next
restart. It does not delete CAD documents, exports or FreeCAD preferences.
Addon Manager owns checkout updates; the standalone installer's rollback button
only affects its separate macro installation. To roll back the addon use an
explicit previously tested Git ref/custom-repository configuration.

## Official publication gate

FreeCAD's current official index is FreeCAD/Addons (not the pre-1.0 legacy
FreeCAD-addons index). Publication requires review by the Addons team.
The indexed addon must be substantially functional, have a consistent license,
accurate manifest and compatibility declarations, and meet repository/codebase
age and maintenance requirements. Alpha code and untested proof-of-concept
claims are unsuitable for indexing.

Before submitting:

1. Test installation, restart, CAM toolbar activation, export, OpenSpindle opening,
   updates and removal in actual supported FreeCAD builds. Record versions.
2. Verify the manifest against the current FreeCAD manifest schema, and verify
   its version requirements against the tested CAM API versions.
3. Prepare a stable release tag and verify the package version and metadata.
4. Confirm licensing and maintenance ownership. The PR proposes MIT licensing.
5. Check the repository and codebase age against the Index's 30-day requirement.
6. Submit an **Addon - Addition** issue in FreeCAD/Addons with the repository,
   release ref, compatibility and test evidence. Follow the review; an official
   catalog listing is controlled by FreeCAD maintainers, not this repository.

The addon is available through its custom repository. Official catalog listing is a separate review.

Sources:
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Publishing/Indexed.md
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Topics/Addon-Index/Index/Qualities.md
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Code/Workbench/index.md

Toolbar API reference: https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Code/Manipulators/index.md
