import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pipeline
import adopt_current_named_prefix_evidence as owner


class CurrentNamedPrefixFusionRouteTests(unittest.TestCase):
    def fixture(self):
        return dict(mode=owner.MODE, output_graph_sha256='a'*64, stage=dict(mode=owner.MODE,
            current_source_scopes=4, prior_topology_components_and_all_attributes_preserved=True,
            related_HIL_confirmation_inherited=False, human_accepted=False,
            new_mappings=0, new_physical_values_assigned=0))

    def test_native_owner_is_called_and_whole_acceptance_remains_pending(self):
        with patch.object(owner, 'verify_output', return_value=self.fixture()) as verify:
            result = pipeline.validate_current_named_prefix_evidence_fusion(Path('native-fusion'))
        verify.assert_called_once_with(Path('native-fusion'))
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['new_physical_values_assigned'], 0)

    def test_loss_of_old_values_or_inherited_HIL_blocks_route(self):
        for key, value in [('prior_topology_components_and_all_attributes_preserved', False),
                           ('human_accepted', True), ('new_physical_values_assigned', False)]:
            data = copy.deepcopy(self.fixture())
            data['stage'][key] = value
            with patch.object(owner, 'verify_output', return_value=data):
                with self.assertRaises(ValueError):
                    pipeline.validate_current_named_prefix_evidence_fusion(Path('native-fusion'))

    def test_actual_CLI_dispatch_returns_exit2(self):
        output = io.StringIO()
        with patch.object(owner, 'verify_output', return_value=self.fixture()), \
             patch.object(sys, 'argv', ['pipeline.py', 'validate-current-named-prefix-evidence-fusion', '--fusion-run', 'native-fusion']), \
             contextlib.redirect_stdout(output):
            code = pipeline.main()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['current_named_prefix_source_scopes'], 4)


if __name__ == '__main__':
    unittest.main()
