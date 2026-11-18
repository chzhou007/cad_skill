import copy,unittest
from refresh_compound_interface_attributes import delta

def fixture(mixed=False):
    old=[dict(edge_id='NEW',values=dict(diameter_nominal_mm='',crossview_whole_edge_length_mm='',source='preserved')),dict(edge_id='OLD',values=dict(diameter_nominal_mm=250,typed_length=3350))]
    current=copy.deepcopy(old);current[0]['values'].update(diameter_nominal_mm=200 if mixed else 300,diameter_text='DN200' if mixed else 'DN300')
    if not mixed:current[0]['values']['batch_complete_horizontal_centerline_mm']=4000
    context=dict(records=[dict(axis_edge_id='NEW',nominal_mm=200 if mixed else 300,kind='lower_member_approach_with_local_rise' if mixed else 'primary_member_main',complete_horizontal_centerline_route_mm=None if mixed else 4000,plan_projection=dict(value_mm=1000 if mixed else 4000))])
    return old,current,context
class Tests(unittest.TestCase):
    def test_new_values_counted_separately_from_inherited_values(self):
        r=delta(*fixture());self.assertEqual(r['new_known_DN_edges'],['NEW']);self.assertEqual(r['new_complete_centerline_edges'],['NEW']);self.assertTrue(r['unrelated_effective_values_preserved'])
        r=delta(*fixture(True));self.assertEqual(r['new_known_DN_edges'],['NEW']);self.assertEqual(r['new_complete_centerline_edges'],[])
    def test_mixed_length_promotion_and_unrelated_old_value_change_rejected(self):
        args=fixture(True);args[1][0]['values']['batch_complete_horizontal_centerline_mm']=1000
        with self.assertRaisesRegex(ValueError,'mixed local rise'):delta(*args)
        args=fixture();args[1][1]['values']['typed_length']=3300
        with self.assertRaisesRegex(ValueError,'unrelated inherited'):delta(*args)
    def test_prior_positive_DN_and_source_evidence_cannot_be_overwritten(self):
        args=fixture();args[0][0]['values']['diameter_nominal_mm']=250
        with self.assertRaisesRegex(ValueError,'previously known'):delta(*args)
        args=fixture();args[1][0]['values']['source']='lost'
        with self.assertRaisesRegex(ValueError,'inherited source'):delta(*args)
if __name__=='__main__':unittest.main()
