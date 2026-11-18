import copy,unittest
from alias_aware_provider_inventory import inventory
from alias_member_circle_interfaces import MODE as SOURCE_MODE
from alias_member_interface_context import MODE as CONTEXT_MODE

def fixture():
    original=dict(records=[dict(edge_id='E',classification='horizontal_only',correspondence_observations=[],has_existing_correspondence=False),dict(edge_id='V',classification='mixed_horizontal_vertical',correspondence_observations=[],has_existing_correspondence=False)],counts={},inputs=dict(historical='retained'),ordinary_junction_mappings={'2':{'P':'A'}},member_domain_observations=[],new_correspondences_assigned=0)
    r=dict(axis_edge_id='E',mapping_id='M',plan_member_edge_id='MEMBER:S:E',member_scope_id='MEMBER:S',axis_nodes=['A','B'])
    proof=dict(mode=SOURCE_MODE,inputs=dict(provider_inventory=dict(sha256='b'*64)),ordinary_junction_mapping_extended=False,human_accepted=False,records=[r],member_local_graph=dict(edges=[dict(edge_id='MEMBER:S:E')]))
    context=dict(mode=CONTEXT_MODE,source_bindings=dict(native_proof='c'*64),records=[copy.deepcopy(r)],human_accepted=False)
    effective=[dict(edge_id='E',values=dict(diameter_nominal_mm=300,alias_member_complete_centerline_mm=1000)),dict(edge_id='V',values={})]
    baseline=dict(records=[dict(edge_id='E',floor=2,next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path')]);bindings=dict(native_proof='c'*64,original_inventory='b'*64)
    return original,proof,context,effective,baseline,bindings

class Tests(unittest.TestCase):
    def test_member_provider_inherited_without_entering_ordinary_anchors(self):
        args=fixture();before=copy.deepcopy(args);result=inventory(*args);self.assertEqual(args,before);self.assertEqual(result['ordinary_junction_mappings'],args[0]['ordinary_junction_mappings']);self.assertEqual(result['counts']['existing_correspondence_edges'],1);self.assertEqual(result['counts']['pure_horizontal_complete_DN_and_centerline'],1);self.assertEqual(result['current_horizontal_frontier']['pure_horizontal_remaining_attributes'],0);self.assertEqual(result['counts']['mixed_edges_without_any_correspondence'],1)
        self.assertEqual(result['member_domain_observations'][0]['domain'],'physical_member_graph');self.assertEqual(result['DN_or_length_values_assigned'],0);self.assertIsNone(result['mixed_unmapped_horizontal_extent_count'])
    def test_competing_provider_namespace_and_missing_old_completion_fail(self):
        for kind in('existing','namespace','regression'):
            args=fixture()
            if kind=='existing':args[0]['records'][0]['has_existing_correspondence']=True
            elif kind=='namespace':args[1]['records'][0]['plan_member_edge_id']='ordinary-T'
            else:args[3][0]['values']={};args[4]['records']=[]
            with self.assertRaises(ValueError):inventory(*args)
if __name__=='__main__':unittest.main()
