import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import test_junction_rebased_paired_plan_attributes as fixtures
from pipeline import validate_current_paired_plan_attributes


class CurrentPairedAttributeGateTests(unittest.TestCase):
    def test_native_owner_dispatch_and_unknowns_preserved(self):
        with patch('junction_rebased_paired_plan_attributes.verify_output', return_value=fixtures.state()) as native:
            result = validate_current_paired_plan_attributes(Path('RUN'))
        native.assert_called_once_with(Path('RUN'))
        self.assertEqual(result['known_DN_scopes'], 0)
        self.assertFalse(result['hil_ready'])

    def test_failed_native_or_physical_assignment_blocks(self):
        with patch('junction_rebased_paired_plan_attributes.verify_output', side_effect=ValueError('source changed')), self.assertRaisesRegex(ValueError, 'source changed'):
            validate_current_paired_plan_attributes(Path('RUN'))
        data = fixtures.state(); data['physical_values_fused'] = True
        with patch('junction_rebased_paired_plan_attributes.verify_output', return_value=data), self.assertRaises(ValueError):
            validate_current_paired_plan_attributes(Path('RUN'))


if __name__ == '__main__': unittest.main()
