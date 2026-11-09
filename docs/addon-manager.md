# Addon Manager installation and publication

## Experimental installation from our repository

This addon is not in the official FreeCAD catalog yet.

1. Open **Tools → Addon Manager** in FreeCAD.
2. Open its preferences/settings and find **Custom repositories**. The settings
   location and labels can differ between Addon Manager versions.
3. Add repository `https://github.com/passeride/FreeCadMakeraBridge` and select
   branch `feat/openspindle-handoff`. Use the branch field if shown; do not leave
   it on main, which does not contain the addon until the PR is merged.
4. Refresh the addon list, select **FreeCADMakeraBridge** and install it.
5. Restart FreeCAD, activate **CAM**, and show the **Makera Bridge** toolbar if
   you previously hid it. It contains one **Klargjør på Z1** button.
6. Select your CAM Job and click the button. Choose the OpenSpindle executable
   on the first run. Its path and export directory are remembered.

There is no additional workbench to select. The addon contributes a small
CAM-only toolbar using FreeCAD's workbench-manipulator API, available since 1.0.
The internal CAMWorkbench name and legacy PathWorkbench alias are recognized.
Other workbenches receive no toolbar changes. No separate macro installer is
needed with this installation method.

The installed FreeCAD must have Machine-based CAM and the export2 API. The
manifest minimum is a baseline loader requirement, not a promise that legacy
1.1 CAM Jobs work. A configured Makera post and a compatible OpenSpindle build
are still needed. The addon does not install OpenSpindle or add Linux support
to OpenSpindle itself. GUI discovery and end-to-end installation need testing
on the user's FreeCAD build.

For updates use Addon Manager's update operation and restart FreeCAD. If a
previous installation still reports a missing `FreeCAD_SendToOpenSpindle.FCMacro`,
reinstall the addon from the configured branch and restart FreeCAD. Use the
CAM toolbar button after restarting. Addon Manager may copy a launcher macro
to a different FreeCAD Macro directory. The toolbar loads the Python dialog
from its own addon package. The current launcher also works with the installed
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
3. Merge and prepare a stable release branch/tag; change package.xml's repository
   branch and documentation URL to that stable branch, and update version/date.
4. Confirm licensing and maintenance ownership. The PR proposes MIT licensing.
5. Check the repository and codebase age against the Index's 30-day requirement.
6. Submit an **Addon - Addition** issue in FreeCAD/Addons with the repository,
   release ref, compatibility and test evidence. Follow the review; an official
   catalog listing is controlled by FreeCAD maintainers, not this repository.

No index request has been submitted because this integration is still awaiting
real FreeCAD testing. The PR makes custom-repository installation possible and
provides the publication path without advertising an approved catalog listing.

Sources:
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Publishing/Indexed.md
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Topics/Addon-Index/Index/Qualities.md
- https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Code/Workbench/index.md

Toolbar API reference: https://github.com/FreeCAD/Addon-Academy/blob/main/Source/Guides/Code/Manipulators/index.md
