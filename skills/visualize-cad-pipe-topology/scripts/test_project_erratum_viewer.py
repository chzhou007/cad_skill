import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_project_erratum_ancestor


class ProjectErratumViewerTests(unittest.TestCase):
    def test_unchanged_native_parent_is_required_before_old_viewer_ancestry(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'graph.json';parent=Path(temp)/'parent.json';g={'sourceDraftingErrata':{'records':[1]}};p.write_text(json.dumps(g));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();audit=dict(output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('apply_known_project_pipe_erratum.verify_output',return_value=audit):
                self.assertEqual(verified_project_erratum_ancestor(p,g)[0],parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_project_erratum_ancestor(p,dict(g,changed=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_project_erratum_ancestor(p,g)

    def test_raw_edge_erratum_claim_without_root_is_not_accepted(self):
        with self.assertRaisesRegex(ValueError,'lacks verified'):verified_project_erratum_ancestor(Path('missing'),dict(edges=[{'source_drafting_erratum':{'scope':'local'}}]))


if __name__=='__main__':unittest.main()
