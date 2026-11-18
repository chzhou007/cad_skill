import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
_p=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(_p)not in sys.path:sys.path.insert(0,str(_p))
from test_full_batch_axis_attributes import fixture
from full_batch_axis_attribute_composition import append,ROOT
from validate_full_batch_plan_attributes import validate
from build_visualization import verified_source_attribute_ancestor


def graph_fixture():
    args=list(fixture());h=args[-1]
    h.update(identity_graph='d'*64,plan_graphs={'1':'f'*64},plan_sources={'1':'a'*64},axis_source='e'*64,mapping_receipt='b'*64,DN_receipt='c'*64,parent_graph='1'*64)
    args[4]['identity_graph_sha256']=h['identity_graph'];args[6]['floors']['1']['graph_sha256']=h['plan_graphs']['1']
    g=append(*args);g['sourceCheckedCrossViewAttributeEvidence']=dict(full_batch_plan_attribute_fusion_audit=dict(stage=copy.deepcopy(g[ROOT]),human_accepted=False,hil_ready=False))
    return g


class Tests(unittest.TestCase):
    def test_builder_dispatches_current_batch_before_old_prefix_and_fails_without_root(self):
        expected=('raw-native',{'current':True})
        with patch('full_batch_plan_attribute_viewer.verify',return_value=expected)as fn:
            self.assertEqual(verified_source_attribute_ancestor('g',dict(sourceFullPlanBatchAttributes={'mode':'current'},nodes=[],edges=[])),expected);fn.assert_called_once()
        with self.assertRaises(ValueError):verified_source_attribute_ancestor('g',dict(edges=[dict(batch_plan_attribute_scopes={})]))
    def test_bundle_checks_current_scope_root_and_original_axis_extent(self):
        g=graph_fixture();self.assertEqual(validate(g)['current_edges'],1)
        with self.assertRaises(ValueError):validate(g,object(),'changed')
        g['edges'][0]['batch_plan_attribute_scopes']['plan_drawn_nominal_mm']=200
        with self.assertRaises(ValueError):validate(g)
    def test_missing_native_composition_proof_cannot_be_certified_by_carrier_fields(self):
        g=graph_fixture();g.pop('sourceCheckedCrossViewAttributeEvidence')
        with self.assertRaises(ValueError):validate(g)


if __name__=='__main__':unittest.main()
