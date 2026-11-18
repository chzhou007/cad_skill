import copy,unittest
from full_plan_DN_gate import check


def fixture():
    return dict(mode='complete_local_plan_native_DN_batch_v1',local_graphs_mutated=False,human_accepted=False,hil_ready=False,
        crossview_mapping_required_to_read_plan=False,axis_values_fused=0,physical_lengths_assigned=0,
        floors={'1':dict(records=[dict(edge_id='A',nominal_mm=80,status='direct_plan_DN',human_accepted=False),
            dict(edge_id='B',nominal_mm=None,status='conflict',human_accepted=False)],
            counts=dict(graph_edges=2),crossview_subset_used_for_scope=False)},
        local_parent_replay={'1':dict(native_replay_passed=True)},counts=dict(total_plan_edges=2,known_plan_DN_edges=1))


class Tests(unittest.TestCase):
    def test_full_local_batch_keeps_conflicts_and_distinguishes_axis_and_human_acceptance(self):
        r=check(fixture());self.assertEqual(r['known_plan_DN_edges'],1);self.assertEqual(r['conflicting_DN_edges'],1)
        self.assertEqual(r['axis_values_fused'],0);self.assertFalse(r['hil_ready'])
    def test_partial_scope_false_values_and_bypassed_parent_are_rejected(self):
        for kind in ['filtered','duplicate','unreplayed','conflict_has_value','human','count']:
            d=fixture()
            if kind=='filtered':d['floors']['1']['crossview_subset_used_for_scope']=True
            if kind=='duplicate':d['floors']['1']['records'][1]['edge_id']='A'
            if kind=='unreplayed':d['local_parent_replay']['1']['native_replay_passed']=False
            if kind=='conflict_has_value':d['floors']['1']['records'][1]['nominal_mm']=80
            if kind=='human':d['human_accepted']=True
            if kind=='count':d['counts']['known_plan_DN_edges']=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):check(d)


if __name__=='__main__':unittest.main()
