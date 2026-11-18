import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from lower_floor_plan_viewer_evidence import verify
from attach_lower_floor_plan_attributes import ROOT
from attach_upper_floor_plan_attributes import ROOT as UPPER_ROOT
from build_visualization import verified_source_attribute_ancestor


class Tests(unittest.TestCase):
    def fixture(self,root):
        prior=[dict(mapping_id=e,edge_id=e) for e in ('U1','U2','U3','U4')]
        rows=[dict(mapping_id=e,edge_id=e) for e in ('L1','L2','L3','L4')]
        graph=dict(edges=[dict(edge_id=r['edge_id'],plan_segment_attributes=[r]) for r in prior+rows],
            **{ROOT:dict(records=rows),UPPER_ROOT:dict(records=prior)})
        target=root/'graph_with_edges.json';target.write_text(json.dumps(graph),'utf8')
        named=dict(verified_axis_segment_parent=dict(native_parent=True),records=[dict(old_named='kept')],
            plan_DN_scope_fusion=[dict(old_DN='kept')],parent_graph=dict(path='AXIS-PARENT'))
        upper=dict(records=prior,verified_named_parent=named)
        audit=dict(output_graph_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),records=rows,verified_upper_parent=upper,
            previous_plan_vertical_and_component_fields_preserved=True,mixed_edge_whole_values_assigned=0,
            physical_ports_verified=False,related_HIL_confirmation_inherited=False,human_accepted=False,hil_ready=False)
        return target,graph,audit

    def test_replay_preserves_all_upper_and_named_context_without_replaying_parent_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            target,graph,audit=self.fixture(Path(tmp));proof=dict(records=[dict(old='kept')],plan_DN_scope_fusion=[])
            with patch('attach_lower_floor_plan_attributes.verify_output',return_value=audit) as native,patch('attach_axis_riser_segment_attributes.viewer_ancestry',return_value=(Path('BASE'),proof)):
                ancestor,result=verify(target,graph)
            native.assert_called_once_with(target.parent);self.assertEqual(ancestor,Path('BASE'));self.assertEqual(len(result['records']),2)
            self.assertEqual(result['upper_floor_plan_segment_attribute_audit'],audit['verified_upper_parent'])
            self.assertEqual(result['lower_floor_plan_segment_attribute_audit'],audit);self.assertFalse(result['hil_ready'])

    def test_stale_or_missing_upper_lower_or_HIL_claims_rejected(self):
        for case in ('stale','upper','lower','root','mixed','HIL','duplicate'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                target,graph,audit=self.fixture(Path(tmp))
                if case=='stale':audit['output_graph_sha256']='wrong'
                elif case=='upper':graph['edges'][0].pop('plan_segment_attributes')
                elif case=='lower':graph['edges'][-1].pop('plan_segment_attributes')
                elif case=='root':graph[ROOT]['records']=[]
                elif case=='mixed':audit['mixed_edge_whole_values_assigned']=1
                elif case=='HIL':audit['human_accepted']=True
                else:graph['edges'][0]['plan_segment_attributes'][0]['mapping_id']='L1'
                target.write_text(json.dumps(graph),'utf8')
                if case!='stale':audit['output_graph_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
                with patch('attach_lower_floor_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):verify(target,graph)

    def test_dispatch_checks_lower_before_retained_upper_stage(self):
        data={ROOT:dict(new=True),UPPER_ROOT:dict(old=True)};expected=(Path('BASE'),dict(native=True))
        with patch('lower_floor_plan_viewer_evidence.verify',return_value=expected) as current,patch('upper_floor_plan_viewer_evidence.verify') as parent:
            self.assertEqual(verified_source_attribute_ancestor(Path('graph.json'),data),expected)
        current.assert_called_once_with(Path('graph.json'),data);parent.assert_not_called()


if __name__=='__main__':unittest.main()
