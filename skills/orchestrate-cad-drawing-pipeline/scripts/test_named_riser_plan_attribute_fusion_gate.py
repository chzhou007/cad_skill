import json,tempfile,unittest
from unittest.mock import patch
import test_paired_attribute_extension_gate as fixtures
from source_comparison_gate import check,check_named_riser_plan_attribute_graph


class Tests(unittest.TestCase):
    def fixture(self,folder):
        root,graph,pg,cache,old,audit,sha=fixtures.PairedAttributeGateTests().fixture(folder)
        graph.write_text(json.dumps(dict(sourceNamedRiserPlanAttributeFusion={'new':True},sourceAxisRiserSegmentAttributes={'old':True})))
        audit.update(output_graph_sha256=sha(graph),prior_edges_and_vertical_attributes_preserved=True,physical_ports_verified=False,
            whole_edge_DN_assigned=0,installed_lengths_assigned=0,related_HIL_confirmation_inherited=False,
            source_scope_sha256='S',mapping_sha256='M')
        return root,graph,pg,cache,old,audit,sha
    def test_all_parent_issues_survive_fresh_native_named_scope_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.fixture(folder);old['errors']=['old source defect'];cache.write_text(json.dumps(old))
            with patch('attach_named_riser_plan_attributes.verify_output',return_value=audit) as verify:
                result=check_named_riser_plan_attribute_graph(root,old,sha(graph),graph)
            verify.assert_called_once_with(root.resolve());self.assertEqual(result['errors'],old['errors']);self.assertIn('old datum issue',result['pending'])
            self.assertEqual(result['status'],'failed');self.assertFalse(result['hil_ready']);self.assertIn('named_riser_plan_attribute_stage',result)
    def test_new_scope_dispatches_before_the_vertical_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.fixture(folder)
            with patch('attach_named_riser_plan_attributes.verify_output',side_effect=ValueError('bad named source')),patch('source_comparison_gate.check_axis_riser_attribute_graph') as old_handler:
                result=check(old,sha(graph),root,graph)
            self.assertIn('bad named source',result['errors'][0]);old_handler.assert_not_called()
    def test_preservation_false_physical_claims_or_stale_context_block(self):
        for case in ('preservation','port','DN','length','HIL','base','context'):
            with tempfile.TemporaryDirectory() as folder:
                root,graph,pg,cache,old,audit,sha=self.fixture(folder)
                if case=='preservation':audit['prior_edges_and_vertical_attributes_preserved']=False
                elif case=='port':audit['physical_ports_verified']=True
                elif case=='DN':audit['whole_edge_DN_assigned']=1
                elif case=='length':audit['installed_lengths_assigned']=1
                elif case=='HIL':audit['related_HIL_confirmation_inherited']=True
                elif case=='base':pg.write_text('{"changed":true}')
                else:old=dict(old,pending=[])
                with self.subTest(case=case),patch('attach_named_riser_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):
                    check_named_riser_plan_attribute_graph(root,old,sha(graph),graph)


if __name__=='__main__':unittest.main()
