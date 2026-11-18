import copy,json,unittest
from refresh_qualified_plan_scope_attributes import delta
class Tests(unittest.TestCase):
    def test_specific_provider_delta_keeps_old_member_and_vertical_columns_exact(self):
        record=dict(axis_edge_id='E',nominal_mm=150,horizontal_plan_run_centerline_mm=2150,mapping_id='BATCH-OLD')
        prior=[dict(edge_id='E',values={}),dict(edge_id='OLD',values=dict(member_plan_run_centerline_mm=1500,axis_vertical_DN_segments_json='retained'))];current=copy.deepcopy(prior);current[0]['values']=dict(diameter_nominal_mm=150,member_plan_run_centerline_mm=2150,ordered_owner_mapping_id='BATCH-OLD',ordered_owner_plan_run_evidence_json=json.dumps(record),member_plan_net_pipe_cut_length_mm='')
        r=delta(prior,current,dict(records=[record]));self.assertEqual(r['new_known_DN'],1);self.assertEqual(r['new_complete_horizontal_centerlines'],1)
        current[1]['values']['member_plan_run_centerline_mm']=1501
        with self.assertRaises(ValueError):delta(prior,current,dict(records=[record]))
if __name__=='__main__':unittest.main()
