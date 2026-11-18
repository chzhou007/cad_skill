import hashlib,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
from source_comparison_gate import check,check_crossview_attribute_graph
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))

class CrossviewAttributeGateTests(unittest.TestCase):
    def test_unreplayed_claim_and_edge_only_attributes_block(self):
        for graph in ({'crossViewAttributeFusion':{'claim':True}},{'edges':[{'cross_view_attributes':{'claim':True}}]}):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);p=root/'graph_with_edges.json';p.write_text(json.dumps(graph))
                out=check({},'G',root,p);self.assertEqual(out['status'],'failed');self.assertIn('cross-view attribute',out['errors'][0])
    def fixture(self,folder):
        root=Path(folder);parent=root/'parent';parent.mkdir();child=root/'child';child.mkdir()
        pg=parent/'graph.json';pg.write_text('{}');cg=child/'graph_with_edges.json';cg.write_text('{}')
        report={'graph_sha256':'PARENT'};rp=parent/'report.json';rp.write_text(json.dumps(report))
        audit=dict(output_graph_sha256='CHILD',parent_graph=dict(path=str(pg),sha256=hashlib.sha256(pg.read_bytes()).hexdigest()),
            inputs=dict(parent_report=dict(path=str(rp))),records=[dict(diameter_status='candidate_disagreement_unresolved',plan_horizontal_projection_mm=800)])
        return child,cg,pg,report,audit
    def test_parent_blockers_and_unknown_lengths_survive_partial_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            root,cg,pg,report,audit=self.fixture(folder);parent={'errors':[],'pending':['equipment scope still unresolved'],'hil_ready':False}
            with patch('attach_crossview_plan_attributes.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent):
                out=check_crossview_attribute_graph(root,report,'CHILD',cg)
            self.assertEqual(out['status'],'pending');self.assertIn('equipment scope still unresolved',out['pending']);self.assertFalse(out['hil_ready'])
            self.assertTrue(any('disagreements' in p for p in out['pending']));self.assertFalse(out['crossview_attribute_stage']['whole_edge_physical_lengths_complete'])
            self.assertEqual(parent['pending'],['equipment scope still unresolved'])
    def test_changed_parent_or_different_report_fails(self):
        for kind in ('parent','report'):
            with tempfile.TemporaryDirectory() as folder:
                root,cg,pg,report,audit=self.fixture(folder)
                if kind=='parent':pg.write_text('{"changed":true}')
                else:report={}
                with patch('attach_crossview_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):check_crossview_attribute_graph(root,report,'CHILD',cg)

if __name__=='__main__':unittest.main()
