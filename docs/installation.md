# Install, update and return to a previous version

## First install

1. Download **FreeCADMakeraBridge-install** from the successful **Handoff tests**
   Actions run for the PR/commit you want. GitHub may require you to sign in.
   The artifact download wraps the installation ZIP: extract that ZIP too.
2. Extract the whole installation package into a temporary folder. Keep its
   installer and Python files together. Do not run from inside a ZIP viewer.
3. In FreeCAD open Macro → Macros, browse to the extracted folder and run
   Install_FreeCADMakeraBridge.FCMacro.
4. Verify the macro directory displayed by the installer (it reads FreeCAD's
   configured path) and click **Installer / oppdater**.
5. Return to FreeCAD's normal macro directory and run **Klargjor_pa_Z1**.
   Choose the OpenSpindle executable once; that preference is retained.

The runtime is copied into the macro directory. The downloaded package can be
removed afterwards. Installation affects only the current user's chosen macro
folder. No pip, Poetry, terminal, administrator rights or running CNC is required.
OpenSpindle itself must be installed separately. Existing Community macros are
not replaced: the new install keeps its own private helper copy.

## Updates

Close other FreeCAD windows and wait for any export dialog to finish. Download
the new package, extract it and run **its** installer. The old installer installs
its own bundled version, so keep track of which download you opened.

A complete version is staged before it is activated. The active pointer is
replaced atomically; interrupted activation leaves the previous pointer in
place. Existing installed runtime files are never overwritten during update.
The installer rejects a conflicting launcher and detects edited runtime files;
it asks you to resolve these rather than silently overwriting custom work.
Repeated installation of the same payload does nothing and keeps rollback history.

The launcher's filename stays Klargjor_pa_Z1.FCMacro, so toolbar shortcuts keep
working. Start it again after the update. A restart is optional if no old dialog
is open. There is no import-cache dependency: every invocation loads its active
version from disk.

Preferences, exported NC snapshots, manifests and CAD documents are not part of
the installation and are not removed or reset. Version directories accumulate;
only remove an inactive directory after confirming it is not the previous
version you want to keep. Automatic cleanup and update notifications are future
work; this version does not fetch or execute remote updates.

## Roll back

Run an extracted installer and choose **Gå tilbake til forrige versjon**. This
switches to the previous complete installed version after checking its contents.
It does not download anything. Pressing again toggles back. A fresh install has
no previous version. This reverses application code only, not changes made to
CAD documents or jobs by a newer version; inspect those separately.

## Uninstall

Close FreeCAD dialogs. Remove Klargjor_pa_Z1.FCMacro and the private
FreeCADMakeraBridge subdirectory from the selected macro directory. Remove an
optional toolbar button using FreeCAD customization. Other macros, preferences,
CAD documents and exported jobs are kept. Delete preferences or exports separately
only if you also want to remove those.

## CLI and development

From an extracted package, with Python 3.10+:

```sh
python bridge_installer.py --macro-dir /absolute/path/to/FreeCAD/Macro
python bridge_installer.py --macro-dir /absolute/path/to/FreeCAD/Macro --rollback
```

Build a package with `python scripts/package_install.py`. Version is in VERSION;
the installed directory ID hashes the version and exact runtime bytes. This is
an integrity/change identifier, not a signature certifying a download's publisher.
Use packages from the intended repository and review the selected commit.

## Validation limits

Automated tests cover install, repeated install, update, rollback, failure before
activation, invalid packages, local modifications and conflicting filenames.
The ZIP is also tested by extracting it and installing from the extracted files.
FreeCAD GUI installation and toolbar behavior require manual validation on each
supported platform; they have not been exercised here.
