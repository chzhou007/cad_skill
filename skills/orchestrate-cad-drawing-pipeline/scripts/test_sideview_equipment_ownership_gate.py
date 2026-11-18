import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_sideview_equipment_ownership_graph


class SideviewOwnershipGateTests(unittest.TestCase):
    def fixture(self,folder,family=False):
        root=Path(folder).resolve();parent=root/'parent/topology-source-layout-equipment-ownership/graph_with_edges.json'
        parent.parent.mkdir(parents=True);parent.write_text('{}')
        output=root/'task' if family else root/'output';output.mkdir()
        directory=output/'topology-source-sideview-equipment-ownership' if family else output
        directory.mkdir(exist_ok=True);graph=directory/'graph_with_edges.json'
        graph.write_text(json.dumps(dict(sourceSideviewEquipmentOwnership={},sourceLayoutEquipmentOwnership={'records':[1]},nodes=[],edges=[])))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(parent),sha256=sha(parent)),inputs={'source':{'sha256':'SOURCE'}},records=[])
        previous=dict(status='pending',errors=[],pending=['independent source conflict','1 equipment nodes have unresolved source-port ownership'],
            equipment_source_port_blockers=[{'node_id':'A'}],graph_unresolved_node_blockers=[],graph_algorithm_family_blockers=[],hil_ready=False)
        if family:
            (directory/'sideview-equipment-ownership-audit.json').write_text('{}')
            (output/'reports').mkdir();receipt=dict(status='native_confirmed_sideview_logical_ownership_source_checked',artifact_directory=str(directory),graph_sha256=sha(graph),parent_graph_sha256=sha(parent),source_sha256='SOURCE',audit_sha256=sha(directory/'sideview-equipment-ownership-audit.json'),hil_ready=False,physical_ports_verified=False,detail_view_metric_verified=False)
            (output/'reports/source-sideview-equipment-ownership-stage.json').write_text(json.dumps(receipt))
        return output,parent,graph,audit,previous,sha

    def test_ancestor_report_is_not_rebound_and_pending_is_preserved(self):
        for family in (False,True):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,previous,sha=self.fixture(folder,family);report={'graph_sha256':'original-screen'}
                with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=previous) as recurse:
                    result=check_sideview_equipment_ownership_graph(root,report,sha(graph),graph)
                recurse.assert_called_once_with(report,sha(parent),parent.parent.parent,parent)
                self.assertIn('independent source conflict',result['pending'])
                self.assertNotIn('1 equipment nodes have unresolved source-port ownership',result['pending'])
                self.assertEqual(result['sideview_ownership_parent_comparison'],previous)
                self.assertFalse(result['hil_ready']);self.assertFalse(result['source_sideview_equipment_ownership_stage']['detail_view_metric_verified'])

    def test_bad_ancestry_receipt_or_output_fails_closed(self):
        for variant in ('parent','output','receipt'):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,previous,sha=self.fixture(folder,True)
                if variant=='parent':parent.write_text('changed')
                elif variant=='output':audit['output_graph_sha256']='OTHER'
                else:
                    p=root/'reports/source-sideview-equipment-ownership-stage.json';d=json.loads(p.read_text());d['detail_view_metric_verified']=True;p.write_text(json.dumps(d))
                with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_sideview_equipment_ownership_graph(root,{},sha(graph),graph)

    def test_original_errors_remain_release_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,previous,sha=self.fixture(folder);previous['errors']=['bad source coverage']
            with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=previous):
                result=check_sideview_equipment_ownership_graph(root,{},sha(graph),graph)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['errors'],['bad source coverage'])

    def test_root_and_edge_claims_dispatch_before_inherited_ownership(self):
        for mode in ('root','edge'):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,previous,sha=self.fixture(folder)
                if mode=='edge':graph.write_text('{"edges":[{"source_sideview_equipment_interface":{}}],"sourceLayoutEquipmentOwnership":{"records":[1]}}')
                with patch('reconstruct_sideview_equipment_ownership.verify_output',side_effect=ValueError('missing native proof')),patch('calibrated_ownership_scope_composition.verify_ownership_output') as old:
                    result=check({},sha(graph),root,graph)
                self.assertEqual(result['status'],'failed');self.assertIn('missing native proof',result['errors'][0]);old.assert_not_called()


if __name__=='__main__':unittest.main()
