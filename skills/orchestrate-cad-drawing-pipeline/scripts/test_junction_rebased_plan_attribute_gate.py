import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_junction_rebased_plan_attributes
from test_junction_rebased_plan_attributes import CurrentCorridorAttributeTests


class CurrentCorridorPlanGateTests(unittest.TestCase):
    def test_actual_owner_dispatch_keeps_source_stage_pending(self):
        fixture = CurrentCorridorAttributeTests().fixture()
        with patch('junction_rebased_plan_attributes.verify_output', return_value=fixture) as native:
            result = validate_junction_rebased_plan_attributes(Path('RUN'))
        native.assert_called_once_with(Path('RUN'))
        self.assertEqual(result['mapped_plan_attribute_scopes'], 10)
        self.assertFalse(result['hil_ready'])

    def test_failed_native_replay_or_physical_promotion_blocks(self):
        with patch('junction_rebased_plan_attributes.verify_output', side_effect=ValueError('native failed')), self.assertRaisesRegex(ValueError, 'native failed'):
            validate_junction_rebased_plan_attributes(Path('RUN'))
        data = CurrentCorridorAttributeTests().fixture(); data['installed_lengths_assigned'] = 1
        with patch('junction_rebased_plan_attributes.verify_output', return_value=data), self.assertRaises(ValueError):
            validate_junction_rebased_plan_attributes(Path('RUN'))


if __name__ == '__main__': unittest.main()
