import sys
import types
import unittest
from unittest.mock import Mock, patch

from freecad.makera_bridge.commands import postprocess, z1_clearance_retract


class PostprocessTests(unittest.TestCase):
    def test_only_selected_operations_are_passed_to_the_freecad_post(self):
        job = types.SimpleNamespace(Machine='Z1')
        operation = object()
        post = Mock(spec=['export2'])
        post.export2.return_value = [('part.cnc', 'G1 X1')]
        processor = Mock()
        processor.PostProcessorFactory.get_post_processor.return_value = post
        machines = Mock()
        machines.MachineFactory.get_machine.return_value.postprocessor_file_name = 'makera_z1_named'
        with patch.dict(sys.modules, {'Path.Post.Processor': processor, 'Machine.models.machine': machines}):
            self.assertEqual(postprocess(job, [operation]), ('G1 X1', 'makera_z1_named'))
            with self.assertRaises(ValueError):
                postprocess(job, [])
        processor.PostProcessorFactory.get_post_processor.assert_called_once_with(
            {'job': job, 'operations': [operation]}, 'makera_z1_named'
        )

    def test_makera_post_uses_configured_minimum_when_toolhead_omits_it(self):
        # FreeCAD's bundle merge leaves MIN_SPINDLE_SPEED unset when a toolhead
        # has no minimum. The Makera post compares an S word against that value.
        for toolhead_minimum, expected_minimum in [(None, 5.0), (1000.0, 1000.0)]:
            with self.subTest(toolhead_minimum=toolhead_minimum):
                machine = types.SimpleNamespace(
                    postprocessor_file_name="makera_z1_named",
                    postprocessor_properties={"min_spindle_speed": 5.0, "min_feed_rate": 8.0},
                )
                job = types.SimpleNamespace(Machine="Z1")
                post = types.SimpleNamespace()

                def apply_configuration_bundle():
                    self.assertIs(post._machine, machine)
                    post.values = {
                        "MIN_SPINDLE_SPEED": toolhead_minimum,
                        "MIN_FEED_RATE": 8.0,
                    }

                def export2():
                    self.assertTrue(post._bundle_applied)
                    self.assertEqual(post.values["MIN_SPINDLE_SPEED"], expected_minimum)
                    self.assertEqual(post.values["MIN_FEED_RATE"], 8.0)
                    self.assertFalse(10000.0 < post.values["MIN_SPINDLE_SPEED"])
                    return [("job.cnc", "M3 S10000\nG1 X1 F100\n")]

                post.apply_configuration_bundle = apply_configuration_bundle
                post.export2 = export2
                processor = types.ModuleType("Path.Post.Processor")
                processor.PostProcessorFactory = Mock()
                processor.PostProcessorFactory.get_post_processor.return_value = post
                machines = types.ModuleType("Machine.models.machine")
                machines.MachineFactory = Mock()
                machines.MachineFactory.get_machine.return_value = machine
                with patch.dict(sys.modules, {
                    "Path.Post.Processor": processor,
                    "Machine.models.machine": machines,
                }):
                    self.assertEqual(
                        postprocess(job),
                        ("M3 S10000\nG1 X1 F100\n", "makera_z1_named"),
                    )

    def test_z1_export_adds_only_cutting_clearance_before_approach(self):
        source = (
            "G90 G94\nG17\nG21\nG54\nM05\nT2 M6\nM3 S12000.0\n"
            "(Vcarve)\n(starting)\nG0 Z3.000\nG0 X59.059 Y90.653 Z3.000\n"
            "G1 X59.059 Y90.653 Z-1.850 F120.0\n"
        )
        post = Mock(spec=["export2"])
        post.export2.return_value = [("part.cnc", source)]
        processor = Mock()
        processor.PostProcessorFactory.get_post_processor.return_value = post
        machines = Mock()
        machine = machines.MachineFactory.get_machine.return_value
        with patch.dict(sys.modules, {"Path.Post.Processor": processor, "Machine.models.machine": machines}):
            job = types.SimpleNamespace(Machine="Z1")
            machine.postprocessor_file_name = "makera_z1_named"
            exported, _ = postprocess(job)
            self.assertEqual(exported, source.replace(
                "(starting)\nG0 Z3.000",
                "(starting)\nG53 G0 Z-3\nM400\nG0 Z3.000",
            ))
            machine.postprocessor_file_name = "makera_carvera"
            self.assertEqual(postprocess(job)[0], source)

    def test_z1_clearance_retract_handles_each_tool_and_is_idempotent(self):
        source = (
            "G21 G90\r\nT2 M6\r\nG00 X20 Y30 Z3\r\nG1 Z-1\r\n"
            "M5\r\nM06 T3\r\nG0 Z4\r\nG0 X21 Y31"
        )
        result = z1_clearance_retract(source)
        self.assertIn("G53 G0 Z-3\r\nM400\r\nG00 X20 Y30 Z3", result)
        self.assertTrue(result.endswith("G53 G0 Z-3\r\nM400\r\nG0 Z4\r\nG0 X21 Y31"))
        self.assertEqual(z1_clearance_retract(result), result)
