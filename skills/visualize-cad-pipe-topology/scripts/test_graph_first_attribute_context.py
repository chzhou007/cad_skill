import copy,json,unittest
from graph_first_attribute_context import collect,METRIC_MODE,VERTICAL_MODE

def fixture():
    a,b,c,d=('a'*64,'b'*64,'c'*64,'d'*64)
    horizontal=dict(edge_id='H',system='supply',start_node_id='A',end_node_id='B',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[10,0]]],equipment_inventory=[])
    v=dict(edge_id='V',system='return',start_node_id='C',end_node_id='D',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[0,2],[2,4],[2,6]]],equipment_inventory=[])
    raw=dict(metadata=dict(source_sha256=a),edges=[horizontal,v]);view=dict(copy.deepcopy(raw),instances=[])
    seed=dict(edge_id='V',path_index=0,segment_index=2,system='return',nominal_mm=80,scope_points=[[2,4],[2,6]],observations=[dict(nominal_mm=80,source_text=dict(source_sha256=a,handle='T'))])
    inherited=dict(edge_id='V',path_index=0,segment_index=0,system='return',nominal_mm=80,scope_points=[[0,0],[0,2]],seed_record=seed,
        continuity_evidence=dict(bends=[dict(source_arms=2,physical_T_crossed=False)]),annotation_guard=dict(other_in_scope_DN_annotations=[],F_crossings=[]),whole_edge_DN_assigned=False,physical_length_mm=None,whole_edge_physical_length_mm=None,human_accepted=False)
    row=dict(axis_edge_id='H',mapping_id='M',plan_edge_id='P',floor=2,system='supply',axis_nodes=['A','B'],axis_attribute_paths=horizontal['attribute_paths'],complete_horizontal_centerline_mm=10,
        projection=dict(value_mm=10,pieces=[dict(length_mm=10)]),nominal_mm=None,physical_installed_length_mm=None,net_pipe_cut_length_mm=None,human_accepted=False)
    metrics=dict(mode=METRIC_MODE,cycle_correspondences_independently_replayed=True,original_metric_readers_reused=True,local_graphs_changed=False,human_accepted=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,
        inputs=dict(axis_graph=dict(sha256=b),plan_source=dict(sha256=a),cycle_proof=dict(path='proof',sha256=b)),records=[row],counts=dict(complete_horizontal_centerlines=1))
    vertical=dict(mode=VERTICAL_MODE,original_native_annotations_independently_replayed=True,original_direction_routing_independently_replayed=True,original_axis_graphs_unchanged=True,all_vertical_values_from11=True,horizontal_plan_attributes_changed=False,human_accepted=False,
        crossed_physical_Ts=0,whole_edge_DN_assigned=0,physical_lengths_assigned=0,inputs=dict(raw_axis_graph=dict(sha256=c),graph=dict(sha256=b),source=dict(sha256=a),annotations=dict(sha256=a)),records=[inherited],counts=dict(new_inherited_vertical_domains=1))
    prior=dict(source_graph_sha256=c,rendered_graph_sha256=d,axis_vertical_segment_DN=dict(records=[copy.deepcopy(seed)],source_bindings=dict(native_vertical_DN_proof=a)))
    bindings=dict(raw_axis_graph=c,rendered_graph=d,cycle_metric_proof=a,vertical_inheritance_proof=b)
    return raw,view,metrics,vertical,bindings,prior

class Tests(unittest.TestCase):
    def test_native_tuple_indices_survive_persisted_viewer_and_fresh_replay(self):
        a=fixture();a[2]['records'][0]['plan_subdivision_reading_projection']=dict(original_indices=[[(0,0),(1,0)]])
        before=copy.deepcopy(a);result=collect(*a)
        self.assertEqual(result,json.loads(json.dumps(result)))
        self.assertEqual(result['cycle_records'][0]['plan_subdivision_reading_projection']['original_indices'],[[[0,0],[1,0]]])
        self.assertEqual(a,before)
    def test_two_independent_scopes_preserve_old_context_and_unknowns(self):
        a=fixture();before=copy.deepcopy(a);r=collect(*a)
        self.assertEqual(r['cycle_records'][0]['complete_horizontal_centerline_mm'],10)
        self.assertEqual(r['vertical_records'][0]['nominal_mm'],80);self.assertEqual(r['all_current_vertical_domain_count'],2)
        self.assertIsNone(r['cycle_records'][0]['nominal_mm']);self.assertEqual(a,before)
    def test_cross_system_seed_T_barrier_whole_value_or_existing_owner_rejected(self):
        for kind in ('system','seed','T','whole','existing','repeat'):
            a=fixture()
            if kind=='system':a[3]['records'][0]['system']='supply'
            elif kind=='seed':a[3]['records'][0]['seed_record']['segment_index']=1
            elif kind=='T':a[3]['records'][0]['continuity_evidence']['bends'][0]['source_arms']=3
            elif kind=='whole':a[2]['records'][0]['nominal_mm']=300
            elif kind=='existing':a[5]['other_owner']=dict(records=[dict(axis_edge_id='H')])
            else:a[3]['records'].append(copy.deepcopy(a[3]['records'][0]))
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(*a)

if __name__=='__main__':unittest.main()
