import copy,unittest
from recovered_component_provider_inventory import inherit
class Tests(unittest.TestCase):
    def fixture(self):
        original=dict(records=[dict(edge_id='E',has_existing_correspondence=True)],ordinary_junction_mappings={'1':{'A':'B'}},member_domain_observations=[dict(member_id='M')],remaining_horizontal_attributes=[dict(edge_id='E',next_scope='unknown_length')],current_horizontal_frontier={'records':['keep']},counts={'existing_correspondence_edges':1})
        audit=dict(output_instances=2);proof=dict(complete_parent_and_native_inventory_replayed=True,pipe_graph_restoration_exact=True,new_correspondences_assigned=0,physical_parameters_assigned=0,human_accepted=False,audit=audit,affected_component_profiles=[dict(status='current_native_component_profiles_agree',new_correspondence=False)],inputs=dict(native_inventory={'sha256':'native'},native_axis_graph={'sha256':'axis'}),rendered_graph_sha256='rendered',component_rows_added=1,unresolved_native_components=[{'source_handle':'unresolved'}]);graph=dict(instances=[{'id':'old'},{'id':'new'}],sourceRecoveredNativeComponentIndex=audit);return original,proof,graph
    def test_all_existing_providers_members_and_unknown_tasks_are_exact(self):
        a=self.fixture();before=copy.deepcopy(a);r=inherit(*a)
        for key in('records','ordinary_junction_mappings','member_domain_observations','remaining_horizontal_attributes','current_horizontal_frontier'):self.assertEqual(r[key],a[0][key])
        self.assertEqual(r['counts']['existing_correspondence_edges'],1);self.assertEqual(r['counts']['rendered_component_instances'],2);self.assertEqual(a,before);self.assertEqual(r['current_component_inventory']['unresolved_native_components'],[{'source_handle':'unresolved'}])
    def test_incomplete_replay_wrong_index_profile_conflicts_and_invented_values_fail(self):
        for mode in('parent','graph','profile','parameter','mapping','HIL'):
            a=list(self.fixture())
            if mode=='parent':a[1]['complete_parent_and_native_inventory_replayed']=False
            elif mode=='graph':a[2]['instances'].pop()
            elif mode=='profile':a[1]['affected_component_profiles'][0]['status']='conflict'
            elif mode=='parameter':a[1]['physical_parameters_assigned']=1
            elif mode=='mapping':a[1]['new_correspondences_assigned']=1
            else:a[1]['human_accepted']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):inherit(*a)
if __name__=='__main__':unittest.main()
