import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from test_attach_external_feed_plan_attributes import fixture as source_fixture
from attach_external_feed_plan_attributes import append,ROOT,FIELD,NODE_FIELD
from external_feed_plan_viewer_evidence import verify
from build_visualization import verified_source_attribute_ancestor


def fixture(root):
    args=source_fixture();old=args[0];graph,stage=append(*args);p=root/'parent';p.mkdir();parent=p/'graph_with_edges.json';parent.write_text(json.dumps(old),encoding='utf-8');ph=hashlib.sha256(parent.read_bytes()).hexdigest()
    f=root/'new';f.mkdir();g=f/'graph_with_edges.json';g.write_text(json.dumps(graph),encoding='utf-8');gh=hashlib.sha256(g.read_bytes()).hexdigest()
    audit=dict(stage=copy.deepcopy(stage),output_graph_sha256=gh,hil_ready=False,human_accepted=False,parent_graph=dict(path=str(parent),sha256=ph),verified_prefix_parent=dict(output_graph_sha256=ph))
    return g,graph,audit


class Tests(unittest.TestCase):
    def test_actual_builder_dispatch_precedes_retained_prefix_and_requires_root(self):
        graph={ROOT:{'new':True},'sourceNetworkNamedLowerPlanAttributes':{'old':True}}
        with patch('external_feed_plan_viewer_evidence.verify',return_value=('BASE',{})) as native,patch('network_named_lower_plan_viewer_evidence.verify') as old:
            self.assertEqual(verified_source_attribute_ancestor(Path('G'),graph),('BASE',{}))
        native.assert_called_once();old.assert_not_called()
        for graph in (dict(edges=[{FIELD:{}}]),dict(nodes=[{NODE_FIELD:{}}])):
            with self.assertRaisesRegex(ValueError,'verified fusion stage'):verified_source_attribute_ancestor(None,graph)
    def test_new_root_replayed_once_and_fresh_complete_prefix_context_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp))
            with patch('attach_external_feed_plan_attributes.verify_output',return_value=audit) as native,patch('network_named_lower_plan_viewer_evidence.from_audit',return_value=(Path('BASE'),dict(records=['old']))) as prior:
                ancestor,proof=verify(g,graph)
            native.assert_called_once();prior.assert_called_once();self.assertEqual(ancestor,Path('BASE'));self.assertEqual(proof['records'],['old']);self.assertFalse(proof['hil_ready'])
    def test_changed_old_node_component_edge_or_destination_context_blocks(self):
        for case in ('old','edge','node','root','HIL'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                g,graph,audit=fixture(Path(temp))
                if case=='old':graph['retained_old_root']['unchanged']=False
                elif case=='edge':next(e for e in graph['edges'] if FIELD in e)[FIELD]['nominal_mm']=200
                elif case=='node':next(n for n in graph['nodes'] if NODE_FIELD in n)[NODE_FIELD]['destination']='elsewhere'
                elif case=='root':graph[ROOT]['records']=[]
                else:audit['hil_ready']=True
                g.write_text(json.dumps(graph),encoding='utf-8');audit['output_graph_sha256']=hashlib.sha256(g.read_bytes()).hexdigest()
                with patch('attach_external_feed_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):verify(g,graph)

if __name__=='__main__':unittest.main()
