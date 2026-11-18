import copy,json,unittest
from refresh_alias_member_bridge_attributes import delta
class Tests(unittest.TestCase):
    def case(self):
        before=[dict(edge_id='E',values=dict(axis_vertical_DN_segments_json='retained')),dict(edge_id='other',values={})]
        row=dict(axis_edge_id='E',mapping_id='M',source_parent_plan_edge='P',nominal_mm=300,plan_pipe_projection_mm=3720,component_correspondences=[{}])
        after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=300,diameter_text='DN300',alias_bridge_mapping_id='M',alias_bridge_plan_edge='P',alias_bridge_plan_pipe_projection_mm=3720,alias_bridge_component_pairs_json='[{}]',alias_bridge_evidence_json=json.dumps(row))
        return before,after,dict(records=[row])
    def test_dn_and_pipe_projection_do_not_complete_length(self):
        a=self.case();r=delta(*a);self.assertEqual(r['new_known_DN'],1);self.assertEqual(r['new_complete_centerlines'],0);self.assertTrue(r['all_old_vertical_values_unchanged'])
    def test_old_vertical_unrelated_and_installed_length_changes_fail(self):
        for key in('axis_vertical_DN_segments_json','installed_length_mm','alias_member_complete_centerline_mm'):
            a=self.case();a[1][0]['values'][key]=0
            with self.subTest(key=key),self.assertRaises(ValueError):delta(*a)
        a=self.case();a[1][1]['values']['new']='bad'
        with self.assertRaises(ValueError):delta(*a)
if __name__=='__main__':unittest.main()
