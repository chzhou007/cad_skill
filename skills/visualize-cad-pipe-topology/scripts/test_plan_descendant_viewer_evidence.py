import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from plan_descendant_viewer_evidence import verify
from confirm_crossview_paths import sha,encode


class Tests(unittest.TestCase):
    def fixture(self,wave=True):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name);child=r/'wave';child.mkdir();parent=r/'owner/graph_with_edges.json';parent.parent.mkdir();parent.write_bytes(encode(dict(nodes=[],edges=[])))
        current=child/'graph_with_edges.json';g=dict(nodes=[],edges=[])
        if wave:g['sourceInheritedWavePairContinuity']={}
        current.write_bytes(encode(g));audit=dict(output_graph_sha256=sha(current),inputs=dict(graph=dict(path=str(parent),sha256=sha(parent))))
        (child/'inherited-wave-receipt.json').write_bytes(encode(audit))
        return current,parent,g,audit

    def test_ordinary_graph_keeps_the_original_validation_path(self):
        p,parent,g,a=self.fixture(False)
        with patch('plan_descendant_viewer_evidence.verify_wave') as owner:
            ancestor,proof,paths=verify(p,g);owner.assert_not_called()
        self.assertEqual(ancestor,p.resolve());self.assertIsNone(proof);self.assertEqual(paths,{})

    def test_native_wave_ancestry_keeps_current_display_and_tracks_real_dependencies(self):
        p,parent,g,a=self.fixture();before=p.read_bytes()
        with patch('plan_descendant_viewer_evidence.verify_wave',return_value=a):ancestor,proof,paths=verify(p,g)
        self.assertEqual(ancestor,parent.resolve());self.assertEqual(p.read_bytes(),before);self.assertTrue(proof['display_current_graph_retained'])
        self.assertFalse(proof['old_receipts_rebound']);self.assertFalse(proof['hil_ready']);self.assertIn('plan_inherited_wave_owner',paths)

    def test_changed_graph_or_stale_native_parent_is_not_an_ancestry_match(self):
        p,parent,g,a=self.fixture();changed=copy.deepcopy(g);changed['fake']=True
        with self.assertRaisesRegex(ValueError,'actual input'):verify(p,changed)
        a['inputs']['graph']['sha256']='OLD'
        with patch('plan_descendant_viewer_evidence.verify_wave',return_value=a):
            with self.assertRaisesRegex(ValueError,'parent changed'):verify(p,g)

    def test_source_role_cannot_inherit_an_unbound_mapping_scope(self):
        p,parent,g,a=self.fixture();g['sourceDeclaredCappedBranchInterfaces']={};p.write_bytes(encode(g))
        with self.assertRaisesRegex(ValueError,'explicit project'):verify(p,g)
        with self.assertRaisesRegex(ValueError,'snapshot changed'):verify(p,g,dict(path=str(parent),sha256='OLD'))

    def test_cyclic_parent_rejected_before_any_display_substitution(self):
        p,parent,g,a=self.fixture();a['inputs']['graph']=dict(path=str(p),sha256=sha(p))
        with patch('plan_descendant_viewer_evidence.verify_wave',return_value=a):
            with self.assertRaisesRegex(ValueError,'cycles'):verify(p,g)

    def test_main_builder_noop_for_original_axis_and_dispatches_plan_child(self):
        from build_visualization import verified_plan_descendant_ancestor
        p,parent,g,a=self.fixture(False)
        self.assertEqual(verified_plan_descendant_ancestor(p,g),(p,None,{}))
        g['sourceDeclaredCappedBranchInterfaces']={};p.write_bytes(encode(g));before=copy.deepcopy(g)
        with self.assertRaisesRegex(ValueError,'missing graph-bound'):
            verified_plan_descendant_ancestor(p,g)
        scope=dict(path=str(parent),sha256=sha(parent));proof={'display_current_graph_retained':True}
        with patch('project_descendant_dispatch.snapshot_scope',return_value=(scope,parent)),patch('plan_descendant_viewer_evidence.verify',return_value=(parent,proof,{})) as owner:
            ancestor,actual,paths=verified_plan_descendant_ancestor(p,g);owner.assert_called_once_with(p,g,scope)
        self.assertEqual(ancestor,parent);self.assertEqual(actual,proof);self.assertEqual(g,before);self.assertEqual(paths['plan_project_snapshot_declaration'],parent)


if __name__=='__main__':unittest.main()
