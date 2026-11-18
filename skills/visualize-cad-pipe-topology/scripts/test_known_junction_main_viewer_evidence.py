import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILLS=Path(__file__).resolve().parents[2]
for p in (SKILLS/'build-cad-pipe-topology/scripts',SKILLS/'orchestrate-cad-drawing-pipeline/scripts'):
    sys.path.insert(0,str(p))
from confirm_crossview_paths import encode,load,sha
import attach_known_junction_main_plan_attributes as owner
import test_known_junction_main_fusion_gate as fixture_module
import known_junction_main_viewer_evidence as viewer
import build_visualization as builder


def fixture(root):
    parent,child,prior,audit=fixture_module.fixture(root)
    external=root/'external/graph_with_edges.json';external.parent.mkdir();external.write_bytes(encode(dict(native='external parent')))
    current=audit['verified_complete_parent'];current.update(stage=dict(parent='current floor'),
        parent_graph=dict(path=str(external),sha256=sha(external)),verified_complete_parent=dict(output_graph_sha256=sha(external)))
    return parent,child,audit,external


class ViewerEvidenceTests(unittest.TestCase):
    def test_native_fusion_and_current_parent_are_restored_before_ancestry_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,child,audit,external=fixture(Path(temp));ancestor=Path(temp)/'native-axis.json'
            with (patch.object(owner,'verify_output',return_value=audit),patch('current_floor_scope_adoption_gate.restore') as restore_current,
                  patch('external_feed_plan_viewer_evidence.from_audit',return_value=(ancestor,dict(retained='prior proof'))) as previous):
                result,proof=viewer.verify(child,load(child))
            self.assertEqual(result,ancestor);self.assertEqual(proof['retained'],'prior proof')
            self.assertEqual(proof['known_junction_main_fusion_audit'],audit);self.assertFalse(proof['human_accepted'])
            restore_current.assert_called_once();self.assertEqual(previous.call_args.args[0],external)

    def test_changed_current_parent_or_external_ancestor_blocks(self):
        for scope in ('current','external'):
            with tempfile.TemporaryDirectory() as temp:
                parent,child,audit,external=fixture(Path(temp));(parent if scope=='current' else external).write_text('{}',encoding='utf-8')
                with patch.object(owner,'verify_output',return_value=audit),self.assertRaises(ValueError):viewer.verify(child,load(child))

    def test_new_root_dispatch_precedes_retained_parent_root(self):
        g={owner.ROOT:dict(owned=True),'sourceCurrentFloorPlanScopeAdoption':dict(retained=True)}
        expected=(Path('NATIVE'),dict(checked=True))
        with patch.object(viewer,'verify',return_value=expected) as selected,patch('current_floor_scope_viewer_evidence.verify',side_effect=AssertionError('wrong root')):
            self.assertEqual(builder.verified_source_attribute_ancestor(Path('CHILD'),g),expected)
        selected.assert_called_once()

    def test_dependency_paths_keep_parent_audit_in_parent_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,child,audit,_=fixture(Path(temp));audit.update(mapping_path=str(Path(temp)/'mapping/mapping.json'),attribute_scope_path=str(Path(temp)/'attrs/attributes.json'))
            proof=dict(known_junction_main_fusion_audit=audit,current_floor_plan_scope_adoption_audit=audit['verified_complete_parent'])
            base={'current_floor_scope_adoption_audit':parent.parent/'current-floor-plan-scope-adoption-audit.json'}
            with patch('current_floor_scope_viewer_evidence.dependency_paths',return_value=base) as previous:paths=viewer.dependency_paths(proof,child)
            self.assertEqual(previous.call_args.args[1],parent)
            self.assertEqual(paths['current_floor_scope_adoption_audit'].parent,parent.parent)
            self.assertEqual(paths['known_junction_main_fusion_audit'].parent,child.parent)
            self.assertEqual(paths['known_junction_main_attribute_receipt'].name,'known-main-attribute-receipt.json')

    def test_native_verification_failure_is_not_treated_as_ancestry(self):
        with patch.object(owner,'verify_output',side_effect=ValueError('native changed')),self.assertRaisesRegex(ValueError,'native changed'):
            viewer.verify(Path('UNKNOWN/graph_with_edges.json'),{})


if __name__=='__main__':unittest.main()
