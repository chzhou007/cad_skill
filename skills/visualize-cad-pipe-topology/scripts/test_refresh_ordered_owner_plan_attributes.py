import copy,json,unittest
from refresh_ordered_owner_plan_attributes import delta
class Tests(unittest.TestCase):
    def fixture(self):
        r=dict(axis_edge_id='E',nominal_mm=200,horizontal_plan_run_centerline_mm=1500,mapping_id='M')
        prior=[dict(edge_id='E',values={}),dict(edge_id='V',values=dict(axis_vertical_DN_segments_json='ORIGINAL'))]
        current=copy.deepcopy(prior);current[0]['values']=dict(diameter_nominal_mm=200,member_plan_run_centerline_mm=1500,ordered_owner_mapping_id='M',ordered_owner_plan_run_evidence_json=json.dumps(r),member_plan_net_pipe_cut_length_mm='')
        return prior,current,dict(records=[r])
    def test_new_complete_centerline_and_DN_not_installed_length(self):
        r=delta(*self.fixture());self.assertEqual(r['new_known_DN'],1);self.assertEqual(r['new_complete_horizontal_centerlines'],1);self.assertEqual(r['new_installed_lengths'],0)
    def test_old_vertical_DN_or_installed_length_cannot_change(self):
        for kind in ('vertical','DN','installed'):
            a=self.fixture()
            if kind=='vertical':a[1][1]['values']['axis_vertical_DN_segments_json']='CHANGED'
            if kind=='DN':a[0][0]['values']['diameter_nominal_mm']=300
            if kind=='installed':a[1][0]['values']['crossview_whole_edge_length_mm']=1500
            with self.assertRaises(ValueError,msg=kind):delta(*a)
if __name__=='__main__':unittest.main()
