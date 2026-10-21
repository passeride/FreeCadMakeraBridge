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
