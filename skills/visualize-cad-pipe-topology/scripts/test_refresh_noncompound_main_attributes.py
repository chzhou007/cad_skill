import copy,unittest
from refresh_noncompound_main_attributes import check_effective_delta,revised_manifest

class Tests(unittest.TestCase):
    def data(self):
        prior=[dict(edge_id='E',values=dict(diameter_nominal_mm=250,batch_complete_horizontal_centerline_mm='',crossview_whole_edge_length_mm='')),dict(edge_id='OTHER',values=dict(diameter_nominal_mm=200))]
        current=copy.deepcopy(prior);current[0]['values'].update(batch_complete_horizontal_centerline_mm=3350,noncompound_main_complete_centerline_mm=3350)
        return prior,current,dict(records=[dict(axis_edge_id='E',nominal_mm=250,complete_horizontal_centerline_route_mm=3350)])
    def test_only_new_complete_length_and_source_columns_change(self):
        r=check_effective_delta(*self.data());self.assertEqual(r['complete_main_lengths_added'],1);self.assertTrue(r['all_existing_DN_preserved']);self.assertEqual(r['whole_installed_lengths_assigned'],0)
    def test_DN_existing_length_unrelated_edge_and_fake_installed_zero_block(self):
        for alter in (lambda a:a[1][0]['values'].update(diameter_nominal_mm=300),lambda a:a[0][0]['values'].update(batch_complete_horizontal_centerline_mm=3000),lambda a:a[1][1]['values'].update(diameter_nominal_mm=250),lambda a:a[1][0]['values'].update(crossview_whole_edge_length_mm=0)):
            args=self.data();alter(args)
            with self.assertRaises(ValueError):check_effective_delta(*args)
    def test_existing_typed_plan_centreline_is_preserved_and_not_counted_as_new(self):
        args=self.data()
        for rows in args[:2]:rows[0]['values'].update(crossview_whole_edge_length_mm=3350,crossview_whole_edge_length_kind='floor_plan_horizontal_main_centerline_route')
        r=check_effective_delta(*args);self.assertEqual(r['complete_main_lengths_added'],0);self.assertEqual(r['complete_main_lengths_requalified'],1)
    def test_new_effective_length_invalidates_related_review_identity(self):
        old=dict(bundleId='BEFORE',templateHashes={},reviewContentHashes=dict(viewer_graph='a'*64))
        r=revised_manifest(old,{'public/edge-attributes.js':'b'*64},'c'*64,'d'*64,10352,dict(noncompound_main_extents=dict(checked=True)))
        self.assertNotEqual(r['bundleId'],old['bundleId']);self.assertFalse(r['attributeTemplateRefresh']['human_confirmation_inherited'])
if __name__=='__main__':unittest.main()
