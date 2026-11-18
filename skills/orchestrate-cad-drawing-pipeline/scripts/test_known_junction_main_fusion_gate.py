import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from confirm_crossview_paths import encode,sha
import attach_known_junction_main_plan_attributes as owner
import test_attach_known_junction_main_plan_attributes as fixture_module
import known_junction_main_fusion_gate as gate
import source_comparison_gate as dispatch


def fixture(root):
    p,l,m,a,h=fixture_module.fixture();p['sourceCurrentFloorPlanScopeAdoption']=dict(retained=True)
    parent=root/'parent/graph_with_edges.json';parent.parent.mkdir();parent.write_bytes(encode(p));h['parent']=sha(parent)
    g,stage=owner.append(p,l,m,a,h,[0]);child=root/'child/graph_with_edges.json';child.parent.mkdir();child.write_bytes(encode(g))
    prior=dict(status='failed',graph_sha256=sha(parent),errors=['older source blocker'],pending=['older ambiguity'],hil_ready=False)
    (parent.parent/'source-comparison-gate.json').write_bytes(encode(prior))
    audit=dict(stage=stage,parent_graph=dict(path=str(parent),sha256=sha(parent)),verified_complete_parent=dict(output_graph_sha256=sha(parent)),
        output_graph_sha256=sha(child),human_accepted=False,hil_ready=False)
    return parent,child,prior,audit


class FusionSourceGateTests(unittest.TestCase):
    def test_old_errors_and_pending_are_preserved_without_accepting_floor(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,child,prior,audit=fixture(Path(temp))
            with patch.object(owner,'verify_output',return_value=audit):result=gate.check(child.parent,prior,sha(child),child)
            self.assertEqual(result['errors'],prior['errors']);self.assertEqual(result['pending'][:-1],prior['pending'])
            self.assertEqual(result['status'],'failed');self.assertFalse(result['human_accepted']);self.assertFalse(result['hil_ready'])

    def test_foreign_comparison_cannot_drop_old_issues(self):
        with tempfile.TemporaryDirectory() as temp:
            _,child,prior,audit=fixture(Path(temp))
            with patch.object(owner,'verify_output',return_value=audit),self.assertRaisesRegex(ValueError,'discarded'):
                gate.check(child.parent,dict(prior,errors=[]),sha(child),child)

    def test_changed_complete_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,child,prior,audit=fixture(Path(temp));parent.write_text('{}',encoding='utf-8')
            with patch.object(owner,'verify_output',return_value=audit),self.assertRaisesRegex(ValueError,'parent changed'):
                gate.check(child.parent,prior,sha(child),child)

    def test_outermost_new_root_dispatch_precedes_retained_current_floor_root(self):
        with tempfile.TemporaryDirectory() as temp:
            _,child,prior,_=fixture(Path(temp));expected=dict(status='pending',errors=[],pending=['kept'],hil_ready=False)
            with patch.object(gate,'check',return_value=expected) as selected,patch('current_floor_scope_adoption_gate.check',side_effect=AssertionError('wrong retained root')):
                self.assertEqual(dispatch.check(prior,sha(child),child.parent,child),expected)
            selected.assert_called_once()

    def test_native_failure_cannot_fall_back_to_the_retained_root(self):
        with tempfile.TemporaryDirectory() as temp:
            _,child,prior,_=fixture(Path(temp))
            with patch.object(gate,'check',side_effect=ValueError('native changed')):
                result=dispatch.check(prior,sha(child),child.parent,child)
            self.assertEqual(result['status'],'failed');self.assertIn('native changed',str(result['errors']))
            self.assertFalse(result['hil_ready'])


if __name__=='__main__':unittest.main()
