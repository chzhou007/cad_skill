import copy,unittest
from confirmed_member_plan_attribute_context import collect

def fixture():
    h='a'*64;scope=dict(floor=2,system='supply',kind='same_floor_T_to_T_main',plan_edges=['P'],iso_edges=['E'],group_scope_not_allocated_to_child_edges=False,
        plan_drawn_nominal_mm=200,graph_sha256=dict(plan=h),source_sha256=dict(plan=h,iso=h),mapping_id='M',mapping_receipt_sha256=h)
    graph=dict(nodes=[dict(node_id='A',node_type='tee',floor=2,x=0,y=0),dict(node_id='B',node_type='tee',floor=2,x=100,y=0)],
        edges=[dict(edge_id='E',system='supply',start_node_id='A',end_node_id='B',start_floor=2,end_floor=2,attribute_paths=[[[0,0],[100,0]]],batch_plan_attribute_scopes=scope)],
        sourceFullPlanBatchAttributes=dict(source_verification_pending=False,human_accepted=False,records=[scope]))
    members=dict(graph_sha256=h,source_sha256=h,local_connectivity_changed=False,detail_drawing_span_used_as_length=False,records=[dict(plan_edge_id='P',floor=2,system='supply',nominal_mm=200,
        horizontal_plan_run_centerline_mm=4000,net_pipe_cut_length_mm=None,installed_whole_edge_length_mm=None,detail_inline_positions_scaled_to_plan=False,run_centerline_includes_inline_assembly_extents=True)])
    return graph,copy.deepcopy(graph),members,dict(axis_graph=h,rendered_graph=h,member_proof=h),[0,45,135]

class Tests(unittest.TestCase):
    def test_axis_span_is_not_length_and_old_graph_is_exact(self):
        args=fixture();before=copy.deepcopy(args[0]);r=collect(*args)
        self.assertEqual(r['axis_edges'],1);self.assertEqual(r['records'][0]['horizontal_plan_run_centerline_mm'],4000)
        self.assertIsNone(r['records'][0]['net_pipe_cut_length_mm']);self.assertEqual(args[0],before)
    def test_mixed_vertical_and_merged_mapping_are_not_promoted(self):
        for defect in ('cross_floor','group','missing'):
            a=list(fixture())
            if defect=='cross_floor':a[0]['edges'][0]['end_floor']=3;a[1]['edges'][0]['end_floor']=3
            elif defect=='group':a[0]['sourceFullPlanBatchAttributes']['records'][0]['iso_edges'].append('OTHER')
            else:a[0]['sourceFullPlanBatchAttributes']['records']=[]
            r=collect(*a);self.assertEqual(r['axis_edges'],0);self.assertEqual(len(r['pending']),1)
    def test_changed_service_source_DN_or_rendered_geometry_fails(self):
        for defect in ('system','source','DN','geometry','net_length'):
            a=list(fixture())
            if defect=='geometry':a[1]['edges'][0]['attribute_paths']=[[[0,0],[90,0]]]
            elif defect=='net_length':a[2]['records'][0]['net_pipe_cut_length_mm']=4000
            elif defect=='source':a[2]['source_sha256']='b'*64
            elif defect=='DN':a[2]['records'][0]['nominal_mm']=300
            else:a[2]['records'][0]['system']='return'
            with self.subTest(defect=defect),self.assertRaises(ValueError):collect(*a)
if __name__=='__main__':unittest.main()
