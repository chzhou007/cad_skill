import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts'))
import native_detail_corner_context as owner
from pipeline import validate_native_detail_corner_context


def evidence():
    return dict(mode=owner.MODE, frames=[dict(frame_id='A')], graph_mutated=False, mapping_ready=False,
        coordinate_offsets_are_physical_lengths=False, human_accepted=False, hil_ready=False,
        connections_added=0, pipe_values_assigned=0)


class CornerContextGateTests(unittest.TestCase):
    def test_native_reader_replayed_but_mapping_and_HIL_remain_pending(self):
        with patch.object(owner, 'verify_output', return_value=evidence()) as replay:
            result = validate_native_detail_corner_context('native-context')
        replay.assert_called_once_with('native-context')
        self.assertEqual(result['source_replay'], 'passed')
        self.assertEqual(result['status'], 'pending')
        self.assertFalse(result['individual_mapping_confirmed'])
        self.assertFalse(result['hil_ready'])

    def test_source_failure_is_not_accepted_as_regional_context(self):
        with patch.object(owner, 'verify_output', side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                validate_native_detail_corner_context('native-context')

    def test_forged_physical_or_mapping_claims_rejected(self):
        for key in ('graph_mutated', 'mapping_ready', 'coordinate_offsets_are_physical_lengths', 'human_accepted', 'hil_ready'):
            result = evidence()
            result[key] = True
            with self.subTest(key=key), patch.object(owner, 'verify_output', return_value=result):
                with self.assertRaises(ValueError):
                    validate_native_detail_corner_context('native-context')
        for key in ('connections_added', 'pipe_values_assigned'):
            for value in (1, False, None):
                result = evidence()
                result[key] = value
                with self.subTest(key=key, value=value), patch.object(owner, 'verify_output', return_value=result):
                    with self.assertRaises(ValueError):
                        validate_native_detail_corner_context('native-context')

    def test_empty_or_repeated_frame_scope_rejected(self):
        for frames in ([], [dict(frame_id='A'), dict(frame_id='A')]):
            result = copy.deepcopy(evidence())
            result['frames'] = frames
            with self.subTest(frames=frames), patch.object(owner, 'verify_output', return_value=result):
                with self.assertRaises(ValueError):
                    validate_native_detail_corner_context('native-context')


if __name__ == '__main__':
    unittest.main()
