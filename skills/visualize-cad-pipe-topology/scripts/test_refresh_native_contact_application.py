import copy,unittest
from refresh_native_contact_application import delta

class Tests(unittest.TestCase):
    def fixture(self):
        row=dict(axis_edge_id='A',mapping_id='M',nominal_mm=250.,complete_horizontal_centerline_mm=None)
        old=[dict(edge_id='A',values=dict(diameter_nominal_mm='',old_length=None)),dict(edge_id='B',values=dict(diameter_nominal_mm=100,old_value='中文'))]
        new=copy.deepcopy(old);new[0]['values'].update(contact_owner_mapping_id='M',contact_owner_plan_DN_mm=250.,contact_owner_complete_centerline_mm='',contact_owner_evidence_json=__import__('json').dumps(row),diameter_nominal_mm=250.,diameter_text='DN250')
        return old,new,[row]
    def test_only_declared_new_DN_and_fields_change_old_unknown_length_stays_unknown(self):
        result=delta(*self.fixture());self.assertEqual(result['new_plan_DN_values'],1);self.assertEqual(result['new_complete_horizontal_lengths'],0);self.assertTrue(result['all_other_effective_pipe_values_exact'])
    def test_old_known_DN_unrelated_value_or_unknown_length_cannot_be_overwritten(self):
        for kind in ('DN','other','length'):
            args=self.fixture()
            if kind=='DN':args[0][0]['values']['diameter_nominal_mm']=150
            elif kind=='other':args[1][1]['values']['old_value']='changed'
            else:args[1][0]['values']['old_length']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):delta(*args)

if __name__=='__main__':unittest.main()
