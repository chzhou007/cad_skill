import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_refined_paired_attribute_viewer as fixtures
from build_visualization import verified_source_attribute_ancestor


class Tests(unittest.TestCase):
    def data(self,folder):
        gp,data,parent,common,ba,sha=fixtures.RefinedPairedAttributeViewerTests().data(folder)
        data['sourceAxisRiserSegmentAttributes']={'new':True};gp.write_text(json.dumps(data))
        audit=dict(verified_parent_composition=parent,verified_parent_base_attribute_audit=dict(path=str(ba),sha256=sha(ba)),
            parent_graph=dict(path=str(gp),sha256=sha(gp)),all_prior_plan_attributes_preserved=True,local_topology_and_components_preserved=True,output_graph_sha256=sha(gp))
        return gp,data,audit,common,ba,sha
    def test_segment_replay_reuses_just_verified_parent_context_without_second_full_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.data(folder)
            with patch('attach_axis_riser_segment_attributes.verify_output',return_value=audit) as current,patch('compose_refined_paired_plan_attributes.verify_output',side_effect=AssertionError('duplicate parent replay')):
                ancestor,proof=verified_source_attribute_ancestor(gp,data)
            current.assert_called_once_with(gp.parent);self.assertEqual(ancestor,common);self.assertEqual(proof['records'],['OLD','NEW'])
            self.assertIn('axis_riser_segment_attribute_audit',proof);self.assertFalse(proof['hil_ready'])
    def test_unverified_stale_or_changed_parent_context_cannot_enter_viewer(self):
        with self.assertRaisesRegex(ValueError,'verified extension'):
            verified_source_attribute_ancestor(Path('missing.json'),{'edges':[dict(axis_riser_attributes=[{'forged':True}])]})
        for case in ['audit','context','preservation','replay']:
            with tempfile.TemporaryDirectory() as folder:
                gp,data,audit,common,ba,sha=self.data(folder)
                if case=='audit':audit['output_graph_sha256']='other'
                elif case=='context':ba.write_text('{}')
                elif case=='preservation':audit['all_prior_plan_attributes_preserved']=False
                def verify(_):
                    if case=='replay':raise ValueError('source changed')
                    return audit
                with self.subTest(case=case),patch('attach_axis_riser_segment_attributes.verify_output',side_effect=verify),self.assertRaises(ValueError):verified_source_attribute_ancestor(gp,data)


if __name__=='__main__':unittest.main()
