import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_layout_equipment_ownership_graph


class OwnershipGateTests(unittest.TestCase):
    def fixture(self,folder):
        base=Path(folder);parent=base/'task/topology-rotated-equipment-identity/graph_with_edges.json'
        parent.parent.mkdir(parents=True);parent.write_text('{"sourceEquipmentIdentityResolution":{"records":[1]}}')
        root=base/'ownership';root.mkdir();graph=root/'graph_with_edges.json'
        graph.write_text(json.dumps(dict(sourceEquipmentIdentityResolution={'records':[1]},sourceLayoutEquipmentOwnership={'records':[1]},
            nodes=[dict(node_id='A',node_type='equipment',connection_status='source_calibrated_logical_interfaces_physical_ports_unknown'),
                   dict(node_id='B',node_type='equipment',connection_status='ports_unresolved')],edges=[])))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(graph),records=[dict(equipment_id='A')])
        previous=dict(status='pending',errors=[],pending=['native unresolved DN','2 equipment nodes have unresolved source-port ownership',
            'equipment labels source-checked; device port ownership, cross-view correspondence and human acceptance remain pending'],
            equipment_source_port_blockers=[{'node_id':'A'},{'node_id':'B'}],graph_unresolved_node_blockers=[],graph_algorithm_family_blockers=[],hil_ready=False)
        return root,parent,graph,audit,previous,sha

    def test_replay_keeps_real_parent_report_and_recomputes_current_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder)
            report={'graph_sha256':'older-screen-ancestor'}
            with patch('calibrated_equipment_interface_ownership.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=previous) as recurse:
                result=check_layout_equipment_ownership_graph(root,report,sha(graph),graph)
            recurse.assert_called_once_with(report,sha(parent),parent.parent.parent,parent)
            self.assertIn('native unresolved DN',result['pending'])
            self.assertIn('1 equipment nodes have unresolved source-port ownership',result['pending'])
            self.assertNotIn('2 equipment nodes have unresolved source-port ownership',result['pending'])
            self.assertEqual([r['node_id'] for r in result['equipment_source_port_blockers']],['B'])
            self.assertEqual(result['ownership_parent_comparison'],previous)
            self.assertFalse(result['hil_ready']);self.assertFalse(result['source_layout_equipment_ownership_stage']['human_accepted'])

    def test_parent_errors_and_unrelated_pending_are_not_cleared(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder);previous['errors']=['bad native line coverage']
            with patch('calibrated_equipment_interface_ownership.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=previous):
                result=check_layout_equipment_ownership_graph(root,{},sha(graph),graph)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['errors'],previous['errors'])

    def test_changed_parent_and_unbound_output_fail(self):
        for variant in ('parent','output'):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,previous,sha=self.fixture(folder)
                if variant=='parent':parent.write_text('{"changed":true}')
                else:audit['output_graph_sha256']='wrong'
                with patch('calibrated_equipment_interface_ownership.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_layout_equipment_ownership_graph(root,{},sha(graph),graph)

    def test_dispatch_ownership_before_inherited_identity_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder)
            with patch('calibrated_equipment_interface_ownership.verify_output',side_effect=ValueError('native ownership changed')),patch('resolve_rotated_equipment_labels.verify_output') as wrong:
                result=check({},sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('native ownership changed',result['errors'][0]);wrong.assert_not_called()

    def test_edge_claim_without_root_requires_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder)
            graph.write_text('{"edges":[{"source_layout_equipment_interface":{"equipment_id":"A"}}]}')
            with patch('calibrated_equipment_interface_ownership.verify_output',side_effect=ValueError('missing native proof')):
                self.assertEqual(check({},sha(graph),root,graph)['status'],'failed')

    def test_scope_composition_receipt_dispatches_native_v2_before_parent(self):
        from calibrated_ownership_scope_composition import MODE
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder)
            (root/'calibrated-equipment-ownership-audit.json').write_text(json.dumps({'mode':MODE}),encoding='utf8')
            with patch('calibrated_ownership_scope_composition.verify_output',return_value=audit) as current,patch('calibrated_equipment_interface_ownership.verify_output') as old,patch('source_comparison_gate.check',return_value=previous):
                result=check_layout_equipment_ownership_graph(root,{},sha(graph),graph)
            current.assert_called_once_with(graph.parent);old.assert_not_called();self.assertFalse(result['hil_ready']);self.assertIn('native unresolved DN',result['pending'])


if __name__=='__main__':unittest.main()
