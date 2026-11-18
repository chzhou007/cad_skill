import copy,unittest
from refresh_alias_member_interface_attributes import delta

class Tests(unittest.TestCase):
    def fixture(self,main):
        before=[dict(edge_id='E',values=dict(axis_vertical_segment_DN_json='original11',old='kept')),dict(edge_id='other',values={})];after=copy.deepcopy(before);after[0]['values'].update(alias_member_horizontal_DN_mm=300 if main else 200,alias_member_horizontal_complete_centerline_mm=1000,alias_member_complete_centerline_mm=1000 if main else'')
        if main:after[0]['values'].update(diameter_nominal_mm=300,diameter_text='DN300')
        context=dict(records=[dict(axis_edge_id='E',kind='primary_member_main'if main else'lower_member_approach_with_local_rise',nominal_mm=300 if main else 200,attribute_source_domains=dict(horizontal_complete_centerline_mm=1000))]);return before,after,context
    def test_primary_and_mixed_horizontal_values_conserve_all_old_vertical_values(self):
        for main in(False,True):
            args=self.fixture(main);result=delta(*args);self.assertTrue(result['all_old_vertical_values_unchanged']);self.assertEqual(result['installed_lengths_assigned'],0)
            args[1][0]['values']['axis_vertical_segment_DN_json']='changed'
            with self.assertRaisesRegex(ValueError,'vertical'):delta(*args)
    def test_mixed_whole_length_and_unrelated_change_are_blocked(self):
        args=self.fixture(False);args[1][0]['values']['alias_member_complete_centerline_mm']=1000
        with self.assertRaisesRegex(ValueError,'whole length'):delta(*args)
        args=self.fixture(True);args[1][1]['values']['new']='unrelated'
        with self.assertRaisesRegex(ValueError,'unrelated'):delta(*args)
if __name__=='__main__':unittest.main()
