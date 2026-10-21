# FreeCAD Makera Bridge

FreeCAD CAM macro: [FreeCAD_SendToCommunity.FCMacro](FreeCAD_SendToCommunity.FCMacro).

Export G-code using your configured Makera Z1 Machine postprocessor. The macro writes a local `.nc` and optionally a JSON request in `~/Documents/Carvera-FreeCAD-Inbox` for a source-built Carvera Community Controller inbox consumer. The standard Controller executable cannot consume requests without the optional source modification. No machining is started automatically.

## Installation

Copy the `.FCMacro` file to FreeCAD's macro directory (Macro → Macros). Run it with your CAM Job selected. Automatic upload is OFF by default. For manual upload, use Controller's Upload and Select command.

For automatic upload, the Controller fork requires the optional `carveracontroller/freecad_inbox_bridge.py` consumer enabled in `main.py`. The bridge was not yet installed in the fork because GitHub denied writes (HTTP 403). See the previous downloadable bridge package for the standalone source installer.

Status files: `.request.json` pending, `.processing.json` claimed, `.done.json` upload acknowledged, `.failed.json` failed or timed out. A timeout does not prove the CNC lacks the file. Check the machine file list before retrying.

Review G-code, work offsets, tool clearance, and Scan Machining Area before manually starting the machine.
