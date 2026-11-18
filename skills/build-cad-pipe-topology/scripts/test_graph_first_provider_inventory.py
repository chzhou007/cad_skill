import copy,unittest
from graph_first_provider_inventory import inherit
from bridge_aware_provider_inventory import MODE as OLD
from rebuild_anchored_cycle_gate_batch import MODE as CYCLE
from graph_first_attribute_context import MODE as CONTEXT

def fixture():
    h='a'*64;pending=dict(edge_id='E',floor=2,next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path')
    old=dict(mode=OLD,inputs={},records=[dict(edge_id='E',classification='horizontal_only',has_existing_correspondence=False,correspondence_observations=[]),dict(edge_id='V',classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[])],ordinary_junction_mappings={'2':{'P0':'A0'}},member_domain_observations=[dict(member_edge_id='MEMBER:x')],remaining_horizontal_attributes=[pending],counts={})
    cycle=dict(mode=CYCLE,inputs=dict(inventory=dict(sha256=h)),floors={'2':dict(new_junction_mapping={'P1':'A1'},records=[dict(mapping_id='M',plan_edges=['P'],iso_edges=['E'])])})
    metrics=dict(inputs=dict(cycle_proof=dict(sha256=h)));context=dict(mode=CONTEXT,source_bindings=dict(cycle_metric_proof=h),cycle_records=[dict(axis_edge_id='E',mapping_id='M',plan_edge_id='P',floor=2,complete_horizontal_centerline_mm=10)],all_current_vertical_domain_count=2)
    values=[dict(edge_id='E',values=dict(cycle_gate_mapping_id='M',cycle_gate_complete_centerline_mm=10)),dict(edge_id='V',values={})]
    return old,cycle,metrics,context,values,dict(metric_proof=h,cycle_proof=h,original_inventory=h)

class Tests(unittest.TestCase):
    def test_known_length_unknown_DN_remains_incomplete_but_not_unmatched(self):
        a=fixture();before=copy.deepcopy(a);r=inherit(*a)
        self.assertEqual(r['counts']['existing_correspondence_edges'],1);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],0)
        self.assertEqual(r['remaining_horizontal_attributes'][0]['next_scope'],'existing_DN_conflict_source_scope_reconciliation')
        self.assertEqual(r['ordinary_junction_mappings']['2']['P1'],'A1');self.assertEqual(r['member_domain_observations'],a[0]['member_domain_observations']);self.assertEqual(a,before)
    def test_old_anchor_or_writer_and_effective_value_conflicts_fail(self):
        for kind in('anchor','writer','value'):
            a=fixture()
            if kind=='anchor':a[0]['ordinary_junction_mappings']['2']['P1']='other'
            elif kind=='writer':a[0]['records'][0]['has_existing_correspondence']=True
            else:a[4][0]['values']['cycle_gate_complete_centerline_mm']=11
            with self.subTest(kind=kind),self.assertRaises(ValueError):inherit(*a)

if __name__=='__main__':unittest.main()
