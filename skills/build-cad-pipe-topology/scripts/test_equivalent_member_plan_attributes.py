import copy,unittest
from equivalent_member_plan_attributes import apply
from test_native_main_endpoint_extent import fixture as inherited_fixture
class Tests(unittest.TestCase):
    def fixture(self,nominal=300.,complete=10.):
        plan,axis,row,projection=inherited_fixture();row.update(native_metric=dict(projection=projection),drawn_plan_projection_mm=10.,complete_horizontal_centerline_mm=complete,incomplete_reasons=[]if complete is not None else['source_length_explicitly_incomplete'],source_member_observation_ids=[])
        b=dict(complete_parent_rechecked=True,source_graphs_mutated=False,physical_pipe_count_inferred=False,DN_used_for_mapping=False,human_accepted=False,records=[row],counts=dict(new_axis_intervals=1));dn=dict(E=dict(edge_id='E',system='supply',scope_paths=copy.deepcopy(plan['edges'][0]['attribute_paths']),nominal_mm=nominal,status='direct_plan_DN'if nominal else'conflict',lineage=[]));return b,dn,plan,axis,copy.deepcopy(axis),copy.deepcopy(axis)
    def test_exact_existing_native_plan_DN_is_retained_on_independent_current_extent(self):
        args=self.fixture();before=copy.deepcopy(args);r=apply(*args,[0,45,135])[0]
        self.assertEqual(r['nominal_mm'],300.);self.assertEqual(r['complete_horizontal_centerline_mm'],10.);self.assertFalse(r['DN_used_for_mapping']);self.assertFalse(r['related_HIL_confirmation_inherited']);self.assertEqual(args,before)
    def test_generic_extent_scalar_never_completes_an_explicitly_incomplete_length(self):
        args=self.fixture(300.,None);r=apply(*args,[0,45,135])[0]
        self.assertEqual(r['nominal_mm'],300.);self.assertIsNone(r['complete_horizontal_centerline_mm']);self.assertTrue(r['incomplete_reasons']);self.assertIsNone(r['installed_length_mm'])
    def test_conflict_and_annotation_unknown_remain_separate_not_guessed_from_axis(self):
        args=self.fixture(None)
        for state,expected in [('conflict','native_plan_DN_conflict'),('annotation_blocked','existing_native_annotation_provider_application_pending')]:
            args[1]['E']['status']=state;r=apply(*args,[0,45,135])[0];self.assertIsNone(r['nominal_mm']);self.assertEqual(r['DN_status'],expected);self.assertEqual(r['complete_horizontal_centerline_mm'],10.)
    def test_source_scope_or_rendered_identity_changes_fail_closed(self):
        for kind in('paths','system','node','duplicate','unreplayed'):
            args=list(self.fixture())
            if kind=='paths':args[1]['E']['scope_paths']=[[[0,0],[9,0]]]
            elif kind=='system':args[5]['edges'][0]['system']='return'
            elif kind=='node':args[5]['edges'][0]['start_node_id']='wrong'
            elif kind=='duplicate':args[0]['records'].append(copy.deepcopy(args[0]['records'][0]))
            else:args[0]['complete_parent_rechecked']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):apply(*args,[0,45,135])
    def test_fragment_DN_needs_native_gap_replay_and_never_assigns_gap_length(self):
        args=list(self.fixture(150.,None));paths=[[[0.,0.],[4.,0.]],[[6.,0.],[10.,0.]]]
        args[2]['edges'][0]['attribute_paths']=copy.deepcopy(paths);args[1]['E']['scope_paths']=copy.deepcopy(paths)
        with self.assertRaisesRegex(ValueError,'original crossover replay'):apply(*args,[0,45,135])
        args[0]['records'][0]['native_metric']['source_evidence']=dict(status='native_source_paths_and_excluded_crossovers_replayed',crossovers=[dict(source_gap='native-G')])
        r=apply(*args,[0,45,135])[0]
        self.assertEqual(r['nominal_mm'],150.);self.assertIsNone(r['complete_horizontal_centerline_mm']);self.assertFalse(r['native_extent_check']['source_gap_length_assigned'])
        args[2]['edges'][0]['attribute_paths'][-1][-1]=[9.,0.];args[1]['E']['scope_paths']=copy.deepcopy(args[2]['edges'][0]['attribute_paths'])
        with self.assertRaisesRegex(ValueError,'both T centres'):apply(*args,[0,45,135])
if __name__=='__main__':unittest.main()
