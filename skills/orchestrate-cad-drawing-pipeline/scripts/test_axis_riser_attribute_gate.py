import json,tempfile,unittest
from unittest.mock import patch
import test_paired_attribute_extension_gate as fixtures
from source_comparison_gate import check,check_axis_riser_attribute_graph


class Tests(unittest.TestCase):
    def data(self,folder):
        root,graph,pg,cache,old,audit,sha=fixtures.PairedAttributeGateTests().fixture(folder)
        graph.write_text(json.dumps(dict(sourceAxisRiserSegmentAttributes={'new':True},pairedJunctionCrossViewAttributeFusion={'old':True})))
        audit.update(output_graph_sha256=sha(graph),all_prior_plan_attributes_preserved=True,local_topology_and_components_preserved=True,
            whole_edge_DN_assigned=0,installed_lengths_assigned=0,related_prior_HIL_confirmation_inherited=False,
            added_segment_attributes=8,affected_axis_edges=['E1'],source_scope_sha256='S')
        return root,graph,pg,cache,old,audit,sha
    def test_native_segment_replay_preserves_all_parent_pending_items_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.data(folder);old['errors']=['old source defect'];cache.write_text(json.dumps(old),encoding='utf8')
            with patch('attach_axis_riser_segment_attributes.verify_output',return_value=audit):out=check_axis_riser_attribute_graph(root,old,sha(graph),graph)
            self.assertIn('old datum issue',out['pending']);self.assertEqual(out['errors'],old['errors']);self.assertEqual(out['status'],'failed')
            self.assertEqual(out['axis_riser_segment_attribute_stage']['segments'],8);self.assertFalse(out['hil_ready'])
    def test_axis_segment_extension_is_dispatched_before_refined_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.data(folder)
            with patch('attach_axis_riser_segment_attributes.verify_output',side_effect=ValueError('bad native DN scope')),patch('source_comparison_gate.check_refined_paired_attribute_graph') as wrong:
                out=check(old,sha(graph),root,graph)
            self.assertIn('bad native DN scope',out['errors'][0]);wrong.assert_not_called()
    def test_extent_and_preservation_flags_and_stale_parent_context_block(self):
        for case in ['whole','length','HIL','preservation','base','context']:
            with tempfile.TemporaryDirectory() as folder:
                root,graph,pg,cache,old,audit,sha=self.data(folder)
                if case=='whole':audit['whole_edge_DN_assigned']=1
                elif case=='length':audit['installed_lengths_assigned']=1
                elif case=='HIL':audit['related_prior_HIL_confirmation_inherited']=True
                elif case=='preservation':audit['all_prior_plan_attributes_preserved']=False
                elif case=='base':pg.write_text('{"changed":true}')
                else:old=dict(old,pending=[])
                with self.subTest(case=case),patch('attach_axis_riser_segment_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):check_axis_riser_attribute_graph(root,old,sha(graph),graph)


if __name__=='__main__':unittest.main()
