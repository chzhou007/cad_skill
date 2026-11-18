import copy,unittest
from rebuild_recovered_component_index import affected_profiles
class Tests(unittest.TestCase):
    def fixture(self):
        provider=dict(records=[dict(edge_id='A',classification='horizontal_only',correspondence_observations=[dict(domain='ordinary_local_graph',mapping_id='M',grouped_axis_edges=['A'],plan_edges=['P'])]),dict(edge_id='B',correspondence_observations=[])])
        inventory=dict(added_components=[dict(edge_id=e,source_top_handle=e)for e in('A','B')],components=[dict(edge_id=e,equipment_type='balancing_valve')for e in('A','B')]);plan={'1':[dict(edge_id='P',equipment_type='balancing_valve')]};return provider,inventory,plan,dict(records=[]),[],dict(edges=[dict(edge_id='A',floor_start=1,floor_end=1),dict(edge_id='B',floor_start=2,floor_end=2)])
    def test_existing_profile_is_rechecked_and_unmatched_edge_remains_unmatched(self):
        args=self.fixture();before=copy.deepcopy(args);r=affected_profiles(*args);self.assertEqual(r[0]['status'],'current_native_component_profiles_agree');self.assertEqual(r[1]['status'],'previous_unmatched_scope_retained');self.assertTrue(all(x['new_correspondence']is False for x in r));self.assertEqual(args,before)
    def test_profile_difference_and_competing_provider_do_not_inherit_confirmation(self):
        for mode in('profile','competing','grouped'):
            a=list(self.fixture())
            if mode=='profile':a[2]['1'].append(dict(edge_id='P',equipment_type='球阀'))
            elif mode=='competing':a[0]['records'][0]['correspondence_observations']*=2
            else:a[0]['records'][0]['correspondence_observations'][0]['grouped_axis_edges']=['A','C']
            with self.subTest(mode=mode),self.assertRaises(ValueError):affected_profiles(*a)
    def test_native_member_allocation_must_cover_exact_component_population(self):
        a=list(self.fixture());o=a[0]['records'][0]['correspondence_observations'][0];o.update(domain='reconstructed_member_graph',plan_edges=['MEMBER:P']);a[3]['records']=[dict(scoped_graph=dict(edges=[dict(edge_id='MEMBER:P',candidate_axis_edge='A',component_ids=['C'])]))];a[4].append(dict(device_name='C',equipment_type='平衡阀'));self.assertEqual(affected_profiles(*a)[0]['plan_profile'],[{'balancing_valve':1}]);a[4].clear()
        with self.assertRaises(ValueError):affected_profiles(*a)
    def test_identical_edge_IDs_on_other_floors_never_substitute_for_the_current_plan(self):
        a=list(self.fixture());a[5]['edges'][0].update(floor_start=2,floor_end=2)
        with self.assertRaisesRegex(ValueError,'exact horizontal floor'):affected_profiles(*a)
        a[2]['2']=a[2]['1'];self.assertEqual(affected_profiles(*a)[0]['plan_floor'],'2')
        a[0]['records'][0]['correspondence_observations'][0]['floor']=1
        with self.assertRaisesRegex(ValueError,'exact horizontal floor'):affected_profiles(*a)
if __name__=='__main__':unittest.main()
