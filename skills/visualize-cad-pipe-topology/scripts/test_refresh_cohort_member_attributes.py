import copy,json,unittest
from refresh_cohort_member_attributes import delta
class Tests(unittest.TestCase):
    def fixture(self):
        row=dict(axis_edge_id='E',mapping_id='M',nominal_mm=150.,complete_horizontal_centerline_mm=100.,drawn_plan_projection_mm=100.)
        before=[dict(edge_id='E',values=dict(diameter_nominal_mm='',diameter_text='',diameter_status='unmatched',axis_original='retained')),dict(edge_id='V',values=dict(diameter_nominal_mm=80,vertical_source='original'))]
        after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=150.,diameter_text='DN150',diameter_status='cohort_member_native_plan_DN',cohort_member_mapping_id='M',cohort_member_plan_DN_mm=150.,cohort_member_complete_centerline_mm=100.,cohort_member_drawn_projection_mm=100.,cohort_member_evidence_json=json.dumps(row));return before,after,dict(records=[row])
    def test_declared_generic_DN_improvement_preserves_all_other_values(self):
        p,c,ctx=self.fixture();r=delta(p,c,ctx);self.assertEqual(r['new_plan_DN_values'],1);self.assertEqual(r['new_DN_and_length_complete'],1);self.assertTrue(r['all_other_effective_values_exact'])
    def test_known_DN_verticals_unrelated_fields_and_physical_zero_rejected(self):
        for mode in('known','vertical','old_evidence','physical_zero','missing_main_DN','new_other'):
            p,c,ctx=self.fixture()
            if mode=='known':p[0]['values']['diameter_nominal_mm']=200
            elif mode=='vertical':c[1]['values']['diameter_nominal_mm']=100
            elif mode=='old_evidence':c[0]['values']['axis_original']='changed'
            elif mode=='physical_zero':c[0]['values']['installed_length_mm']=0
            elif mode=='missing_main_DN':c[0]['values']['diameter_nominal_mm']=''
            else:c[1]['values']['cohort_member_mapping_id']='new'
            with self.subTest(mode=mode),self.assertRaises(ValueError):delta(p,c,ctx)
if __name__=='__main__':unittest.main()
