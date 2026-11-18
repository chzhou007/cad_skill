import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
sys.path.insert(0,str(OWNER))
from source_comparison_gate import check_source_checked_attribute_graph
from compose_source_checked_plan_scopes import MODE


class MultiplanAttributeGateTests(unittest.TestCase):
    def test_composed_mode_replays_before_parent_and_preserves_pending(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'child';root.mkdir();parent=Path(d)/'parent.json';parent.write_text('{}',encoding='utf8');graph=root/'graph_with_edges.json';graph.write_text('{}',encoding='utf8')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            (root/'source-attribute-fusion-audit.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8')
            audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(parent),sha256=sha(parent)),records=[])
            with patch('compose_source_checked_plan_scopes.verify_output',return_value=audit) as replay,patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['old unknown shaft'],hil_ready=False)),patch('attach_source_checked_plan_attributes.verify_output') as legacy:
                result=check_source_checked_attribute_graph(root,{},sha(graph),graph)
            replay.assert_called_once_with(graph.parent);legacy.assert_not_called()
            self.assertIn('old unknown shaft',result['pending']);self.assertFalse(result['hil_ready'])

    def test_stale_composition_cannot_fall_through_to_old_fusion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);graph=root/'graph_with_edges.json';graph.write_text('{}',encoding='utf8')
            (root/'source-attribute-fusion-audit.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8')
            with patch('compose_source_checked_plan_scopes.verify_output',side_effect=ValueError('stale scope source')),patch('attach_source_checked_plan_attributes.verify_output') as legacy:
                with self.assertRaisesRegex(ValueError,'stale scope source'):check_source_checked_attribute_graph(root,{},'G',graph)
            legacy.assert_not_called()


if __name__=='__main__':unittest.main()
