import copy,unittest
from axis_vertical_DN_context import collect
from axis_vertical_DN_batch import MODE
def fixture():
    e=dict(edge_id='E',system='return',start_node_id='A',end_node_id='B',attribute_paths=[[[0,0],[0,10]]],axis_riser_attributes=[dict(path_index=0,segment_index=0,nominal_mm=80)])
    raw=dict(metadata=dict(source_sha256='S'),edges=[e]);shown=copy.deepcopy(raw);prior=dict(source_graph_sha256='RAW',rendered_graph_sha256='VIEW');bindings=dict(raw_axis_graph='RAW',rendered_graph='VIEW',native_axis_graph='NATIVE',native_vertical_DN_proof='P')
    r=dict(edge_id='E',path_index=0,segment_index=0,system='return',scope_points=[[0,0],[0,10]],nominal_mm=80,whole_edge_DN_assigned=False,physical_length_mm=None,whole_edge_physical_length_mm=None,observations=[dict(nominal_mm=80,source_text=dict(source_sha256='S'))])
    proof=dict(mode=MODE,graph_mutated=False,horizontal_plan_attributes_changed=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False,source_sha256='S',graph_sha256='NATIVE',records=[r],counts=dict(qualified_vertical_segments=1),pending=[])
    return [raw,shown,proof,bindings,prior]
class Tests(unittest.TestCase):
    def test_vertical_values_retain_existing_domains_and_all_horizontal_raw_data(self):
        args=fixture();before=copy.deepcopy(args);r=collect(*args);self.assertEqual(args,before);self.assertEqual(r['new_axis_vertical_domains'],0);self.assertEqual(r['all_current_axis_vertical_domains'],1);self.assertTrue(r['existing_axis_segment_values_preserved']);self.assertFalse(r['records'][0]['related_HIL_confirmation_inherited'])
    def test_original_segment_orientation_system_and_previous_dn_are_checked(self):
        for failure in('points','system','old_dn'):
            args=fixture()
            if failure=='points':args[2]['records'][0]['scope_points'][1]=[1,10]
            elif failure=='system':args[2]['records'][0]['system']='supply'
            else:args[0]['edges'][0]['axis_riser_attributes'][0]['nominal_mm']=100
            with self.subTest(failure=failure),self.assertRaises(ValueError):collect(*args)
    def test_whole_length_promotion_and_wrong_source_do_not_compose(self):
        args=fixture();args[2]['records'][0]['physical_length_mm']=10
        with self.assertRaises(ValueError):collect(*args)
        args=fixture();args[2]['records'][0]['observations'][0]['source_text']['source_sha256']='OTHER'
        with self.assertRaises(ValueError):collect(*args)
if __name__=='__main__':unittest.main()
