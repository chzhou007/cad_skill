import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
import match_known_junction_direct_mains as mapping_owner
from test_match_known_junction_direct_mains import fixture
import test_known_junction_main_plan_attributes as attribute_fixtures


def mapping_state():
    gs,parents=fixture();rows,_=mapping_owner.discover(gs,parents,2);rows[0]['mapping_id']='NEW'
    return dict(mode=mapping_owner.MODE,status='native_direct_known_junction_mains_attributes_pending',records=rows,
        local_graphs_mutated=False,physical_values_fused=False,whole_floor_connectivity_confirmed=False,human_accepted=False,hil_ready=False)


class KnownJunctionGateTests(unittest.TestCase):
    def test_mapping_dispatch_calls_native_owner_and_retains_pending_state(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=mapping_owner.MODE)),encoding='utf-8')
            with patch('match_known_junction_direct_mains.verify_output',return_value=mapping_state()) as native:
                result=pipeline.validate_source_crossview(folder)
            native.assert_called_once_with(folder);self.assertEqual(result['additional_main_paths'],1)
            self.assertFalse(result['hil_ready']);self.assertFalse(result['whole_floor_connectivity_confirmed'])

    def test_mapping_native_failure_and_promoted_acceptance_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=mapping_owner.MODE)),encoding='utf-8')
            with patch('match_known_junction_direct_mains.verify_output',side_effect=ValueError('native source changed')):
                with self.assertRaisesRegex(ValueError,'native source'):pipeline.validate_source_crossview(folder)
            bad=mapping_state();bad['human_accepted']=True
            with patch('match_known_junction_direct_mains.verify_output',return_value=bad),self.assertRaises(ValueError):
                pipeline.validate_source_crossview(folder)

    def test_attribute_dispatch_calls_native_owner_and_does_not_fuse(self):
        data=attribute_fixtures.PlanAttributeTests().valid_result()
        with patch('known_junction_main_plan_attributes.verify_output',return_value=data) as native:
            result=pipeline.validate_known_junction_main_plan_attributes(Path('ATTR'))
        native.assert_called_once_with(Path('ATTR'));self.assertEqual(result['known_DN_scopes'],1)
        self.assertFalse(result['human_accepted']);self.assertEqual(result['whole_axis_physical_values_assigned'],0)

    def test_attribute_native_failure_and_fabricated_whole_length_fail(self):
        with patch('known_junction_main_plan_attributes.verify_output',side_effect=ValueError('native length changed')):
            with self.assertRaisesRegex(ValueError,'native length'):pipeline.validate_known_junction_main_plan_attributes(Path('ATTR'))
        bad=attribute_fixtures.PlanAttributeTests().valid_result();bad['records'][0]['whole_axis_physical_length_mm']=1000
        with patch('known_junction_main_plan_attributes.verify_output',return_value=bad),self.assertRaises(ValueError):
            pipeline.validate_known_junction_main_plan_attributes(Path('ATTR'))


if __name__=='__main__':unittest.main()
