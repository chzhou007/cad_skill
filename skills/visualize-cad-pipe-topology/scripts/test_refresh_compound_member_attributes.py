import copy,unittest
from refresh_compound_member_attributes import check_effective_delta,revised_manifest

class Tests(unittest.TestCase):
    def data(self):
        prior=[dict(edge_id='TARGET',values=dict(diameter_nominal_mm=300)),dict(edge_id='OTHER',values=dict(diameter_nominal_mm=80))]
        current=[dict(edge_id='TARGET',values=dict(diameter_nominal_mm=200,batch_complete_horizontal_centerline_mm=1000,crossview_whole_edge_length_mm='')),copy.deepcopy(prior[1])]
        ctx=dict(records=[dict(axis_edge_id='TARGET',nominal_mm=200,plan_run_centerline_mm=1000,superseded_scalar_observation=dict(plan_nominal_mm=300))])
        return prior,current,ctx
    def test_explicit_source_member_correction_is_audited_without_touching_other_values(self):
        r=check_effective_delta(*self.data());self.assertEqual(r['corrected_prior_positive_DN'],[dict(edge_id='TARGET',before_mm=300,after_mm=200)]);self.assertTrue(r['unrelated_values_preserved']);self.assertEqual(r['whole_installed_lengths_assigned'],0)
    def test_unrelated_change_another_positive_owner_and_fake_installed_length_block(self):
        args=list(self.data());args[1][1]['values']['diameter_nominal_mm']=90
        with self.assertRaisesRegex(ValueError,'unrelated'):check_effective_delta(*args)
        args=list(self.data());args[0][0]['values']['diameter_nominal_mm']=250
        with self.assertRaisesRegex(ValueError,'another prior DN'):check_effective_delta(*args)
        args=list(self.data());args[1][0]['values']['crossview_whole_edge_length_mm']=0
        with self.assertRaisesRegex(ValueError,'effective values differ'):check_effective_delta(*args)
    def test_semantic_member_context_invalidates_review_identity(self):
        prior=dict(bundleId='OLD',templateHashes={},reviewContentHashes={'viewer_graph':'a'*64})
        result=revised_manifest(prior,{'public/edge-attributes.js':'b'*64},'c'*64,'d'*64,10351,dict(compound_member_mains={'checked':True}))
        self.assertNotEqual(result['bundleId'],'OLD');self.assertFalse(result['attributeTemplateRefresh']['human_confirmation_inherited']);self.assertEqual(prior['reviewContentHashes'],{'viewer_graph':'a'*64})
if __name__=='__main__':unittest.main()
