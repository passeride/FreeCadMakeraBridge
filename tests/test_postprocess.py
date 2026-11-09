import sys
import types
import unittest
from unittest.mock import Mock, patch

from freecad.makera_bridge.commands import postprocess


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
