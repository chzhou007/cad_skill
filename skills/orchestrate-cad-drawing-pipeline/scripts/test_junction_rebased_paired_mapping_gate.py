import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import test_match_junction_rebased_paired_paths as fixtures
from pipeline import validate_source_crossview


class CurrentPairedMappingGateTests(unittest.TestCase):
    def test_actual_dispatch_calls_new_native_owner_and_preserves_pending_state(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=fixtures.MODE)), encoding='utf-8')
            with patch('match_junction_rebased_paired_paths.verify_output', return_value=fixtures.state()) as native:
                result = validate_source_crossview(folder)
            native.assert_called_once_with(folder)
            self.assertEqual(result['path_correspondence'], 'native_current_paired_service_and_branch_target_junctions_replayed')
            self.assertFalse(result['hil_ready'])

    def test_native_failure_and_promoted_state_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=fixtures.MODE)), encoding='utf-8')
            with patch('match_junction_rebased_paired_paths.verify_output', side_effect=ValueError('native changed')), self.assertRaisesRegex(ValueError, 'native changed'):
                validate_source_crossview(folder)
            bad = fixtures.state(); bad['physical_values_assigned'] = 1
            with patch('match_junction_rebased_paired_paths.verify_output', return_value=bad), self.assertRaises(ValueError):
                validate_source_crossview(folder)


if __name__ == '__main__': unittest.main()
