import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from attach_source_checked_plan_attribute_groups import combine,MODE
from attach_source_checked_plan_attributes import verify_output

class GroupCompositionTests(unittest.TestCase):
    def fixture(self):
        base=dict(plan_graph_sha256='P',iso_graph_sha256='I',source_sha256={'plan':'S','iso':'T'},floor=1,human_accepted=False,expert_confirmation_claimed=False)
        return [dict(base,records=[dict(mapping_id='SC-0001',plan_edges=['P'+str(i)],iso_edges=['I'+str(i)])]) for i in (1,2)]

    def test_disjoint_groups_keep_distinct_receipt_identity_without_mutating_inputs(self):
        groups=self.fixture();before=copy.deepcopy(groups);out=combine(groups)
        self.assertEqual(groups,before);self.assertEqual([r['mapping_id'] for r in out['records']],['G01-SC-0001','G02-SC-0001'])
        self.assertEqual(out['records'][1]['source_group_mapping_id'],'SC-0001');self.assertFalse(out['human_accepted'])

    def test_shared_edges_different_versions_floors_and_acceptance_are_rejected(self):
        for variant in ('plan','iso','version','floor','acceptance','receipt'):
            groups=self.fixture()
            if variant in ('plan','iso'):groups[1]['records'][0][variant+'_edges']=groups[0]['records'][0][variant+'_edges']
            elif variant=='version':groups[1]['iso_graph_sha256']='stale'
            elif variant=='floor':groups[1]['floor']=2
            elif variant=='acceptance':groups[1]['human_accepted']=True
            else:groups[1]['records'].append(copy.deepcopy(groups[1]['records'][0]))
            with self.assertRaises(ValueError):combine(groups)
        with self.assertRaises(ValueError):combine(self.fixture()[:1])

    def test_common_verifier_dispatches_batch_before_single_input_assumptions(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            with patch('attach_source_checked_plan_attributes.load',return_value={'mode':MODE}),patch('attach_source_checked_plan_attribute_groups.verify_output',return_value={'mode':MODE}) as batch:
                self.assertEqual(verify_output(folder),{'mode':MODE});batch.assert_called_once_with(folder)

if __name__=='__main__':unittest.main()
