import copy,unittest
from compound_bridge_context import collect,SOURCE_MODE

def fixture():
    h='a'*64;b=dict(axis_graph=h,rendered_graph=h,native_proof=h,member_interfaces=h)
    e=dict(edge_id='E',start_node_id='A',end_node_id='B',system='supply',floor_start=3,floor_end=3,attribute_paths=[[[0,0],[30,0]]],equipment_inventory=[dict(count=1,device_names=['球阀1'])])
    raw=dict(edges=[e]);view=copy.deepcopy(raw);view['edges'][0]['equipment_inventory'][0]['device_names']=['Valve1'];view['instances']=[dict(id='I1',edge_id='E',source_device_name='球阀1',name='Valve1',source_top_handle='HV')]
    prior=dict(source_graph_sha256=h,rendered_graph_sha256=h,compound_member_interfaces=dict(source_bindings=dict(native_proof=h),records=[]),axis_vertical_segment_DN=dict(records=[dict(edge_id='OTHER',path_index=0,segment_index=2,nominal_mm=80)]))
    hashes=dict(raw_axis_graph=h,member_interfaces=h,plan_source=h,axis_source=h)
    r=dict(axis_edge_id='E',mapping_id='M',source_parent_plan_edge='P',floor=3,system='supply',nominal_mm=300.,axis_nodes=['A','B'],axis_attribute_paths=e['attribute_paths'],source_hashes=hashes,plan_pipe_projection_mm=20.,plan_pieces=[dict(kind='native_pipe',measured_plan_pipe_projection_mm=20.,physical_inline_length_mm=None),dict(kind='native_inline_joint',measured_plan_pipe_projection_mm=None,physical_inline_length_mm=None)],component_correspondences=[dict(axis=dict(device_name='球阀1'),plan=dict(device_name='球阀P'))],whole_centerline_length_mm=None,installed_whole_length_mm=None,net_pipe_cut_length_mm=None,physical_elevation_mm=None,inline_graphic_spans_used_as_physical_length=False)
    proof=dict(mode=SOURCE_MODE,DN_used_for_mapping=False,source_drawing_graphs_unchanged=True,installed_lengths_assigned=0,human_accepted=False,source_hashes=hashes,records=[r],counts=dict(qualified_bridges=1),member_local_graph=dict(nodes=[{},{}],edges=[{}],external_ports=[]))
    return raw,view,proof,b,prior
class Tests(unittest.TestCase):
    def test_source_qualified_bridge_preserves_prior_vertical_context_and_components(self):
        a=fixture();before=copy.deepcopy(a);r=collect(*a);self.assertEqual(a,before);self.assertEqual(r['axis_edges'],1);self.assertEqual(r['records'][0]['component_instance_identities'][0]['source_device_name'],'球阀1');self.assertEqual(r['installed_lengths_assigned'],0)
    def test_equal_count_wrong_component_identity_and_legacy_owner_fail(self):
        a=fixture();a[2]['records'][0]['component_correspondences'][0]['axis']['device_name']='OTHER'
        with self.assertRaises(ValueError):collect(*a)
        a=fixture();a[0]['edges'][0]['cross_view_attributes']={'mapping':'OLD'}
        with self.assertRaises(ValueError):collect(*a)
    def test_changed_native_member_binding_or_zero_inline_length_fails(self):
        a=fixture();a[2]['source_hashes']['member_interfaces']='b'*64
        with self.assertRaises(ValueError):collect(*a)
        a=fixture();a[2]['records'][0]['plan_pieces'][1]['physical_inline_length_mm']=0
        with self.assertRaises(ValueError):collect(*a)
if __name__=='__main__':unittest.main()
