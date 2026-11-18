import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from attach_anchored_floor_main_attributes import ROOT,FIELD
from anchored_floor_main_viewer_evidence import verify
from build_visualization import verified_source_attribute_ancestor

def fixture(root):
    parent=root/'parent';parent.mkdir();p=parent/'graph_with_edges.json';old=dict(metadata=dict(old=True),nodes=[],edges=[dict(edge_id='E',system='supply')],old_source_root=dict(retained=True));p.write_text(json.dumps(old),encoding='utf-8');ph=hashlib.sha256(p.read_bytes()).hexdigest()
    graph=copy.deepcopy(old);row=dict(axis_edge='E',nominal_mm=None);graph['edges'][0][FIELD]=copy.deepcopy(row)
    stage=dict(records=[row],prior_topology_components_and_attributes_preserved=True,related_HIL_confirmation_inherited=False);graph[ROOT]=copy.deepcopy(stage)
    folder=root/'new';folder.mkdir();g=folder/'graph_with_edges.json';g.write_text(json.dumps(graph),encoding='utf-8');gh=hashlib.sha256(g.read_bytes()).hexdigest()
    audit=dict(stage=stage,output_graph_sha256=gh,human_accepted=False,hil_ready=False,parent_graph=dict(path=str(p),sha256=ph),verified_wave_parent=dict(output_graph_sha256=ph))
    return g,graph,audit
class Tests(unittest.TestCase):
    def test_new_root_replayed_once_and_prior_fresh_audit_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp))
            with patch('attach_anchored_floor_main_attributes.verify_output',return_value=audit) as native,patch('wave_plan_scope_viewer_evidence.from_audit',return_value=(Path('BASE'),dict(records=['old']))) as prior:
                ancestor,proof=verify(g,graph)
            native.assert_called_once();prior.assert_called_once();self.assertEqual(ancestor,Path('BASE'));self.assertEqual(proof['records'],['old']);self.assertEqual(proof['output_graph_sha256'],audit['output_graph_sha256']);self.assertFalse(proof['hil_ready'])
    def test_dispatch_precedes_wave_and_missing_stage_blocks(self):
        graph={ROOT:dict(yes=True),'sourceWaveRebasedPlanScopeAdoption':dict(old=True)}
        with patch('anchored_floor_main_viewer_evidence.verify',return_value=('BASE',{})) as current,patch('wave_plan_scope_viewer_evidence.verify') as old:
            self.assertEqual(verified_source_attribute_ancestor(Path('G'),graph),('BASE',{}))
        current.assert_called_once();old.assert_not_called()
        with self.assertRaisesRegex(ValueError,'verified fusion stage'):verified_source_attribute_ancestor(None,dict(edges=[{FIELD:{}}]))
    def test_prior_values_component_geometry_or_edge_root_mismatch_blocks(self):
        for case in ('prior','edge','root','HIL'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                g,graph,audit=fixture(Path(temp))
                if case=='prior':graph['old_source_root']['retained']=False
                elif case=='edge':graph['edges'][0][FIELD]['nominal_mm']=999
                elif case=='root':graph[ROOT]['records']=[]
                else:audit['hil_ready']=True
                g.write_text(json.dumps(graph),encoding='utf-8');audit['output_graph_sha256']=hashlib.sha256(g.read_bytes()).hexdigest()
                with patch('attach_anchored_floor_main_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):verify(g,graph)
if __name__=='__main__':unittest.main()
