import copy,unittest
from ordered_owner_plan_context import collect,SOURCE_MODE
def fixture():
    h='a'*64;b=dict(axis_graph=h,rendered_graph=h,native_proof=h,axis_local_graph=h,plan_graph=h)
    e=dict(edge_id='E',start_node_id='A',end_node_id='B',system='supply',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[30,0]]],equipment_inventory=[])
    raw=dict(nodes=[dict(node_id='A',node_type='physical_junction',x=0,y=0,floor=2),dict(node_id='B',node_type='physical_junction',x=30,y=0,floor=2)],edges=[e]);view=copy.deepcopy(raw);view['instances']=[]
    prior=dict(source_graph_sha256=h,rendered_graph_sha256=h,horizontal_directions_degrees=[0,45,135],axis_vertical_segment_DN=dict(records=[dict(edge_id='VERTICAL',nominal_mm=80)]))
    m=dict(kind='same_floor_T_to_T_main',floor=2,system='supply',plan_edges=['P'],iso_edges=['E'],plan_start='PA',plan_end='PB',iso_start='A',iso_end='B',mapping_id='M')
    r=dict(plan_edge_id='P',system='supply',floor=2,nominal_mm=200,horizontal_plan_run_centerline_mm=1500,net_pipe_cut_length_mm=None,installed_whole_edge_length_mm=None,detail_inline_positions_scaled_to_plan=False,human_accepted=False)
    p=dict(mode=SOURCE_MODE,DN_used_for_mapping=False,local_graphs_mutated=False,attributes_fused=False,human_accepted=False,inputs={k:dict(sha256=h)for k in('axis_graph','plan_graph','plan_source','axis_source')},new_records=[m],member_plan_paths=dict(records=[r]),new_member_plan_edges=['P'],counts=dict(new_member_runs=1))
    return raw,view,copy.deepcopy(raw),p,b,prior
class Tests(unittest.TestCase):
    def test_new_member_domain_preserves_all_old_contexts_and_unknown_installed_length(self):
        a=fixture();before=copy.deepcopy(a);r=collect(*a);self.assertEqual(a,before);self.assertEqual(r['axis_edges'],1);self.assertEqual(r['records'][0]['horizontal_plan_run_centerline_mm'],1500);self.assertEqual(r['installed_lengths_assigned'],0)
    def test_vertical_axis_wrong_graph_duplicate_owner_or_unknown_metric_fail(self):
        for kind in ('vertical','graph','owner','metric'):
            a=list(fixture())
            if kind=='vertical':
                for g in a[:3]:g['edges'][0]['attribute_paths']=[[[0,0],[0,30]]]
            if kind=='graph':a[3]['inputs']['plan_graph']['sha256']='b'*64
            if kind=='owner':a[5]['member_plan_runs']=dict(records=[dict(axis_edge_id='E')])
            if kind=='metric':a[3]['member_plan_paths']['records'][0]['net_pipe_cut_length_mm']=0
            with self.assertRaises(ValueError,msg=kind):collect(*a)
if __name__=='__main__':unittest.main()
