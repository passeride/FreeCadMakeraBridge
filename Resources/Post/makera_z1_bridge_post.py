# SPDX-License-Identifier: LGPL-2.1-or-later
"""FreeCAD machine post for the Makera Bridge Z1 profile."""
from Path.Post.Processor import PostProcessor
from freecad.makera_bridge.commands import z1_clearance_retract
from freecad.makera_bridge.vendor.makera_post import Makera_26_Mch

POST_TYPE = "machine"


class Makera_Z1_Bridge(Makera_26_Mch):
    def apply_configuration_bundle(self, *args, **kwargs):
        result = super().apply_configuration_bundle(*args, **kwargs)
        # FreeCAD leaves the spindle minimum unset if the machine has no lower
        # hardware limit. The Makera post still needs a minimum for its S check.
        if self.values.get("MIN_SPINDLE_SPEED") is None:
            self.values["MIN_SPINDLE_SPEED"] = self._machine.postprocessor_properties["min_spindle_speed"]
        return result

    def _build_header(self, postables):
        # Use FreeCAD's header directly and initialize the tool list even if
        # the user disables the header in the machine editor.
        header = PostProcessor._build_header(self, postables)
        self.tool_controllers = (
            self._collect_tool_controllers(postables)
            if self.values["OUTPUT_HEADER"] and self.values.get("LIST_TOOLS_IN_HEADER", True)
            else []
        )
        return header

    def export2(self):
        sections = super().export2()
        if not sections:
            return sections
        return [(name, z1_clearance_retract(nc)) for name, nc in sections]
