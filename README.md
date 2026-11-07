# FreeCAD Makera Bridge

FreeCAD CAM macro: [FreeCAD_SendToCommunity.FCMacro](FreeCAD_SendToCommunity.FCMacro).

Export G-code using your configured Makera Z1 Machine postprocessor. The macro writes a local `.nc` and optionally a JSON request in `~/Documents/Carvera-FreeCAD-Inbox` for a source-built Carvera Community Controller inbox consumer. The standard Controller executable cannot consume requests without the optional source modification. No machining is started automatically.

## Installation

Copy the `.FCMacro` file to FreeCAD's macro directory (Macro → Macros). Run it with your CAM Job selected. Automatic upload is OFF by default. For manual upload, use Controller's Upload and Select command.

For automatic upload, use the source-built [passeride/Carvera_Controller](https://github.com/passeride/Carvera_Controller) fork. The optional bridge is now included in `main` and is disabled unless you enable it. See the [Controller setup guide](https://github.com/passeride/Carvera_Controller/blob/main/docs/freecad-bridge.md).

Launch the Controller from the same Windows account as FreeCAD, with the environment variable `FREECAD_BRIDGE_ENABLED=1`. In PowerShell:

~~~powershell
$env:FREECAD_BRIDGE_ENABLED = "1"
poetry run python -m carveracontroller
~~~

If the inbox is not the default `%USERPROFILE%\Documents\Carvera-FreeCAD-Inbox`, set `FREECAD_BRIDGE_INBOX` to the exact same directory configured in the FreeCAD macro. The standard released Controller executable still does not include the bridge.

In FreeCAD, tick **Automatic upload** to queue the file. This is a local filesystem queue, not an HTTP API; a queued request is not proof that Z1 has received the file.

Status files: `.request.json` pending, `.processing.json` claimed, `.done.json` upload acknowledged, `.failed.json` failed or timed out. A timeout does not prove the CNC lacks the file. Check the machine file list before retrying.

Review G-code, work offsets, tool clearance, and Scan Machining Area before manually starting the machine.

## Addon Manager (experimental)

This PR includes a namespaced **Makera Bridge** workbench and package.xml.
Install through Addon Manager using this repository as a custom repository on
branch `feat/openspindle-handoff`, then restart FreeCAD and select **Makera Bridge**.
Updates are managed by Addon Manager. See [addon installation and official
publication requirements](docs/addon-manager.md). This is not yet listed in the
official catalog and still needs real FreeCAD GUI validation. MIT licensing is
proposed by this PR. The standalone macro installer below remains an alternative.

## OpenSpindle: Klargjør på Z1

Download the installation ZIP from the PR's **Handoff tests** Actions run
(artifact **FreeCADMakeraBridge-install**), then extract the whole ZIP.
In FreeCAD open **Macro → Macros**, browse to the extracted folder and run
`Install_FreeCADMakeraBridge.FCMacro`. Choose **Installer / oppdater**.
The installer uses FreeCAD's configured macro directory and needs no admin rights.
Run `Klargjor_pa_Z1` from the normal macro list afterwards. You can attach this
stable launcher to a toolbar through FreeCAD's macro customization.

For updates, close other FreeCAD windows, download and extract the new package,
then run its installer again. Runtime files are installed together in a versioned
folder and activated with one atomic pointer change. The previous version is
retained. **Gå tilbake til forrige versjon** restores it. Exported jobs and FreeCAD
preferences (OpenSpindle path and export directory) are kept. No network updater
runs inside FreeCAD. See [installation and updates](docs/installation.md).

Select your CAM Job and run `Klargjor_pa_Z1`. Choose the OpenSpindle executable
using **Velg program…**, then **Klargjør på Z1**. On macOS enter the full `.app`
bundle path in the field. Untick opening to export only. The paths are remembered.

Requires FreeCAD's Machine-based CAM `export2` API and a configured Makera
postprocessor. Legacy FreeCAD 1.1 jobs are not supported by this macro.
OpenSpindle must support opening NC files from the OS/command line. At review
time main supported Windows, but release v0.3.0 had macOS assets only; use a
compatible build rather than assuming every published version has this support.

The macro recomputes and blocks objects still marked invalid/error/touched,
exports one complete program (at most 10 MiB), and stores the original post
output with a bridge-owned `handoff.json` in a unique snapshot directory.
A persistent source ID is added to the CAM Job; save the FreeCAD document to
retain it. A copied Job receives a new ID when a duplicate is detected.
The full NC SHA-256 is the **program revision**, not a revision of stock,
fixtures or the whole CAD model. Each export also has a unique snapshot ID.
The manifest records source identity, operation names, postprocessor name and
FreeCAD version. It is local traceability metadata; OpenSpindle does not consume
this sidecar or acknowledge it. The executable is launched without a shell.

If opening fails the export remains available for manual import. A successful
launch means only **Åpning forespurt**, never imported, uploaded, verified, or
running. Check tools, stock and work origin in OpenSpindle. Geometry/fixtures,
stock markers, tool-library synchronization and update-in-place are not
implemented. No work offsets are sent and no machine connection is opened.
There is no automatic machining start.

See [design vision](docs/design-vision.md) and
[delivery status and acceptance runbook](docs/openspindle-integration.md).

Offline tests: `python -m unittest discover -s tests -v`.

