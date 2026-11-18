import copy,io,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from confirm_crossview_paths import encode,sha
from test_reconstruct_native_block_branches import fixture
import reconstruct_native_block_branches as kernel
from native_projection_runtime_v1 import Runtime,accelerated_native_runtime,default_native_runtime,worker_count

class Tests(unittest.TestCase):
    def test_default_runtime_uses_existing_plain_graph_clone_and_preserves_original(self):
        root=Path(__file__).resolve().parents[2];g=dict(nodes=[dict(node_id='暖通井')],edges=[dict(edge_id='E',path=[[0,0],[1,1]])]);original=copy.deepcopy
        with accelerated_native_runtime(root,1)as runtime:
            result=copy.deepcopy(g);result['edges'][0]['path'][0][0]=3
            self.assertEqual(g['edges'][0]['path'][0][0],0)
            self.assertTrue(runtime.stats['graph_copy']['enabled']);self.assertGreater(runtime.stats['graph_copy']['graph_copies'],0)
        self.assertIs(copy.deepcopy,original)

    def test_graph_copy_disabled_or_other_threads_keep_original(self):
        root=Path(__file__).resolve().parents[2];original=copy.deepcopy
        for setting in ('disabled','threads'):
            with patch.dict(os.environ,{'CAD_NATIVE_GRAPH_COPY':'0'}if setting=='disabled'else {}),patch('native_projection_runtime_v1.threading.active_count',return_value=2 if setting=='threads'else 1):
                with accelerated_native_runtime(root,1)as runtime:
                    self.assertIs(copy.deepcopy,original);self.assertFalse(runtime.stats['graph_copy']['enabled'])

    def fixture(self,folder):
        doc,g,_,_,_=fixture(True);source=Path(folder)/'source.dxf';doc.saveas(source);graph=Path(folder)/'graph.json';graph.write_bytes(encode(g));return doc,g,dict(graph=str(graph)),sha(source)
    def test_same_job_projection_reuse_keeps_results_private_and_source_changes_fail(self):
        with tempfile.TemporaryDirectory()as folder:
            doc,g,paths,sh=self.fixture(folder);expected=kernel.projected_coverage(doc,g,'E',sh);runtime=Runtime(Path(__file__).resolve().parents[2],2);runtime.min_parallel_edges=0
            runtime.service=types.SimpleNamespace(stdin=io.StringIO(),stdout=io.StringIO(json.dumps(dict(status='ok',records={'E':dict(status='ok',proof=expected)}))+'\n'),stderr=io.StringIO(),wait=lambda **kw:None,returncode=0)
            runtime.attach(kernel)
            try:
                def invoke(paths):return kernel.projected_coverage(doc,g,'E',sh)
                result=invoke(paths);result[0]['coverage']['edge_id']='consumer edit';self.assertEqual(invoke(paths),expected);self.assertEqual(runtime.stats['native_batches'],1);self.assertEqual(runtime.stats['same_job_projection_reuses'],1)
                Path(doc.filename).write_text('source changed',encoding='utf8')
                with self.assertRaisesRegex(RuntimeError,'source changed'):invoke(paths)
            finally:runtime.close()
    def test_nested_runtime_shares_one_scope_and_serial_control_does_not_create_it(self):
        root=Path(__file__).resolve().parents[2]
        with accelerated_native_runtime(root,2)as outer:
            with accelerated_native_runtime(root,2)as inner:self.assertIs(outer,inner)
        with patch.dict(os.environ,{'CAD_NATIVE_PARALLEL':'0'}):
            with default_native_runtime(root)as disabled:self.assertIsNone(disabled)
        with patch.dict(os.environ,{'CAD_NATIVE_WORKERS':'33'}):
            with self.assertRaises(ValueError):worker_count()
if __name__=='__main__':unittest.main()
