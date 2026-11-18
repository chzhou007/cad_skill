import copy,unittest
from test_compound_bridge_context import fixture as old_fixture
from alias_member_bridge_context import collect,SOURCE_MODE
def fixture():
    raw,view,proof,b,prior=old_fixture();h='a'*64;q='b'*64
    proof.update(mode=SOURCE_MODE,parent_alias_interfaces_independently_replayed=True,all_vertical_attributes_from11=True,whole_centerline_lengths_assigned=0,reading_projection_sha256=q)
    proof['source_hashes'].update(plan_graph=h,axis_graph=h)
    proof['records'][0]['source_hashes']=dict(proof['source_hashes'],original_plan_graph=h,plan_graph=q)
    prior.pop('compound_member_interfaces');prior['alias_member_interfaces']=dict(source_bindings=dict(native_proof=h,plan_graph=h,axis_local_graph=h),records=[])
    return raw,view,proof,b,prior
class Tests(unittest.TestCase):
    def test_source_domains_and_original_component_identities_preserved(self):
        a=fixture();before=copy.deepcopy(a);r=collect(*a);self.assertEqual(a,before);self.assertEqual(r['records'][0]['nominal_mm'],300);self.assertEqual(r['complete_lengths_assigned'],0);self.assertTrue(r['all_vertical_attributes_from11']);self.assertFalse(r['human_accepted'])
    def test_wrong_private_source_equal_count_wrong_component_and_complete_length_promotion_fail(self):
        for kind in('domain','component','length','owner'):
            a=fixture()
            if kind=='domain':a[2]['records'][0]['source_hashes']['original_plan_graph']='stale'
            elif kind=='component':a[2]['records'][0]['component_correspondences'][0]['axis']['device_name']='wrong'
            elif kind=='length':a[2]['records'][0]['whole_centerline_length_mm']=30
            else:a[4]['alias_member_interfaces']['records']=[dict(axis_edge_id='E')]
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(*a)
if __name__=='__main__':unittest.main()
