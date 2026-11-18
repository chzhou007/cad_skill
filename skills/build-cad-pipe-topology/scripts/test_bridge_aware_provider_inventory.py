import copy,unittest
from test_alias_aware_provider_inventory import fixture as old_fixture
from bridge_aware_provider_inventory import inventory
from alias_aware_provider_inventory import MODE as PRIOR_MODE
from alias_member_inline_bridges import MODE as SOURCE_MODE
from alias_member_bridge_context import MODE as CONTEXT_MODE
def fixture():
    old,proof,context,values,baseline,bindings=old_fixture();old.update(mode=PRIOR_MODE,source_bindings=dict(native_proof='d'*64))
    proof.update(mode=SOURCE_MODE,source_hashes=dict(member_interfaces='d'*64));row=proof['records'][0];row['plan_member_edge_id']='MEMBER-BRIDGE:NEW';proof['member_local_graph']['edges']=[dict(edge_id='MEMBER-BRIDGE:NEW')]
    context.update(mode=CONTEXT_MODE,records=[copy.deepcopy(row)]);values[0]['values']=dict(diameter_nominal_mm=300,alias_bridge_plan_pipe_projection_mm=3720)
    return old,proof,context,values,baseline,bindings
class Tests(unittest.TestCase):
    def test_proved_mapping_with_unknown_joint_length_stays_in_metric_queue(self):
        a=fixture();before=copy.deepcopy(a);r=inventory(*a);self.assertEqual(a,before);self.assertEqual(r['counts']['existing_correspondence_edges'],1);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],0)
        pending=r['current_horizontal_frontier']['records'][0];self.assertEqual(pending['next_scope'],'known_member_correspondence_incomplete_metric');self.assertEqual(pending['known_whole_DN'],300);self.assertEqual(r['ordinary_junction_mappings'],a[0]['ordinary_junction_mappings']);self.assertIsNone(r['mixed_unmapped_horizontal_extent_count'])
    def test_competing_provider_bad_member_and_missing_old_completion_fail(self):
        for kind in('provider','member','regression'):
            a=fixture()
            if kind=='provider':a[0]['records'][0]['has_existing_correspondence']=True
            elif kind=='member':a[1]['records'][0]['plan_member_edge_id']='ordinary-T'
            else:a[4]['records']=[]
            with self.subTest(kind=kind),self.assertRaises(ValueError):inventory(*a)
if __name__=='__main__':unittest.main()
