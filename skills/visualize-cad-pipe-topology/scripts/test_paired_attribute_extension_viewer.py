import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_source_attribute_ancestor


class PairedAttributeViewerTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);base=root/'base';base.mkdir();common=root/'common.json';common.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        pg=base/'graph_with_edges.json';pg.write_text('{}');parent=dict(path=str(common),sha256=sha(common))
        ba=base/'source-attribute-fusion-audit.json';ba.write_text(json.dumps(dict(parent_graph=parent,output_graph_sha256=sha(pg),records=['OLD'],plan_DN_scope_fusion=['OLD-DN'])))
        child=root/'child';child.mkdir();gp=child/'graph_with_edges.json';data=dict(pairedServiceCrossViewAttributeFusion={'new':True},sourceCheckedCrossViewAttributeFusion={'old':True})
        gp.write_text(json.dumps(data));audit=dict(parent_graph=dict(path=str(pg),sha256=sha(pg)),common_parent_graph=parent,output_graph_sha256=sha(gp),records=['NEW'],plan_DN_scope_fusion=['NEW-DN'])
        (child/'paired-attribute-extension-audit.json').write_text(json.dumps(audit));return gp,data,audit,common,ba,sha
    def test_native_extension_replay_preserves_common_parent_and_both_proof_sets(self):
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.fixture(folder)
            with patch('compose_paired_plan_attribute_scope.verify_output',return_value=audit):parent,proof=verified_source_attribute_ancestor(gp,data)
            self.assertEqual(parent,common);self.assertEqual(proof['records'],['OLD','NEW']);self.assertEqual(proof['plan_DN_scope_fusion'],['OLD-DN','NEW-DN'])
            self.assertEqual(proof['paired_base_attribute_audit_path'],str(ba))
    def test_uncomposed_scope_and_failed_replay_never_enter_viewer(self):
        with self.assertRaisesRegex(ValueError,'composed verified stage'):verified_source_attribute_ancestor(Path('graph.json'),dict(edges=[dict(cross_view_attributes={'mapping_basis':'native_paired_service_corridors'})]))
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.fixture(folder)
            with patch('compose_paired_plan_attribute_scope.verify_output',side_effect=ValueError('native scope changed')):
                with self.assertRaisesRegex(ValueError,'native scope changed'):verified_source_attribute_ancestor(gp,data)
    def test_changed_base_audit_during_replay_or_wrong_common_parent_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.fixture(folder)
            def replay(_):ba.write_text('{}');return audit
            with patch('compose_paired_plan_attribute_scope.verify_output',side_effect=replay):
                with self.assertRaisesRegex(ValueError,'during replay'):verified_source_attribute_ancestor(gp,data)
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha=self.fixture(folder);audit['common_parent_graph']={'path':'OTHER','sha256':'X'}
            with patch('compose_paired_plan_attribute_scope.verify_output',return_value=audit):
                with self.assertRaisesRegex(ValueError,'different ancestry'):verified_source_attribute_ancestor(gp,data)


if __name__=='__main__':unittest.main()
