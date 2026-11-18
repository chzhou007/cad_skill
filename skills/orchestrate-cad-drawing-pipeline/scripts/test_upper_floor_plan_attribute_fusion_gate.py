import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from upper_floor_plan_attribute_gate import check_upper_floor_plan_attribute_graph
from source_comparison_gate import check


class Tests(unittest.TestCase):
    def setup_files(self,root):
        parent=root/'parent';child=root/'child';parent.mkdir();child.mkdir()
        pg=parent/'graph_with_edges.json';pg.write_text('{}','utf8');gh=hashlib.sha256(pg.read_bytes()).hexdigest()
        report=dict(status='pending',graph_sha256=gh,errors=[],pending=['existing unresolved source case'],hil_ready=False,human_accepted=False)
        (parent/'source-comparison-gate.json').write_text(json.dumps(report),'utf8')
        audit=dict(output_graph_sha256='new',parent_graph=dict(path=str(pg),sha256=gh),
            previous_plan_vertical_and_component_fields_preserved=True,mixed_edge_whole_values_assigned=0,
            physical_ports_verified=False,related_HIL_confirmation_inherited=False,human_accepted=False,hil_ready=False,
            added_segment_attribute_scopes=4,added_axis_edges=['A','B','C','D'],complete_main_centerline_route_edges=['C','D'],
            records=[dict(edge_id=e) for e in ('A','B','C','D')],source_scope_sha256='s',mapping_sha256='m')
        return child,report,audit

    def test_independent_replay_preserves_all_complete_parent_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,report,audit=self.setup_files(Path(tmp))
            with patch('attach_upper_floor_plan_attributes.verify_output',return_value=audit) as verify:
                result=check_upper_floor_plan_attribute_graph(root,report,'new',root/'graph_with_edges.json')
            verify.assert_called_once_with(root.resolve());self.assertEqual(result['pending'][0],report['pending'][0]);self.assertEqual(len(result['pending']),2)
            self.assertEqual(result['upper_floor_plan_segment_attribute_stage']['segment_scopes'],4);self.assertFalse(result['hil_ready'])
            self.assertEqual(report['pending'],['existing unresolved source case'])

    def test_parent_errors_are_retained_rather_than_cleared_by_new_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,report,audit=self.setup_files(Path(tmp));report['errors']=['old source failure']
            (Path(audit['parent_graph']['path']).parent/'source-comparison-gate.json').write_text(json.dumps(report),'utf8')
            with patch('attach_upper_floor_plan_attributes.verify_output',return_value=audit):
                result=check_upper_floor_plan_attribute_graph(root,report,'new',root/'graph_with_edges.json')
            self.assertEqual(result['errors'],['old source failure']);self.assertEqual(result['status'],'failed')

    def test_stale_parent_wrong_output_or_physical_claims_fail_closed(self):
        for case in ('parent','context','output','preservation','mixed','HIL','scopes'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                root,report,audit=self.setup_files(Path(tmp))
                if case=='parent':Path(audit['parent_graph']['path']).write_text('{"changed":1}','utf8')
                elif case=='context':report['pending']=[]
                elif case=='output':audit['output_graph_sha256']='wrong'
                elif case=='preservation':audit['previous_plan_vertical_and_component_fields_preserved']=False
                elif case=='mixed':audit['mixed_edge_whole_values_assigned']=1
                elif case=='HIL':audit['hil_ready']=True
                else:audit['added_segment_attribute_scopes']=3
                with patch('attach_upper_floor_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):
                    check_upper_floor_plan_attribute_graph(root,report,'new',root/'graph_with_edges.json')

    def test_formal_dispatch_handles_new_segments_before_inherited_named_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,report,audit=self.setup_files(Path(tmp));graph=root/'graph_with_edges.json'
            graph.write_text(json.dumps(dict(sourceUpperFloorPlanSegmentAttributes={'new':True},sourceNamedRiserPlanAttributeFusion={'old':True})),'utf8')
            with patch('upper_floor_plan_attribute_gate.check_upper_floor_plan_attribute_graph',side_effect=ValueError('new segment source changed')),patch('source_comparison_gate.check_named_riser_plan_attribute_graph') as inherited:
                result=check(report,'new',root,graph)
            inherited.assert_not_called();self.assertEqual(result['status'],'failed');self.assertIn('new segment source changed',result['errors'][0])
            self.assertEqual(result['pending'],report['pending']);self.assertFalse(result['hil_ready'])


if __name__=='__main__':unittest.main()
