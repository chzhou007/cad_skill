import copy,unittest
from rebuild_ordered_owner_crossview import additions,preserve_member_runs

def row(pid='P',eid='E',mid='OLD'):
    return dict(kind='same_floor_T_to_T_main',floor=2,system='supply',plan_edges=[pid],iso_edges=[eid],mapping_id=mid)
class Tests(unittest.TestCase):
    def test_semantic_new_ID_ignores_discovery_ordinal_and_input_order(self):
        old=[row()];new=[row('Q','F','BATCH-1'),row()];before=copy.deepcopy((old,new));a=additions(old,new);new[0]['mapping_id']='BATCH-999';b=additions(old,list(reversed(new)))
        self.assertEqual(a,b);self.assertEqual(old,before[0]);self.assertEqual(a[0]['plan_edges'],['Q']);self.assertTrue(a[0]['mapping_id'].startswith('OWNER-F2-'))
    def test_retiring_history_parallel_writers_or_duplicate_records_fail(self):
        for old,new in [([row()],[]),([row()],[row(),row()]),([row()],[row(),row('Q','E')]),([row()],[row(),row('P','F')])]:
            with self.assertRaises(ValueError):additions(old,new)
    def test_all_historical_member_values_remain_exact(self):
        old=[dict(plan_edge_id='P',nominal_mm=200,horizontal_plan_run_centerline_mm=1500,net_pipe_cut_length_mm=None)]
        new=copy.deepcopy(old)+[dict(plan_edge_id='Q',nominal_mm=200,horizontal_plan_run_centerline_mm=4350,net_pipe_cut_length_mm=None)]
        self.assertEqual(preserve_member_runs(old,new),['Q']);new[0]['horizontal_plan_run_centerline_mm']=1501
        with self.assertRaises(ValueError):preserve_member_runs(old,new)
if __name__=='__main__':unittest.main()
