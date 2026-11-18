import copy,unittest
from ordered_branch_attribute_context import collect
def fixture():
    h='a'*64;edge=dict(edge_id='E',start_node_id='V',end_node_id='T',system='supply',start_port_id='VP',end_port_id=None,source_insert_handle='M',attribute_paths=[[[0,0],[1,0],[5,0]]])
    graph=dict(edges=[edge],sourceFullPlanBatchAttributes=dict(source_hashes=dict(identity_graph=h)))
    row=dict(mapping_id='MAP',parent_mapping_id='GROUP',floor=3,system='supply',routes=dict(plan=dict(edges=['P'],terminal_id='BOUNDARY'),iso=dict(edges=['E'])),iso_snapshot=dict(edges=[copy.deepcopy(edge)]),plan_snapshot=dict(edges=[dict(edge_id='P',attribute_paths=[[[10,0],[20,0]]])]),
        main_anchor=dict(plan_node='PT',axis_node='T'),physical_port_verified=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,remote_equipment_identity_inferred=False,
        plan_horizontal_projection=dict(value_mm=10,pieces=[dict(length_mm=10)],installed_whole_edge_length_mm=None),whole_horizontal_plan_route_mm=None,circle_radius_added_to_metric=False,axis_marker_centre_span_added_to_metric=False,
        axis_drawing_port=dict(port_id='VP',display_segment_index=0),plan_drawn_nominal_mm=250,plan_DN_records=[],local_DN_evidence_status='retained')
    proof=dict(original_local_graphs_mutated=False,original_axis_graph_mutated=False,whole_axis_DN_assigned=0,physical_whole_edge_lengths_assigned=0,anchor_feedback_into_its_own_parent=False,pending=[],records=[row],source_hashes=dict(parent_graph=h,axis_graph=h,axis_source=h,plan_source_3=h,plan_graph_3=h))
    return graph,copy.deepcopy(graph),proof,dict(axis_graph=h,rendered_graph=h,branch_proof=h)
class Tests(unittest.TestCase):
    def test_partial_plan_metric_and_DN_preserve_graph_and_unknown_whole_axis_values(self):
        args=fixture();before=copy.deepcopy(args);result=collect(*args);self.assertEqual(result['axis_edges'],1);row=result['records'][0];self.assertEqual(row['known_plan_pipe_XY_mm'],10);self.assertEqual(row['plan_drawn_nominal_mm'],250);self.assertIsNone(row['whole_axis_physical_length_mm']);self.assertFalse(row['whole_axis_DN_selected']);self.assertEqual(args,before)
    def test_source_geometry_owner_metric_and_port_promotions_fail(self):
        for defect in('source','geometry','owner','metric','whole'):
            args=list(fixture())
            if defect=='source':args[2]['source_hashes']['parent_graph']='changed'
            elif defect=='geometry':args[1]['edges'][0]['start_port_id']='wrong'
            elif defect=='owner':args[0]['edges'][0]['cross_view_attributes']={'prior':True}
            elif defect=='metric':args[2]['records'][0]['plan_horizontal_projection']['value_mm']=20
            else:args[2]['records'][0]['whole_axis_DN_selected']=True
            with self.subTest(defect=defect),self.assertRaises(ValueError):collect(*args)
if __name__=='__main__':unittest.main()
