import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from build_visualization import verified_attribute_ancestor,digest

class CrossviewAttributeViewerTests(unittest.TestCase):
    def test_attribute_claim_or_unbound_edge_does_not_skip_native_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';p.write_text('{}')
            with self.assertRaises(FileNotFoundError):verified_attribute_ancestor(p,{'crossViewAttributeFusion':{'claim':True}})
            with self.assertRaisesRegex(ValueError,'lack verified'):verified_attribute_ancestor(p,{'edges':[{'cross_view_attributes':{'claim':True}}]})
    def test_replayed_attribute_layer_uses_unchanged_local_parent_for_older_repairs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'graph.json';parent=root/'parent.json';g={'crossViewAttributeFusion':{'records':[1]}}
            p.write_text(json.dumps(g));parent.write_text('{}')
            audit=dict(output_graph_sha256=digest(p),parent_graph=dict(path=str(parent),sha256=digest(parent)))
            with patch('attach_crossview_plan_attributes.verify_output',return_value=audit):
                result,proof=verified_attribute_ancestor(p,g);self.assertEqual(result,parent);self.assertEqual(proof,audit)
                with self.assertRaisesRegex(ValueError,'differs'):verified_attribute_ancestor(p,dict(g,changed=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_attribute_ancestor(p,g)

if __name__=='__main__':unittest.main()
