import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pipeline
import native_named_prefix_version_bridge as owner


class NamedPrefixVersionBridgeGateTests(unittest.TestCase):
    def fixture(self):
        return dict(mode=owner.MODE, status='native_current_named_prefix_scopes_preserved_mapping_adoption_pending',
            both_native_parent_ancestries_replayed=True, graph_mutated=False,
            related_HIL_confirmation_inherited=False, human_accepted=False, hil_ready=False,
            new_mappings=0, new_physical_values_assigned=0, records=[dict(mapping_id='M'+str(i),
                system='supply' if i % 2 == 0 else 'return', native_pipe_scope_and_DN_unchanged=True,
                whole_axis_values_assigned=False, physical_ports_verified=False, human_accepted=False) for i in range(4)])

    def test_gate_replays_source_owner_and_retains_adoption_pending(self):
        with patch.object(owner, 'verify_output', return_value=self.fixture()) as verify:
            result = pipeline.validate_named_prefix_version_bridge(Path('source-run'))
        verify.assert_called_once_with(Path('source-run'))
        self.assertEqual(result['source_replay'], 'passed')
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['new_mappings'], 0)

    def test_failed_native_parent_is_not_converted_into_pending_success(self):
        with patch.object(owner, 'verify_output', side_effect=ValueError('changed native ancestor')):
            with self.assertRaisesRegex(ValueError, 'changed native ancestor'):
                pipeline.validate_named_prefix_version_bridge(Path('source-run'))

    def test_result_cannot_inherit_HIL_or_promote_zero_to_a_value(self):
        for key, value in [('human_accepted', True), ('new_physical_values_assigned', False),
                           ('both_native_parent_ancestries_replayed', False)]:
            data = copy.deepcopy(self.fixture())
            data[key] = value
            with patch.object(owner, 'verify_output', return_value=data):
                with self.assertRaises(ValueError):
                    pipeline.validate_named_prefix_version_bridge(Path('source-run'))

    def test_actual_CLI_dispatch_returns_pending_exit2(self):
        stdout = io.StringIO()
        with patch.object(owner, 'verify_output', return_value=self.fixture()), \
             patch.object(sys, 'argv', ['pipeline.py', 'validate-named-prefix-version-bridge', '--bridge-run', 'source-run']), \
             contextlib.redirect_stdout(stdout):
            code = pipeline.main()
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['preserved_named_scopes'], 4)
        self.assertFalse(result['hil_ready'])


if __name__ == '__main__':
    unittest.main()
