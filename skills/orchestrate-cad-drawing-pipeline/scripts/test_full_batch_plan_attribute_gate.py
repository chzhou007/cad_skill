import copy,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
_OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(_OWNER)not in sys.path:sys.path.insert(0,str(_OWNER))
from confirm_crossview_paths import encode,sha
from full_batch_plan_attribute_gate import check


class Tests(unittest.TestCase):
    def test_source_gate_preserves_old_defects_and_does_not_promote_HIL(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);parent=root/'parent';current=root/'current';parent.mkdir();current.mkdir()
            pp=parent/'graph_with_edges.json';pp.write_bytes(encode(dict(nodes=[],edges=[])))
            gp=current/'graph_with_edges.json';gp.write_bytes(encode(dict(sourceFullPlanBatchAttributes=dict(identity_aliases={}),nodes=[],edges=[])))
            prior=dict(graph_sha256=sha(pp),errors=['old defect'],pending=['old pending']);(parent/'source-comparison-gate.json').write_bytes(encode(prior))
            audit=dict(output_graph_sha256=sha(gp),parent_graph=dict(path=str(pp),sha256=sha(pp)),verified_complete_parent=dict(output_graph_sha256=sha(pp)),summary=dict(current_axis_scope_edges=1))
            with patch('compose_full_batch_plan_attributes.verify_output',return_value=audit),patch('full_batch_axis_attribute_composition.restore'):
                result=check(current,prior,sha(gp),gp)
                self.assertEqual(result['errors'],['old defect']);self.assertEqual(result['status'],'failed');self.assertFalse(result['hil_ready'])
                self.assertIn('old pending',result['pending'])
                with self.assertRaises(ValueError):check(current,dict(prior,errors=[]),sha(gp),gp)
                pp.write_bytes(b'changed')
                with self.assertRaises(ValueError):check(current,prior,sha(gp),gp)


if __name__=='__main__':unittest.main()
