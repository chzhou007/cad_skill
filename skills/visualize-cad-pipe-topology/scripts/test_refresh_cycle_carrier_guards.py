import copy,json,unittest
from refresh_cycle_carrier_guards import delta
class Tests(unittest.TestCase):
    def fixture(self):
        old=[dict(edge_id='A',values=dict(cycle_gate_mapping_id='M',cycle_gate_complete_centerline_mm=10,old='kept')),dict(edge_id='V',values=dict(unbranched_vertical_DN_segment_count=1))]
        record=dict(axis_edge_id='A',drawing_carrier_projection_mm=10);new=copy.deepcopy(old);new[0]['values']={k:v for k,v in new[0]['values'].items()if not k.startswith('cycle_gate_')};new[0]['values'].update(cycle_carrier_drawing_projection_mm=10,cycle_carrier_evidence_json=json.dumps(record))
        return old,new,dict(records=[record])
    def test_only_declared_unproved_claims_retract_source_projection_remains(self):
        r=delta(*self.fixture());self.assertEqual(r['held_physical_cycle_lengths'],1);self.assertEqual(r['new_physical_values'],0)
    def test_old_source_fields_vertical_values_and_unrelated_edges_protected(self):
        for kind in('old','vertical','restore','other'):
            a=self.fixture()
            if kind=='old':a[1][0]['values']['old']='changed'
            elif kind=='vertical':a[1][1]['values']['unbranched_vertical_DN_segment_count']=0
            elif kind=='restore':a[1][0]['values']['cycle_gate_complete_centerline_mm']=10
            else:a[1][1]['values']['cycle_carrier_drawing_projection_mm']=10
            with self.subTest(kind=kind),self.assertRaises(ValueError):delta(*a)
if __name__=='__main__':unittest.main()
