import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from reviewed_plan_gap_gate import check as check_inherited_wave_graph,OWNER
from confirm_crossview_paths import sha as digest
if str(OWNER) not in sys.path:sys.path.insert(0,str(OWNER))


class Tests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        parent=root/'parent/graph_with_edges.json';parent.parent.mkdir();parent.write_text('{}','utf8')
        run=root/'wave';run.mkdir();path=run/'graph_with_edges.json'
        node=lambda name:dict(node_id=name,boundary_type='unresolved_source_terminal')
        graph=dict(nodes=[node('remaining')],edges=[],metadata=dict(hil_ready=False),sourceReviewedDrawingGapContinuity=dict(
            input_graph_sha256=digest(parent),source_sha256='S',physical_Ts_added=0,physical_lengths_assigned=0,supply_return_independent=True,records=[{}],dependent_mapping_attributes_and_HIL_invalidated=True,
            human_accepted=False,retired_node_snapshots=[node('wave1'),node('wave2')]))
        path.write_text(json.dumps(graph),'utf8');audit=dict(mode='explicit_reviewed_same_service_plan_gap_continuity_v1',output_graph_sha256=digest(path),
            inputs=dict(graph=dict(path=str(parent),sha256=digest(parent)),source=dict(sha256='S')),proof=dict(pairs=1,components=2))
        comparison=dict(status='pending',errors=[],pending=['3 graph nodes have unresolved source-terminal or equipment-overlap semantics','other unresolved source issue'],
            graph_unresolved_node_blockers=[node('wave1'),node('wave2'),node('remaining')],equipment_source_port_blockers=[dict(node_id='device')])
        return run,path,graph,audit,comparison

    def test_only_proven_retired_drawing_nodes_change_while_other_issues_remain(self):
        run,path,graph,audit,parent=self.fixture();original=copy.deepcopy(parent)
        with patch('reconstruct_reviewed_plan_gaps.verify_output',return_value=audit) as verify,patch('source_comparison_gate.check',return_value=parent):
            result=check_inherited_wave_graph(run,{},digest(path),path)
        verify.assert_called_once_with(run);self.assertEqual(parent,original)
        self.assertEqual([n['node_id'] for n in result['graph_unresolved_node_blockers']],['remaining'])
        self.assertIn('other unresolved source issue',result['pending']);self.assertFalse(result['hil_ready'])
        self.assertEqual(result['equipment_source_port_blockers'],parent['equipment_source_port_blockers'])
        self.assertEqual(result['reviewed_drawing_gap_stage']['physical_lengths_assigned'],0)

    def test_parent_errors_stay_blocking(self):
        run,path,graph,audit,parent=self.fixture();parent['errors']=['source unreadable']
        with patch('reconstruct_reviewed_plan_gaps.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent):
            result=check_inherited_wave_graph(run,{},digest(path),path)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['errors'],['source unreadable'])

    def test_unrelated_removed_node_or_new_blocker_cannot_be_hidden(self):
        run,path,graph,audit,parent=self.fixture();parent['graph_unresolved_node_blockers'].append(dict(node_id='unrelated'))
        with patch('reconstruct_reviewed_plan_gaps.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent):
            with self.assertRaisesRegex(ValueError,'unrelated unresolved'):check_inherited_wave_graph(run,{},digest(path),path)

    def test_stale_output_identity_fails_before_parent_consumption(self):
        run,path,graph,audit,parent=self.fixture()
        with patch('reconstruct_reviewed_plan_gaps.verify_output',return_value=audit),patch('source_comparison_gate.check') as check:
            with self.assertRaisesRegex(ValueError,'evidence or invalidation'):check_inherited_wave_graph(run,{},'wrong',path)
        check.assert_not_called()

    def test_dispatches_before_retained_ownership_and_preserves_errors_on_failure(self):
        from source_comparison_gate import check
        run,path,graph,audit,parent=self.fixture();graph['sourceLayoutEquipmentOwnership']={};path.write_text(json.dumps(graph),'utf8')
        with patch('reviewed_plan_gap_gate.check',return_value={'chosen':'wave'}) as current,patch('source_comparison_gate.check_layout_equipment_ownership_graph') as old:
            self.assertEqual(check({},digest(path),run,path),{'chosen':'wave'})
        current.assert_called_once();old.assert_not_called()
        with patch('reviewed_plan_gap_gate.check',side_effect=ValueError('native changed')):
            result=check({'errors':['old error'],'pending':['old pending']},digest(path),run,path)
        self.assertIn('old error',result['errors']);self.assertEqual(result['pending'],['old pending']);self.assertFalse(result['hil_ready'])


if __name__=='__main__':unittest.main()
