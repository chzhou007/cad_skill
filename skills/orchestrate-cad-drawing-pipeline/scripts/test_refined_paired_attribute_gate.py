import json,tempfile,unittest
from unittest.mock import patch
import test_paired_attribute_extension_gate as fixtures
from source_comparison_gate import check,check_refined_paired_attribute_graph


class RefinedPairedAttributeGateTests(unittest.TestCase):
    def data(self,folder):
        root,graph,pg,cache,old,audit,sha=fixtures.PairedAttributeGateTests().fixture(folder)
        graph.write_text(json.dumps(dict(pairedJunctionCrossViewAttributeFusion={'new':True},sourceCheckedCrossViewAttributeFusion={'old':True})))
        audit.update(output_graph_sha256=sha(graph),coarse_paired_child_not_added=True,related_prior_HIL_confirmation_inherited=False,superseded_mapping_records=[dict(mapping_id='OLD-COARSE')])
        return root,graph,pg,cache,old,audit,sha
    def test_native_refinement_preserves_all_prior_source_issues_and_superseded_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.data(folder)
            with patch('compose_refined_paired_plan_attributes.verify_output',return_value=audit):r=check_refined_paired_attribute_graph(root,old,sha(graph),graph)
            self.assertIn('old datum issue',r['pending']);self.assertFalse(r['hil_ready']);self.assertFalse(r['human_accepted'])
            state=r['refined_paired_attribute_stage'];self.assertEqual(state['superseded_mapping_records'],audit['superseded_mapping_records']);self.assertTrue(state['coarse_child_replaced_not_added'])
    def test_refined_stage_is_checked_before_old_attribute_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.data(folder)
            with patch('compose_refined_paired_plan_attributes.verify_output',side_effect=ValueError('bad refined source')),patch('source_comparison_gate.check_source_checked_attribute_graph') as wrong:
                result=check(old,sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('bad refined source',result['errors'][0]);wrong.assert_not_called()
    def test_stale_context_or_false_replacement_flags_never_pass(self):
        for case in ('context','base','cache','preservation','coarse_added','HIL_inherited'):
            with tempfile.TemporaryDirectory() as folder:
                root,graph,pg,cache,old,audit,sha=self.data(folder)
                if case=='context':old=dict(old,pending=[])
                elif case=='base':pg.write_text('{"changed":true}')
                elif case=='cache':cache.unlink()
                elif case=='preservation':audit['all_prior_attribute_values_preserved']=False
                elif case=='coarse_added':audit['coarse_paired_child_not_added']=False
                else:audit['related_prior_HIL_confirmation_inherited']=True
                with patch('compose_refined_paired_plan_attributes.verify_output',return_value=audit):
                    with self.subTest(case=case),self.assertRaises((ValueError,OSError)):check_refined_paired_attribute_graph(root,old,sha(graph),graph)
    def test_original_error_is_retained_even_when_new_scope_replays(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.data(folder);old['errors']=['old source defect'];cache.write_text(json.dumps(old),encoding='utf8')
            with patch('compose_refined_paired_plan_attributes.verify_output',return_value=audit):r=check_refined_paired_attribute_graph(root,old,sha(graph),graph)
            self.assertEqual(r['status'],'failed');self.assertEqual(r['errors'],old['errors'])


if __name__=='__main__':unittest.main()
