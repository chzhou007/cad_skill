import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import test_current_remaining_floor_plan_scopes as fixtures
from pipeline import validate_current_remaining_plan_scopes


class CurrentRemainingScopeGateTests(unittest.TestCase):
    def test_actual_native_owner_dispatch_preserves_partial_physical_scope(self):
        with patch('current_remaining_floor_plan_scopes.verify_output', return_value=fixtures.state()) as native:
            result = validate_current_remaining_plan_scopes(Path('RUN'))
        native.assert_called_once_with(Path('RUN'))
        self.assertEqual(result['mapped_plan_attribute_scopes'], 4)
        self.assertFalse(result['physical_values_fused'])

    def test_native_failure_or_candidate_promotion_blocks(self):
        with patch('current_remaining_floor_plan_scopes.verify_output', side_effect=ValueError('source failed')), self.assertRaisesRegex(ValueError, 'source failed'):
            validate_current_remaining_plan_scopes(Path('RUN'))
        data = fixtures.state(); data['axis_local_DN_candidates']['status'] = 'accepted'
        with patch('current_remaining_floor_plan_scopes.verify_output', return_value=data), self.assertRaises(ValueError):
            validate_current_remaining_plan_scopes(Path('RUN'))


if __name__ == '__main__': unittest.main()
