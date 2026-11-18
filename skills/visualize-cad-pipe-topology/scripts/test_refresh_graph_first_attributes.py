import copy,json,unittest
from refresh_graph_first_attributes import delta

class Tests(unittest.TestCase):
    def fixture(self):
        old=[dict(edge_id='H',values=dict(diameter_nominal_mm='',old='retained')),dict(edge_id='V',values=dict(axis_vertical_DN_segments_json='old')),dict(edge_id='other',values={})]
        r=dict(axis_edge_id='H',mapping_id='M',plan_edge_id='P',complete_horizontal_centerline_mm=10);v=dict(edge_id='V',nominal_mm=80)
        new=copy.deepcopy(old);new[0]['values'].update(cycle_gate_mapping_id='M',cycle_gate_plan_edge='P',cycle_gate_complete_centerline_mm=10,cycle_gate_evidence_json=json.dumps(r));new[1]['values'].update(unbranched_vertical_DN_segment_count=1,unbranched_vertical_DN_segments_json=json.dumps([v]))
        return old,new,dict(cycle_records=[r],vertical_records=[v],all_current_vertical_domain_count=2)
    def test_all_old_values_retained_with_two_separate_new_domains(self):
        r=delta(*self.fixture());self.assertEqual(r['new_horizontal_centerlines'],1);self.assertEqual(r['new_vertical_DN_domains'],1);self.assertEqual(r['new_whole_DN'],0)
    def test_cannot_silently_change_an_old_field_or_unrelated_edge(self):
        for kind in ('DN','vertical','unrelated','newfield'):
            a=self.fixture()
            if kind=='DN':a[1][0]['values']['diameter_nominal_mm']=300
            elif kind=='vertical':a[1][1]['values']['axis_vertical_DN_segments_json']='changed'
            elif kind=='unrelated':a[1][2]['values']['extra']=10
            else:a[1][0]['values']['installed_length_mm']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):delta(*a)

if __name__=='__main__':unittest.main()
