import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from test_rebuild_qualified_plan_scope_extension import fixture
from rebuild_qualified_plan_scope_extension import match_current,MODE
from qualified_plan_scope_context import collect
class Tests(unittest.TestCase):
    def case(self):
        a=fixture();records,_=match_current(*a);raw=a[5];view=copy.deepcopy(raw);view['instances']=[];h='a'*64
        proof=dict(mode=MODE,specific_provider_reconstructed=True,source_graphs_mutated=False,DN_used_for_mapping=False,physical_pipe_count_inferred=False,human_accepted=False,native_provider=dict(old_provider_receipt_accepted=False,current_native_provider_recomputed=True),inputs={k:dict(sha256=h)for k in('plan_graph','axis_graph','plan_source','axis_source')},records=records)
        return raw,view,a[4],a[3],proof,dict(axis_graph=h,rendered_graph=h,native_proof=h,axis_local_graph=h,plan_graph=h),dict(source_graph_sha256=h,rendered_graph_sha256=h,horizontal_directions_degrees=[0,45,135],axis_vertical_segment_DN=dict(records=[dict(edge_id='V',nominal_mm=80)]))
    def test_current_source_provider_fills_only_qualified_unknown_and_preserves_verticals(self):
        a=self.case();before=copy.deepcopy(a);r=collect(*a);self.assertEqual(a,before);self.assertEqual(r['axis_edges'],1);self.assertEqual(r['records'][0]['nominal_mm'],150);self.assertFalse(r['physical_pipe_count_inferred']);self.assertEqual(r['installed_lengths_assigned'],0)
    def test_old_receipt_acceptance_owner_collision_or_source_change_blocks(self):
        for kind in('receipt','owner','source'):
            a=list(self.case())
            if kind=='receipt':a[4]['native_provider']['old_provider_receipt_accepted']=True
            if kind=='owner':a[6]['member_plan_runs']=dict(records=[dict(axis_edge_id='E')])
            if kind=='source':a[4]['inputs']['plan_graph']['sha256']='b'*64
            with self.assertRaises(ValueError,msg=kind):collect(*a)
if __name__=='__main__':unittest.main()
