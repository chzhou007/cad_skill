import copy,unittest
from refresh_riser_header_attributes import delta
class Tests(unittest.TestCase):
    def fixture(self):
        member=dict(axis_edge_id='M',mapping_id='MAP',nominal_mm=300,complete_horizontal_centerline_mm=None);clear=dict(axis_edge_id='C',complete_horizontal_centerline_mm=8000);ctx=dict(member_records=[member],cycle_clearances=[clear]);old=[dict(edge_id='M',values=dict(old=1)),dict(edge_id='C',values=dict(cycle_carrier_hold_status='held',old=2)),dict(edge_id='V',values=dict(unbranched_vertical_DN_segments_json='108'))];new=copy.deepcopy(old);new[0]['values'].update(riser_header_mapping_id='MAP',riser_header_plan_DN_mm=300,riser_header_complete_centerline_mm='',riser_header_evidence_json='{"axis_edge_id":"M","mapping_id":"MAP","nominal_mm":300,"complete_horizontal_centerline_mm":null}');new[1]['values']=dict(old=2,cycle_gate_complete_centerline_mm=8000,cycle_carrier_clearance_evidence_json='{"axis_edge_id":"C","complete_horizontal_centerline_mm":8000}');return old,new,ctx
    def test_declared_additions_and_clearance_preserve_all_other_values(self):
        old,new,ctx=self.fixture();r=delta(old,new,ctx);self.assertEqual(r['new_plan_DN_values'],1);self.assertEqual(r['new_complete_horizontal_lengths'],0);self.assertEqual(r['restored_native_cycle_lengths'],1)
    def test_unrelated_value_changes_and_zero_filled_unknown_length_fail(self):
        for key in('vertical','length','old','held'):
            old,new,ctx=self.fixture()
            if key=='vertical':new[2]['values']['unbranched_vertical_DN_segments_json']='0'
            elif key=='length':new[0]['values']['riser_header_complete_centerline_mm']=0
            elif key=='old':new[0]['values']['old']=2
            else:new[1]['values']['cycle_carrier_hold_status']='held'
            with self.subTest(key=key),self.assertRaises(ValueError):delta(old,new,ctx)
if __name__=='__main__':unittest.main()
