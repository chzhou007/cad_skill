import copy,json,unittest
from refresh_axis_vertical_DN_attributes import delta
def fixture():
    prior=[dict(edge_id='E',values=dict(diameter_nominal_mm=100,batch_plan_pipe_XY_mm=3000)),dict(edge_id='OLD',values=dict(diameter_nominal_mm=250,typed_length=1000))];current=copy.deepcopy(prior);record=dict(edge_id='E',path_index=0,segment_index=1,nominal_mm=80);context=dict(records=[record],axis_source_sha256='S',previous_axis_riser_domains=8,new_axis_vertical_domains=1,all_current_axis_vertical_domains=9)
    current[0]['values'].update(axis_vertical_DN_segment_count=1,axis_vertical_DN_segments_json=json.dumps([record]),axis_vertical_DN_source_sha256='S');return prior,current,context
class Tests(unittest.TestCase):
    def test_local_vertical_dn_is_appended_and_known_horizontal_values_retained(self):
        r=delta(*fixture());self.assertEqual(r['new_vertical_segment_annotations'],1);self.assertEqual(r['new_whole_edge_DN'],0);self.assertEqual(r['new_physical_lengths'],0);self.assertTrue(r['old_effective_attributes_exact'])
    def test_whole_dn_changes_and_unrelated_old_length_changes_fail(self):
        args=fixture();args[1][0]['values']['diameter_nominal_mm']=80
        with self.assertRaises(ValueError):delta(*args)
        args=fixture();args[1][1]['values']['typed_length']=999
        with self.assertRaises(ValueError):delta(*args)
    def test_actual_exported_segment_identity_must_match_qualified_context(self):
        args=fixture();args[1][0]['values']['axis_vertical_DN_segments_json']=json.dumps([dict(edge_id='E',path_index=0,segment_index=2,nominal_mm=80)])
        with self.assertRaises(ValueError):delta(*args)
if __name__=='__main__':unittest.main()
