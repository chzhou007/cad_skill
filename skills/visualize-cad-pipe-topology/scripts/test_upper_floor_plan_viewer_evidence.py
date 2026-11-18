import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from upper_floor_plan_viewer_evidence import verify
from attach_upper_floor_plan_attributes import ROOT
from build_visualization import verified_source_attribute_ancestor


class Tests(unittest.TestCase):
    def fixture(self,root):
        rows=[dict(mapping_id=e,edge_id=e) for e in ('A','B','C','D')]
        graph=dict(edges=[dict(edge_id=r['edge_id'],plan_segment_attributes=[r]) for r in rows],**{ROOT:dict(records=rows)})
        target=root/'graph_with_edges.json';target.write_text(json.dumps(graph),'utf8')
        named=dict(verified_axis_segment_parent=dict(current_native_parent=True),records=[dict(old_named_approach='kept')],
            plan_DN_scope_fusion=[dict(old_DN='kept')],parent_graph=dict(path='AXIS-PARENT'))
        audit=dict(output_graph_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),records=rows,verified_named_parent=named,
            previous_plan_vertical_and_component_fields_preserved=True,mixed_edge_whole_values_assigned=0,
            physical_ports_verified=False,related_HIL_confirmation_inherited=False,human_accepted=False,hil_ready=False)
        return target,graph,audit

    def test_fresh_native_parent_context_retains_old_records_without_whole_edge_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            target,graph,audit=self.fixture(Path(tmp));proof=dict(records=[dict(old='kept')],plan_DN_scope_fusion=[])
            with patch('attach_upper_floor_plan_attributes.verify_output',return_value=audit) as native,patch('attach_axis_riser_segment_attributes.viewer_ancestry',return_value=(Path('BASE'),proof)) as ancestry:
                ancestor,result=verify(target,graph)
            native.assert_called_once_with(target.parent);ancestry.assert_called_once_with(audit['verified_named_parent']['verified_axis_segment_parent'],audit['output_graph_sha256'])
            self.assertEqual(ancestor,Path('BASE'));self.assertEqual(len(result['records']),2)
            self.assertEqual(result['upper_floor_plan_segment_attribute_audit'],audit);self.assertFalse(result['hil_ready'])

    def test_graph_stale_segment_removed_or_whole_mixed_claim_blocks(self):
        for case in ('stale_graph','missing_row','root','mixed','HIL'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                target,graph,audit=self.fixture(Path(tmp))
                if case=='stale_graph':audit['output_graph_sha256']='wrong'
                elif case=='missing_row':graph['edges'][0].pop('plan_segment_attributes');target.write_text(json.dumps(graph),'utf8');audit['output_graph_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
                elif case=='root':graph[ROOT]['records']=[];target.write_text(json.dumps(graph),'utf8');audit['output_graph_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
                elif case=='mixed':audit['mixed_edge_whole_values_assigned']=1
                else:audit['human_accepted']=True
                with patch('attach_upper_floor_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):verify(target,graph)

    def test_builder_dispatches_new_stage_before_the_named_parent(self):
        data=dict(sourceUpperFloorPlanSegmentAttributes={'new':True},sourceNamedRiserPlanAttributeFusion={'old':True})
        expected=(Path('BASE'),dict(new_verified_stage=True))
        with patch('upper_floor_plan_viewer_evidence.verify',return_value=expected) as current,patch('attach_named_riser_plan_attributes.verify_output') as parent:
            self.assertEqual(verified_source_attribute_ancestor(Path('graph.json'),data),expected)
        current.assert_called_once_with(Path('graph.json'),data);parent.assert_not_called()
        with self.assertRaisesRegex(ValueError,'verified extension'):
            verified_source_attribute_ancestor(None,dict(edges=[dict(plan_segment_attributes=[{}])]))

    def test_source_gate_and_viewer_share_only_one_current_native_result_in_same_batch(self):
        owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from native_replay_session import replay_session
        from upper_floor_plan_attribute_gate import check_upper_floor_plan_attribute_graph
        with tempfile.TemporaryDirectory() as tmp:
            target,graph,audit=self.fixture(Path(tmp));parent=Path(tmp)/'parent';parent.mkdir();pg=parent/'graph_with_edges.json';pg.write_text('{}','utf8')
            ph=hashlib.sha256(pg.read_bytes()).hexdigest();report=dict(status='pending',errors=[],pending=['old source issue'],graph_sha256=ph)
            (parent/'source-comparison-gate.json').write_text(json.dumps(report),'utf8')
            audit.update(parent_graph=dict(path=str(pg),sha256=ph),added_segment_attribute_scopes=4,complete_main_centerline_route_edges=['C','D'],
                added_axis_edges=['A','B','C','D'],source_scope_sha256='s',mapping_sha256='m')
            def native(directory):
                target.read_bytes();return audit
            proof=dict(records=[],plan_DN_scope_fusion=[])
            with replay_session() as session,patch('attach_upper_floor_plan_attributes.verify_output',side_effect=native) as replay,patch('attach_axis_riser_segment_attributes.viewer_ancestry',return_value=(Path('BASE'),proof)):
                checked=check_upper_floor_plan_attribute_graph(target.parent,report,audit['output_graph_sha256'],target)
                _,shown=verify(target,graph)
                self.assertEqual(replay.call_count,1);self.assertEqual(session.statistics()['same_batch_reuses'],1)
            self.assertFalse(checked['hil_ready']);self.assertFalse(shown['hil_ready']);self.assertEqual(checked['pending'][0],'old source issue')


if __name__=='__main__':unittest.main()
