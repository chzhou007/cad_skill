import copy,unittest
from cohort_member_provider_inventory import inherit
class Tests(unittest.TestCase):
    def fixture(self):
        rows=[dict(edge_id=e,classification='horizontal_only',has_existing_correspondence=e=='OLD',correspondence_observations=[dict(provider='prior')]if e=='OLD'else[])for e in('OLD','A','B')]
        front=[dict(edge_id=e,floor=3,next_scope='unmatched',attributes={})for e in('A','B')]
        original=dict(records=rows,ordinary_junction_mappings={'3':{'P':'I'}},member_domain_observations=[dict(domain='old_member',member_id='keep')],remaining_horizontal_attributes=front,counts={},current_horizontal_frontier={})
        target=dict(axis_edge_id='A',plan_edge_id='PA',mapping_id='M',floor=3,nominal_mm=150.,complete_horizontal_centerline_mm=100.,source_member_observation_ids=['scope'],DN_status='native_specific_plan_DN_reapplied')
        app=dict(records=[target],complete_source_batch_replayed=True,human_accepted=False)
        batch=dict(complete_parent_rechecked=True,floor=3,records=[dict(iso_edges=['A'],plan_edges=['PA'],mapping_id='M')],native_bounded_batch=dict(new_junction_mapping={'Q':'J'}))
        values=[dict(edge_id='OLD',values=dict(diameter_nominal_mm=80,full_plan_complete_centerline_mm=10)),dict(edge_id='A',values=dict(cohort_member_mapping_id='M',cohort_member_plan_DN_mm=150.,cohort_member_complete_centerline_mm=100.)),dict(edge_id='B',values={})]
        # Use an actual supported existing length field, avoiding synthetic
        # completeness that would weaken the regression guard.
        from alias_aware_provider_inventory import COMPLETE_FIELDS
        values[0]['values'][COMPLETE_FIELDS[0]]=10
        return original,app,batch,values
    def test_adds_ordinary_domains_preserves_every_prior_member_and_input(self):
        a=self.fixture();before=copy.deepcopy(a);r=inherit(*a)
        self.assertEqual(r['counts']['existing_correspondence_edges'],2);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],2);self.assertEqual(len(r['remaining_horizontal_attributes']),1);self.assertEqual(r['member_domain_observations'],a[0]['member_domain_observations']);self.assertEqual(r['records'][0],a[0]['records'][0]);self.assertEqual(a,before);self.assertEqual(r['ordinary_junction_mappings']['3']['Q'],'J')
    def test_conflicting_DN_and_partial_length_are_not_unmatched_or_zero(self):
        a=self.fixture();a[1]['records'][0].update(nominal_mm=None,DN_status='native_plan_DN_conflict',complete_horizontal_centerline_mm=None);a[3][1]['values'].update(cohort_member_plan_DN_mm='',cohort_member_complete_centerline_mm='')
        r=inherit(*a);p=next(x for x in r['remaining_horizontal_attributes']if x['edge_id']=='A');self.assertEqual(p['next_scope'],'known_cohort_plan_DN_conflict');self.assertFalse(p['complete_centerline']);self.assertTrue(r['records'][1]['has_existing_correspondence'])
    def test_competing_old_writer_or_identity_wrong_values_and_missing_target_fail(self):
        for mode in('writer','junction','vertical','metric','population','unreplayed'):
            a=list(self.fixture())
            if mode=='writer':a[0]['records'][1]['has_existing_correspondence']=True
            elif mode=='junction':a[2]['native_bounded_batch']['new_junction_mapping']={'Q':'I'}
            elif mode=='vertical':a[0]['records'][1]['classification']='mixed_horizontal_vertical'
            elif mode=='metric':a[3][1]['values']['cohort_member_complete_centerline_mm']=999
            elif mode=='population':a[2]['records']=[]
            else:a[2]['complete_parent_rechecked']=False
            with self.subTest(mode=mode),self.assertRaises(ValueError):inherit(*a)
if __name__=='__main__':unittest.main()
