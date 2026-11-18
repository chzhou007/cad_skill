import copy,unittest
from riser_header_provider_inventory import inherit,COMPLETE_FIELDS
class Tests(unittest.TestCase):
    def fixture(self):
        obs=dict(provider='cycle_gate_plan_runs',mapping_id='C-MAP');rows=[dict(edge_id='C',classification='horizontal_only',has_existing_correspondence=False,correspondence_observations=[],graphic_candidate_correspondence_observations=[obs]),dict(edge_id='M',classification='horizontal_only',has_existing_correspondence=False,correspondence_observations=[]),dict(edge_id='K',classification='horizontal_only',has_existing_correspondence=True,correspondence_observations=[{'old':'K'}]),dict(edge_id='V',classification='mixed_horizontal_vertical',has_existing_correspondence=True,correspondence_observations=[{'old':'V'}])]
        original=dict(records=rows,ordinary_junction_mappings={'2':{'OLD':'AXOLD'}},held_graphic_junction_mappings={'2':{'P':'AXP'}},held_cycle_axis_edges=['C'],new_cycle_axis_edges=[],member_domain_observations=[{'old_member':'KEEP'}],counts={},current_horizontal_frontier={},remaining_horizontal_attributes=[dict(edge_id=e,floor=2,next_scope='old')for e in('C','M')])
        app=dict(cycle_clearances=[dict(axis_edge_id='C',mapping_id='C-MAP',complete_horizontal_centerline_mm=1000)],member_records=[dict(axis_edge_id='M',mapping_id='M-MAP',member_scope_id='MEMBER-RISER:X',plan_member_edge_id='MEMBER-RISER:X:approach',floor=2)])
        effective=[dict(edge_id='C',values=dict(cycle_gate_mapping_id='C-MAP',cycle_gate_complete_centerline_mm=1000,cycle_carrier_clearance_status='native_atom_origin_replayed_scope_cleared')),dict(edge_id='M',values=dict(riser_header_mapping_id='M-MAP',riser_header_member_scope='MEMBER-RISER:X',riser_header_plan_DN_mm=300,riser_header_complete_centerline_mm=500)),dict(edge_id='K',values=dict(diameter_nominal_mm=80,**{COMPLETE_FIELDS[0]:1000})),dict(edge_id='V',values=dict(unbranched_vertical_DN_segment_count=108))]
        return original,app,effective
    def test_complete_inventory_retains_old_prefix_and_separates_member_namespace(self):
        old,a,e=self.fixture();before=copy.deepcopy(old);r=inherit(old,a,e);self.assertEqual(old,before);self.assertEqual(r['counts']['existing_correspondence_edges'],4);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],2);self.assertEqual(r['counts']['pure_horizontal_remaining_attributes'],1);self.assertEqual(r['member_domain_observations'][0],old['member_domain_observations'][0]);self.assertEqual(r['ordinary_junction_mappings']['2'],{'OLD':'AXOLD','P':'AXP'});self.assertNotIn('MEMBER-RISER:X',r['ordinary_junction_mappings']['2']);self.assertEqual(r['records'][-1],old['records'][-1])
    def test_adopted_member_with_unknown_connector_is_not_unmatched(self):
        old,a,e=self.fixture();e[1]['values']['riser_header_complete_centerline_mm']='';r=inherit(old,a,e);row=next(x for x in r['remaining_horizontal_attributes']if x['edge_id']=='M');self.assertEqual(row['next_scope'],'known_riser_member_connector_length_unproved');self.assertEqual(row['known_whole_DN'],300);self.assertEqual(len(row['correspondence_observations']),1)
    def test_stale_values_competing_identity_or_regressed_old_metric_fail(self):
        for kind in('stale','compete','regression','anchor'):
            old,a,e=self.fixture()
            if kind=='stale':e[0]['values']['cycle_gate_complete_centerline_mm']=1001
            elif kind=='compete':old['records'][1]['has_existing_correspondence']=True
            elif kind=='regression':e[2]['values']={}
            else:old['ordinary_junction_mappings']['2']['CONFLICT']='AXP'
            with self.subTest(kind=kind),self.assertRaises(ValueError):inherit(old,a,e)
if __name__=='__main__':unittest.main()
