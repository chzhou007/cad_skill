import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from project_descendant_dispatch import snapshot_scope,check
from confirm_crossview_paths import encode,sha


class Tests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name);g={'sourceDeclaredCappedBranchInterfaces':{}}
        graph=r/'graph_with_edges.json';graph.write_bytes(encode(g));mapping=r/'mapping.json';mapping.write_bytes(encode({'records':[]}))
        declaration=r/'project-descendant-snapshot-scope.json';value=dict(graph_sha256=sha(graph),mapping=dict(path='mapping.json',sha256=sha(mapping)))
        declaration.write_bytes(encode(value));return r,graph,g,mapping,declaration,value

    def test_current_graph_bound_mapping_resolves_relative_to_declaration(self):
        r,p,g,m,d,v=self.fixture();scope,declaration=snapshot_scope(p,sha(p),g)
        self.assertEqual(scope,dict(path=str(m.resolve()),sha256=sha(m)));self.assertEqual(declaration,d.resolve())
        self.assertEqual(snapshot_scope(p,sha(p),{}),(None,None))

    def test_wrong_graph_changed_mapping_and_extra_overrides_block(self):
        for mode in ('graph','mapping','override','missing'):
            r,p,g,m,d,v=self.fixture()
            if mode=='graph':v['graph_sha256']='OLD'
            elif mode=='mapping':v['mapping']['sha256']='OLD'
            elif mode=='override':v['output']='elsewhere'
            else:d.unlink()
            if mode!='missing':d.write_bytes(encode(v))
            with self.subTest(mode=mode),self.assertRaises(ValueError):snapshot_scope(p,sha(p),g)

    def test_dispatch_calls_actual_native_consumer_with_explicit_scope_and_binds_declaration(self):
        r,p,g,m,d,v=self.fixture();native={'project_scoped_descendant_stage':{'source_replay':'passed'},'errors':[],'hil_ready':False}
        with patch('project_descendant_dispatch.check_project_descendant',return_value=native) as owner:
            result=check(r,{},sha(p),p);owner.assert_called_once_with(r.resolve(),{},p.resolve(),m.resolve(),sha(m))
        self.assertEqual(result['project_scoped_descendant_stage']['snapshot_declaration']['sha256'],sha(d));self.assertFalse(result['hil_ready'])

    def test_unrelated_graph_or_wrong_hash_cannot_reuse_declared_context(self):
        r,p,g,m,d,v=self.fixture()
        with self.assertRaises(ValueError):check(r/'other',{},sha(p),p)
        with self.assertRaises(ValueError):check(r,{},'OLD',p)

    def test_default_source_gate_dispatches_project_child_before_its_wave_ancestor(self):
        from source_comparison_gate import check as default_check
        r,p,g,m,d,v=self.fixture();g['sourceInheritedWavePairContinuity']={};p.write_bytes(encode(g))
        result={'status':'pending','errors':[],'hil_ready':False}
        with patch('project_descendant_dispatch.check',return_value=result) as owner,patch('inherited_wave_source_gate.check_inherited_wave_graph') as legacy:
            self.assertEqual(default_check({},sha(p),r,p),result);owner.assert_called_once();legacy.assert_not_called()

    def test_default_source_gate_keeps_old_errors_on_project_dispatch_failure(self):
        from source_comparison_gate import check as default_check
        r,p,g,m,d,v=self.fixture()
        with patch('project_descendant_dispatch.check',side_effect=ValueError('missing native evidence')):
            result=default_check({'errors':['old error'],'pending':['old issue']},sha(p),r,p)
        self.assertEqual(result['status'],'failed');self.assertIn('old error',result['errors']);self.assertEqual(result['pending'],['old issue']);self.assertFalse(result['hil_ready'])


if __name__=='__main__':unittest.main()
