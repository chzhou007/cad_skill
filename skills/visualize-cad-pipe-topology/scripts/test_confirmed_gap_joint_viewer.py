import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from build_visualization import verified_repair_ancestor,digest

class ConfirmedGapJointViewerTests(unittest.TestCase):
    def test_missing_stage_cannot_bypass_existing_source_repair_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';p.write_text('{}')
            with self.assertRaises(FileNotFoundError):verified_repair_ancestor(p,{'sourceConfirmedGapJoints':{'claimed':True}})
    def test_verified_child_uses_exact_parent_and_preserves_raw_graph(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'graph.json';parent=root/'parent.json';g={'sourceConfirmedGapJoints':{'records':[1]}}
            p.write_text(json.dumps(g));parent.write_text('{}')
            audit=dict(output_graph_sha256=digest(p),inputs=dict(graph=dict(path=str(parent),sha256=digest(parent))))
            with patch('attach_confirmed_gap_joints.verify_output',return_value=audit):
                path,proof=verified_repair_ancestor(p,g)
                self.assertEqual(path,parent);self.assertEqual(proof,audit)
                with self.assertRaisesRegex(ValueError,'differs'):verified_repair_ancestor(p,dict(g,changed=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_repair_ancestor(p,g)

if __name__=='__main__':unittest.main()
