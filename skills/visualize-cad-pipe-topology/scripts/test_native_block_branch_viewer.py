import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_block_branch_ancestor


class NativeBlockBranchViewerTests(unittest.TestCase):
    def test_edge_claim_without_stage_is_not_a_native_proof(self):
        with self.assertRaisesRegex(ValueError,'lacks verified'):
            verified_block_branch_ancestor(Path('graph.json'),dict(edges=[dict(source_native_block_branch={'edge_id':'E'})]))

    def test_replay_then_original_parent_before_gap_floor_and_upstream_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';parent=Path(folder)/'parent.json';g={'sourceNativeBlockBranchReconstruction':{'records':[1]}}
            p.write_text(json.dumps(g));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('reconstruct_native_block_branches.verify_output',return_value=audit):
                self.assertEqual(verified_block_branch_ancestor(p,g)[0],parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_block_branch_ancestor(p,dict(g,edited=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_block_branch_ancestor(p,g)


if __name__=='__main__':unittest.main()
