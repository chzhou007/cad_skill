import copy,unittest
from current_effective_provider import reconcile
from refresh_effective_provider import delta

def fixture():
    rows=[dict(edge_id=e,classification='horizontal_only'if e!='C'else'mixed_horizontal_vertical',has_existing_correspondence=e=='B',correspondence_observations=[])for e in ['A','B','C']]
    pending=dict(edge_id='A',floor=2,next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path',attributes={'old':True},known_whole_DN=None,complete_centerline=False)
    provider=dict(records=rows,remaining_horizontal_attributes=[pending],counts={},current_horizontal_frontier={},ordinary_junction_mappings={'2':{}},member_domain_observations=[],all_current_vertical_DN_domains=[{'native11':'unchanged'}],current_component_inventory={'count':7})
    values=[dict(edge_id='A',values=dict(diameter_nominal_mm=200,uniform_subroute_DN_scope_id='R')),dict(edge_id='B',values=dict(diameter_nominal_mm=300,ordered_group_complete_run_mm=1200)),dict(edge_id='C',values={})]
    context=dict(reviewed_uniform_subroute_DN=dict(records=[dict(axis_edge_id='A',nominal_mm=200,whole_horizontal_edge=True,source_scope_id='R')]))
    return provider,values,context

class CurrentProviderTests(unittest.TestCase):
    def test_actual_DN_snapshot_and_range_length_task_without_identity_inflation(self):
        p,v,c=fixture();old=copy.deepcopy((p,v,c));r=reconcile(p,v,c);self.assertEqual((p,v,c),old)
        a=r['remaining_horizontal_attributes'][0];self.assertEqual(a['attributes'],v[0]['values']);self.assertEqual(a['known_whole_DN'],200);self.assertFalse(a['complete_centerline']);self.assertEqual(a['next_scope'],'reviewed_range_per_edge_length_allocation_unresolved');self.assertEqual(r['records'],p['records']);self.assertEqual(r['all_current_vertical_DN_domains'],p['all_current_vertical_DN_domains']);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],1);self.assertEqual(r['counts']['current_effective_whole_DN_known'],2)
    def test_missing_population_stale_range_and_lost_old_complete_values_block(self):
        for kind in ['population','range','length']:
            p,v,c=fixture()
            if kind=='population':v.pop()
            elif kind=='range':v[0]['values']['uniform_subroute_DN_scope_id']='wrong'
            else:v[1]['values']['ordered_group_complete_run_mm']=None
            with self.subTest(kind=kind),self.assertRaises(ValueError):reconcile(p,v,c)
    def test_primary_DN_delta_cannot_promote_riser_partial_or_change_length(self):
        p=dict(member_records=[dict(axis_edge_id='A',member_kind='approach',nominal_mm=300,complete_horizontal_centerline_mm=1200),dict(axis_edge_id='R',member_kind='riser',nominal_mm=300,complete_horizontal_centerline_mm=None)])
        before=[dict(edge_id='A',values=dict(diameter_nominal_mm=None,length=1200)),dict(edge_id='R',values=dict(diameter_nominal_mm=None,length=None))];after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=300,diameter_text='DN300',diameter_status='native_complete_horizontal_member_approach_DN');self.assertEqual(delta(before,after,p)['primary_complete_member_DN_fills'],['A'])
        for kind in ['length','partial']:
            bad=copy.deepcopy(after)
            if kind=='length':bad[0]['values']['length']=1300
            else:bad[1]['values']['diameter_nominal_mm']=300
            with self.subTest(kind=kind),self.assertRaises(ValueError):delta(before,bad,p)

if __name__=='__main__':unittest.main()
