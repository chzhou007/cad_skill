import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_circle_path_normalization_graph

class CircleGateTests(unittest.TestCase):
    def test_actual_parent_pending_and_errors_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parent=root/'old/graph_with_edges.json';parent.parent.mkdir();parent.write_text('{}')
            child=root/'new/graph_with_edges.json';child.parent.mkdir();child.write_text(json.dumps(dict(sourceCirclePathNormalization={'records':[1]},sourceLayoutEquipmentOwnership={'records':[1]})))
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(child),records=[dict(edge_id='E')])
            previous=dict(status='failed',errors=['native unresolved geometry'],pending=['old DN'],hil_ready=False)
            with patch('normalize_plan_circle_paths.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=previous) as recurse:
                result=check_circle_path_normalization_graph(child.parent,{},sha(child),child)
            recurse.assert_called_once_with({},sha(parent),parent.parent,parent)
            self.assertEqual(result['errors'],previous['errors']);self.assertIn('old DN',result['pending']);self.assertFalse(result['hil_ready'])
            parent.write_text('{"changed":true}')
            with patch('normalize_plan_circle_paths.verify_output',return_value=audit):
                with self.assertRaises(ValueError):check_circle_path_normalization_graph(child.parent,{},sha(child),child)

    def test_newest_stage_dispatches_before_inherited_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);g=root/'graph_with_edges.json';g.write_text('{"sourceCirclePathNormalization":{},"edges":[{"source_circle_path_normalization":{},"source_layout_equipment_interface":{}}]}')
            # Even an empty edge flag must trigger verification rather than a fallback.
            with patch('normalize_plan_circle_paths.verify_output',side_effect=ValueError('empty proof')):
                self.assertEqual(check({},hashlib.sha256(g.read_bytes()).hexdigest(),root,g)['status'],'failed')
            g.write_text('{"sourceCirclePathNormalization":{"records":[1]},"sourceLayoutEquipmentOwnership":{"records":[1]}}')
            with patch('normalize_plan_circle_paths.verify_output',side_effect=ValueError('missing proof')),patch('calibrated_equipment_interface_ownership.verify_output') as old:
                result=check({},hashlib.sha256(g.read_bytes()).hexdigest(),root,g)
            self.assertEqual(result['status'],'failed');self.assertIn('missing proof',result['errors'][0]);old.assert_not_called()

if __name__=='__main__':unittest.main()
