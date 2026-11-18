import copy,unittest
from guarded_cycle_provider_inventory import inherit
class Tests(unittest.TestCase):
    def fixture(self):
        obs=dict(provider='cycle_gate_plan_runs',mapping_id='M');remaining=dict(edge_id='A',next_scope='existing_DN_conflict_source_scope_reconciliation',attributes={},correspondence_observations=[obs],complete_centerline=True)
        original=dict(records=[dict(edge_id='A',has_existing_correspondence=True,correspondence_observations=[obs])],new_cycle_axis_edges=['A'],ordinary_junction_mappings={'2':{'p':'a','old':'old-axis'}},remaining_horizontal_attributes=[remaining],member_domain_observations=[dict(id='untouched-member')],counts={},current_horizontal_frontier={})
        cycles=dict(floors={'2':dict(new_junction_mapping={'p':'a'},records=[dict(iso_edges=['A'],plan_start='p',plan_end='old')])});guard=dict(records=[dict(axis_edge_id='A',mapping_id='M')]);effective=[dict(edge_id='A',values=dict(cycle_carrier_hold_status='physical_member_identity_unproved'))];return original,cycles,guard,effective
    def test_graphic_candidates_are_removed_from_active_ordinary_map_and_retained_as_history(self):
        a=self.fixture();before=copy.deepcopy(a);r=inherit(*a);self.assertEqual(r['counts']['existing_correspondence_edges'],0);self.assertEqual(r['ordinary_junction_mappings']['2'],{'old':'old-axis'});self.assertEqual(r['held_graphic_junction_mappings'],{'2':{'p':'a'}});self.assertTrue(r['records'][0]['graphic_candidate_correspondence_observations']);self.assertFalse(r['remaining_horizontal_attributes'][0]['complete_centerline']);self.assertEqual(a,before)
    def test_wrong_provider_or_restored_cycle_fields_rejected(self):
        for kind in('member','restore'):
            a=self.fixture()
            if kind=='member':a[0]['records'][0]['correspondence_observations'][0]['provider']='verified_member_provider'
            else:a[3][0]['values']['cycle_gate_complete_centerline_mm']=10
            with self.subTest(kind=kind),self.assertRaises(ValueError):inherit(*a)
if __name__=='__main__':unittest.main()
