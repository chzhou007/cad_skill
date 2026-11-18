import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from test_rebuild_bounded_main_complete_extents import case
from rebuild_bounded_main_complete_extents import scope,MODE
from bounded_main_complete_extent_context import collect

def fixture():
    args=case();row,r,_=scope(*args);prior_scope=args[2]
    r.update(mapping=row,prior_bounded_scope=copy.deepcopy(prior_scope),source_hashes={})
    raw=args[1];view=copy.deepcopy(raw);view['instances']=[]
    proof=dict(mode=MODE,current_provider_inventory_replayed=True,bounded_ancestor_native_replayed=True,
        selected_old_and_current_plan_scopes_exact=True,existing_correspondences_unchanged=True,DN_observations_preserved=True,
        local_graphs_mutated=False,source_paths_mutated=False,human_accepted=False,installed_lengths_assigned=0,
        net_pipe_cut_lengths_assigned=0,records=[r])
    return [raw,view,proof,dict(bounded_parent_proof='parent'),dict(anchor_bounded_mains=dict(records=[prior_scope],source_bindings=dict(native_proof='parent')))]

class Tests(unittest.TestCase):
    def test_complete_metric_keeps_original_bounded_owner_and_component_identity(self):
        args=fixture();before=copy.deepcopy(args);r=collect(*args)
        self.assertEqual(args,before);self.assertEqual(r['axis_edges'],1);self.assertTrue(r['DN_observations_preserved'])
        self.assertEqual(r['records'][0]['complete_horizontal_centerline_route_mm'],10)
    def test_parent_scope_graph_change_or_physical_promotion_rejected(self):
        for kind in('scope','graph','physical','replay'):
            args=fixture()
            if kind=='scope':args[4]['anchor_bounded_mains']['records'][0]['nominal_mm']=100
            elif kind=='graph':args[1]['edges'][0]['end_node_id']='other'
            elif kind=='physical':args[2]['records'][0]['whole_installed_length_mm']=10
            else:args[2]['current_provider_inventory_replayed']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(*args)
    def test_source_backed_carrier_supersedes_only_member_value_not_old_observation(self):
        args=fixture();r=args[2]['records'].pop();r.update(complete_horizontal_centerline_route_mm=None,candidate_T_to_T_projection_mm=10,reason='compound_carrier_requires_its_member_identity_not_scalar_main_extent',carrier_evidence=[{'source_LINE':'native'}]);args[2]['quarantined_records']=[r]
        result=collect(*args);self.assertEqual(result['axis_edges'],0);self.assertEqual(result['quarantined_axis_edges'],1)
        self.assertEqual(result['quarantined_records'][0]['prior_bounded_scope']['nominal_mm'],300)
        self.assertIsNone(result['quarantined_records'][0]['complete_horizontal_centerline_route_mm'])
    def test_orthogonal_fragment_cannot_bypass_same_or_missing_member_level_literal(self):
        args=fixture();args[2]['records'][0]['compound_fragment_scope']=dict(direct_native_evidence=dict(observations=[dict(parenthesized_source_value='3.200')]),excluded_unbound_fragment_proposals=[dict(declaration=dict(members=[dict(source_level_text='3.600'),dict(source_level_text='3.000')]))])
        self.assertEqual(collect(*args)['axis_edges'],1)
        for literal in('3',None):
            args[2]['records'][0]['compound_fragment_scope']['direct_native_evidence']['observations'][0]['parenthesized_source_value']=literal
            with self.subTest(literal=literal),self.assertRaises(ValueError):collect(*args)
if __name__=='__main__':unittest.main()
