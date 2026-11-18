import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_mapped_native_DN_comparison
import test_compare_mapped_plan_axis_diameters as native
from compare_mapped_plan_axis_diameters import compare


class Tests(unittest.TestCase):
    def test_formal_owner_replay_keeps_extent_differences_and_unexamined_paths_pending(self):
        data=compare(*native.scenario());data.update(mapping_sha256='M',attributes_sha256='A')
        with patch('compare_mapped_plan_axis_diameters.verify_output',return_value=data) as replay:
            result=validate_mapped_native_DN_comparison('run')
        replay.assert_called_once_with('run');self.assertEqual(result['DN_difference_paths'],2);self.assertEqual(result['paths_without_selected_axis_annotations'],1)
        self.assertFalse(result['source_contradictions_confirmed']);self.assertFalse(result['hil_ready'])

    def test_native_failure_is_not_downgraded_to_a_review_question(self):
        with patch('compare_mapped_plan_axis_diameters.verify_output',side_effect=ValueError('current source differs')),self.assertRaisesRegex(ValueError,'current source differs'):
            validate_mapped_native_DN_comparison('run')


if __name__=='__main__':unittest.main()
