import copy,unittest
from ordered_group_metric_context import collect

def fixture():
    h='a'*64;scope=dict(mapping_id='M',floor=3,system='return',kind='native_main_chain_between_independent_junctions',human_accepted=False,group_scope_not_allocated_to_child_edges=True,
        graph_sha256=dict(plan=h),source_sha256=dict(plan=h,iso=h),plan_edges=['P1','P2'],iso_edges=['E1','E2'],mapping_receipt_sha256=h)
    edges=[dict(edge_id='E'+str(i),system='return',start_node_id='N'+str(i),end_node_id='N'+str(i+1),attribute_paths=[[[100*i,0],[100*(i+1),0]]])for i in (1,2)]
    graph=dict(edges=edges,sourceFullPlanBatchAttributes=dict(records=[scope]));records=[]
    for i,edge in enumerate(edges):
        pieces=[dict(plan_edge='P'+str(i+1),source_line_handle='LINE',length_mm=10)]
        records.append(dict(axis_edge_id=edge['edge_id'],plan_edge_id='P'+str(i+1),index_in_group=i,floor=3,system='return',axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
            known_plan_pipe_XY_mm=10,complete_horizontal_run_centerline_mm=10 if i==0 else None,physical_installed_length_mm=None,net_pipe_cut_length_mm=None,
            axis_drawn_lengths_or_ratios_used=False,unknown_inline_joint_handles=[]if i==0 else['J1','J2'],source_projection=dict(value_mm=10,pieces=pieces,installed_whole_edge_length_mm=None),
            child_equipment_or_external_interface_identity_inferred=False,human_accepted=False,inline_source_proof=dict(heavyweight=True)))
    proof=dict(axis_source_graph_sha256=h,local_graphs_mutated=False,proportional_length_allocation=False,pending=[],groups=[dict(mapping_id='M',plan_graph_sha256=h,source_sha256=dict(plan=h,iso=h),records=records)])
    context=dict(groups=[dict(mapping_id='M',nominal_mm=250)])
    return graph,copy.deepcopy(graph),proof,context,dict(axis_graph=h,rendered_graph=h,length_proof=h)

class Tests(unittest.TestCase):
    def test_native_child_metric_remains_independent_of_axis_scale_and_unknown_inline_interiors(self):
        args=fixture();before=copy.deepcopy(args);result=collect(*args)
        self.assertEqual(result['axis_edges'],2);self.assertEqual(result['complete_run_children'],1);self.assertEqual(result['partial_pipe_XY_children'],1)
        self.assertEqual([r['known_plan_pipe_XY_mm']for r in result['records']],[10,10]);self.assertEqual(result['records'][0]['nominal_mm'],250)
        self.assertNotIn('inline_source_proof',result['records'][1]);self.assertEqual(args,before)
    def test_changed_source_or_path_duplicate_child_and_unknown_length_promotion_fail(self):
        for defect in ('source','geometry','duplicate','negative_index','pieces','net_length','inline_complete','graphic_span'):
            args=list(fixture());row=args[2]['groups'][0]['records'][1]
            if defect=='source':args[2]['groups'][0]['source_sha256']['plan']='b'*64
            elif defect=='geometry':args[1]['edges'][1]['attribute_paths']=[[[0,0],[1,0]]]
            elif defect=='duplicate':row['axis_edge_id']='E1'
            elif defect=='negative_index':row['index_in_group']=-1
            elif defect=='pieces':row['source_projection']['pieces'][0]['length_mm']=20
            elif defect=='net_length':row['net_pipe_cut_length_mm']=10
            elif defect=='inline_complete':row['complete_horizontal_run_centerline_mm']=10
            else:row['source_projection']['joint_graphic_spans_added']=True
            with self.subTest(defect=defect),self.assertRaises(ValueError):collect(*args)
if __name__=='__main__':unittest.main()
