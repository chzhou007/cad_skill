import copy,json,unittest
from refresh_compound_bridge_attributes import delta
def fixture():
    r=dict(axis_edge_id='E',mapping_id='M',source_parent_plan_edge='P',nominal_mm=300.,plan_pipe_projection_mm=4049.,component_correspondences=[dict(plan={'id':'P1'},axis={'id':'A1'})]);prior=[dict(edge_id='E',values=dict(diameter_nominal_mm='',axis_vertical_DN_segment_count='',crossview_whole_edge_length_mm='')),dict(edge_id='OLD',values=dict(diameter_nominal_mm=80,axis_vertical_DN_segment_count=1,axis_vertical_DN_segments_json='native80'))];now=copy.deepcopy(prior)
    now[0]['values'].update(diameter_nominal_mm=300.,diameter_text='DN300',diameter_status='source_checked',physical_edge_length_status='partial',member_bridge_mapping_id='M',member_bridge_plan_edge='P',member_bridge_DN_mm=300.,member_bridge_plan_pipe_projection_mm=4049.,member_bridge_component_pairs_json=json.dumps(r['component_correspondences']),member_bridge_evidence_json=json.dumps(r));return prior,now,dict(records=[r])
class Tests(unittest.TestCase):
    def test_new_DN_and_partial_projection_do_not_complete_unknown_joint_length(self):
        r=delta(*fixture());self.assertEqual(r['new_known_DN'],1);self.assertEqual(r['new_complete_centerlines'],0);self.assertEqual(r['component_pairs'],1)
    def test_vertical_change_fake_whole_length_or_existing_DN_overwrite_fails(self):
        for kind in('vertical','whole','DN'):
            a=fixture()
            if kind=='vertical':a[1][1]['values']['axis_vertical_DN_segments_json']='wrong'
            if kind=='whole':a[1][0]['values']['crossview_whole_edge_length_mm']=5000
            if kind=='DN':a[0][0]['values']['diameter_nominal_mm']=200
            with self.assertRaises(ValueError):delta(*a)
    def test_equal_component_counts_wrong_evidence_does_not_pass(self):
        a=fixture();a[1][0]['values']['member_bridge_component_pairs_json']='[{"wrong":true}]'
        with self.assertRaises(ValueError):delta(*a)
if __name__=='__main__':unittest.main()
