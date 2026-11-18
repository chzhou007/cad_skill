import json,tempfile,unittest
from unittest.mock import patch
import test_paired_attribute_extension_viewer as fixtures
from build_visualization import verified_source_attribute_ancestor


class RefinedPairedAttributeViewerTests(unittest.TestCase):
    def data(self,folder):
        gp,data,audit,common,ba,sha=fixtures.PairedAttributeViewerTests().fixture(folder)
        data.pop('pairedServiceCrossViewAttributeFusion');data['pairedJunctionCrossViewAttributeFusion']={'new':True};gp.write_text(json.dumps(data));audit['output_graph_sha256']=sha(gp)
        (gp.parent/'refined-paired-attribute-composition-audit.json').write_text(json.dumps(audit));return gp,data,audit,common,ba,sha
    def test_refined_stage_replays_and_joins_both_proof_sets_without_old_child(self):
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.data(folder)
            with patch('compose_refined_paired_plan_attributes.verify_output',return_value=audit):parent,proof=verified_source_attribute_ancestor(gp,data)
            self.assertEqual(parent,common);self.assertEqual(proof['records'],['OLD','NEW']);self.assertEqual(proof['plan_DN_scope_fusion'],['OLD-DN','NEW-DN'])
            self.assertEqual(proof['refined_base_attribute_audit_path'],str(ba));self.assertFalse(proof['hil_ready'])
    def test_uncomposed_or_coarse_plus_refined_is_not_viewer_ready(self):
        with self.assertRaisesRegex(ValueError,'composed verified stage'):
            verified_source_attribute_ancestor(None,dict(edges=[dict(cross_view_attributes=dict(mapping_basis='native_paired_service_junction_correspondence'))]))
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.data(folder);data['pairedServiceCrossViewAttributeFusion']={}
            with self.assertRaisesRegex(ValueError,'cannot be combined'):verified_source_attribute_ancestor(gp,data)
    def test_wrong_parent_or_modified_base_audit_cannot_be_reused(self):
        for case in ('parent','modified','replay'):
            with tempfile.TemporaryDirectory() as folder:
                gp,data,audit,common,ba,sha=self.data(folder)
                if case=='parent':audit['common_parent_graph']={'path':'OTHER','sha256':'X'}
                def replay(_):
                    if case=='modified':ba.write_text('{}')
                    if case=='replay':raise ValueError('source changed')
                    return audit
                with patch('compose_refined_paired_plan_attributes.verify_output',side_effect=replay):
                    with self.subTest(case=case),self.assertRaises(ValueError):verified_source_attribute_ancestor(gp,data)


if __name__=='__main__':unittest.main()
