import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check
from wave_plan_scope_adoption_gate import check_wave_plan_scope_adoption


def fixture(root):
    parent=root/'parent';parent.mkdir();pg=parent/'graph_with_edges.json';pg.write_text('{}','utf8');ph=hashlib.sha256(pg.read_bytes()).hexdigest()
    previous=dict(graph_sha256=ph,errors=[],pending=['old unresolved issue'],lower_floor_plan_segment_attribute_stage=dict(source_replay='passed'))
    (parent/'source-comparison-gate.json').write_text(json.dumps(previous),'utf8')
    output=root/'current';output.mkdir();target=output/'graph_with_edges.json'
    proof=dict(prior_topology_components_and_other_attributes_preserved=True,whole_DN_or_lengths_added=0,related_HIL_confirmation_inherited=False,records=[dict(edge_id='E')],retained_historical_attributes=1,added_partial_attributes=0)
    graph=dict(sourceWaveRebasedPlanScopeAdoption=proof,sourceLowerFloorPlanSegmentAttributes={},edges=[]);target.write_text(json.dumps(graph),'utf8');gh=hashlib.sha256(target.read_bytes()).hexdigest()
    audit=dict(output_graph_sha256=gh,hil_ready=False,proof=proof,parent_graph=dict(path=str(pg),sha256=ph),verified_lower_parent=dict(output_graph_sha256=ph),axis_annotation_domains=dict(records=[]))
    return target,gh,previous,audit


class Tests(unittest.TestCase):
    def test_new_root_dispatches_before_lower_and_retains_prior_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            target,gh,previous,audit=fixture(Path(temp));before=copy.deepcopy(previous)
            with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=audit) as replay:
                result=check(previous,gh,target.parent,target)
            replay.assert_called_once_with(target.parent.resolve());self.assertEqual(previous,before)
            self.assertEqual(result['wave_plan_scope_adoption_stage']['source_replay'],'passed');self.assertIn('old unresolved issue',result['pending']);self.assertFalse(result['hil_ready'])

    def test_prior_errors_cannot_be_cleared_by_adoption(self):
        with tempfile.TemporaryDirectory() as temp:
            target,gh,previous,audit=fixture(Path(temp));previous['errors']=['prior deterministic defect']
            pg=Path(audit['parent_graph']['path']).parent/'source-comparison-gate.json';pg.write_text(json.dumps(previous),'utf8')
            with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=audit):result=check_wave_plan_scope_adoption(target.parent,previous,gh,target)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['errors'],['prior deterministic defect'])

    def test_stale_native_parent_or_comparison_context_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            target,gh,previous,audit=fixture(Path(temp))
            with patch('adopt_wave_rebased_plan_scopes.verify_output',side_effect=ValueError('source changed')):
                self.assertEqual(check(previous,gh,target.parent,target)['status'],'failed')
            with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=audit),self.assertRaises(ValueError):
                check_wave_plan_scope_adoption(target.parent,dict(previous,pending=[]),gh,target)


if __name__=='__main__':unittest.main()
