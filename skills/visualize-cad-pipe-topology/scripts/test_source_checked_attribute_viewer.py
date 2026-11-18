import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_source_attribute_ancestor


class SourceCheckedAttributeViewerTests(unittest.TestCase):
    def test_edge_basis_without_replayed_root_is_not_a_fusion_proof(self):
        with self.assertRaisesRegex(ValueError,'lack a verified stage'):
            verified_source_attribute_ancestor(Path('graph.json'),dict(edges=[dict(cross_view_attributes={'mapping_basis':'native_source_and_main_branch_order'})]))

    def test_actual_parent_replay_precedes_old_fusion_block_and_gap_ancestry(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';parent=Path(folder)/'parent.json';data={'sourceCheckedCrossViewAttributeFusion':{'records':[1]}}
            p.write_text(json.dumps(data));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('attach_source_checked_plan_attributes.verify_output',return_value=audit):
                self.assertEqual(verified_source_attribute_ancestor(p,data)[0],parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_source_attribute_ancestor(p,dict(data,modified=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_source_attribute_ancestor(p,data)


if __name__=='__main__':unittest.main()
