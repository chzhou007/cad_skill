import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
sys.path.insert(0,str(OWNER))
from build_visualization import verified_source_attribute_ancestor
from compose_source_checked_plan_scopes import MODE


class MultiplanAttributeViewerTests(unittest.TestCase):
    def test_composed_receipt_uses_common_confirmed_parent_with_no_HIL_inheritance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);parent=root/'parent.json';parent.write_text('{}',encoding='utf8');graph=root/'graph_with_edges.json'
            data=dict(sourceCheckedCrossViewAttributeFusion=dict(human_accepted=False));graph.write_text(json.dumps(data),encoding='utf8')
            (root/'source-attribute-fusion-audit.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('compose_source_checked_plan_scopes.verify_output',return_value=audit) as replay,patch('attach_source_checked_plan_attributes.verify_output') as wrong:
                self.assertEqual(verified_source_attribute_ancestor(graph,data),(parent,audit))
            replay.assert_called_once();wrong.assert_not_called()
            parent.write_text('{"changed":true}',encoding='utf8')
            with patch('compose_source_checked_plan_scopes.verify_output',return_value=audit):
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_source_attribute_ancestor(graph,data)


if __name__=='__main__':unittest.main()
