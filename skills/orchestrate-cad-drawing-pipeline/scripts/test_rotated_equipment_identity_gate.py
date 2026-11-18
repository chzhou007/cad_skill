import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_equipment_identity_layout_graph

class LayoutIdentityGateTests(unittest.TestCase):
    def fixture(self,folder):
        base=Path(folder);parent=base/'task/topology-confirmed-near-tees/graph.json';parent.parent.mkdir(parents=True);parent.write_text('{}')
        output=base/'identity';output.mkdir();graph=output/'graph_with_edges.json';graph.write_text('{"sourceEquipmentIdentityResolution":{"records":[1]}}')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(graph),records=[dict(old_node_id='OLD',new_node_id='NEW')])
        return output,parent,graph,audit,sha
    def test_verified_identity_keeps_parent_blockers_and_unknown_ports(self):
        with tempfile.TemporaryDirectory() as folder:
            output,parent,graph,audit,sha=self.fixture(folder);report={'graph_sha256':sha(parent)}
            with patch('resolve_rotated_equipment_labels.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['old topology issue'])) as previous:
                result=check_equipment_identity_layout_graph(output,report,sha(graph),graph)
            previous.assert_called_once_with(report,sha(parent),parent.parent.parent,parent)
            self.assertIn('old topology issue',result['pending']);self.assertFalse(result['hil_ready']);self.assertFalse(result['equipment_identity_layout_stage']['ports_verified'])
    def test_changed_parent_or_wrong_report_fails(self):
        for change in ('parent','report'):
            with tempfile.TemporaryDirectory() as folder:
                output,parent,graph,audit,sha=self.fixture(folder);report={'graph_sha256':sha(parent)}
                if change=='parent':parent.write_text('{"changed":true}')
                else:report['graph_sha256']='wrong'
                with patch('resolve_rotated_equipment_labels.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_equipment_identity_layout_graph(output,report,sha(graph),graph)
    def test_graph_flag_alone_cannot_skip_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            output,parent,graph,audit,sha=self.fixture(folder)
            with patch('resolve_rotated_equipment_labels.verify_output',side_effect=ValueError('native layout differs')):
                result=check({},sha(graph),output,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('native layout differs',result['errors'][0])

if __name__=='__main__':unittest.main()
