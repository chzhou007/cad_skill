import contextlib,hashlib,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import native_replay_session as observer
import reuse_verified_native_artifact as cache

class Tests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);source=root/'原始CAD证据.txt';source.write_text('中文01',encoding='utf8')
        return root,source

    def test_full_bytes_not_size_or_timestamp_and_negative_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder);missing=root/'optional.txt'
            with cache.capture(observer) as reads:
                source.read_bytes();missing.exists()
            closed=cache.closure_payload(reads)
            self.assertTrue(cache.check_closure(closed,observer,4))
            before=source.stat();source.write_text('中文02',encoding='utf8');os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
            self.assertFalse(cache.check_closure(closed,observer,4))
            source.write_text('中文01',encoding='utf8');os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
            self.assertTrue(cache.check_closure(closed,observer,4))
            missing.write_text('new');self.assertFalse(cache.check_closure(closed,observer,4))

    def test_nested_native_sessions_merge_child_reads_and_owned_scratch(self):
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder)
            with observer.replay_session(allow_owned_scratch=True):
                with cache.capture(observer) as reads:
                    def child(_):
                        with tempfile.TemporaryDirectory() as scratch:
                            Path(scratch,'native-result.txt').write_text('own scratch')
                            return source.read_text(encoding='utf8')
                    self.assertEqual(observer.verify_once(root,child),'中文01')
            closed=cache.closure_payload(reads)
            self.assertIn(os.path.normcase(str(source)),closed['files']);self.assertTrue(closed['scratch_roots'])
            self.assertTrue(cache.check_closure(closed,observer,2))
            source.write_text('changed');self.assertFalse(cache.check_closure(closed,observer,2))

    def test_external_writes_and_failures_do_not_create_reusable_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder);prior=os.stat;trace=observer._trace.get()
            with cache.capture(observer) as reads:
                source.read_bytes();(root/'unowned').write_text('effect')
            self.assertFalse(cache.check_closure(cache.closure_payload(reads),observer,2))
            with self.assertRaisesRegex(ValueError,'bad'):
                with cache.capture(observer):raise ValueError('bad')
            self.assertIs(os.stat,prior);self.assertIs(observer._trace.get(),trace)

    def test_binding_changes_for_code_and_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder)
            with patch.object(cache,'inventory',return_value=[str(source)]):
                _,a=cache.binding(root,'owner',root,2)
                with patch.dict(os.environ,{'CAD_CACHE_TEST_SETTING':'changed'}):_,b=cache.binding(root,'owner',root,2)
                self.assertNotEqual(a,b)
                source.write_text('中文02',encoding='utf8');_,c=cache.binding(root,'owner',root,2)
                self.assertNotEqual(a,c)

    def test_empty_optional_plot_style_read_is_rechecked_negative_probe(self):
        import builtins,io
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder)
            with cache.capture(observer) as reads:
                source.read_bytes()
                with self.assertRaises(FileNotFoundError):open('','r')
            closure=cache.closure_payload(reads)
            self.assertEqual(len(closure['empty_read_probes']),1)
            self.assertTrue(cache.check_closure(closure,observer,2))
            original=builtins.open
            def changed(name,*args,**kwargs):return io.StringIO('unexpected') if name=='' else original(name,*args,**kwargs)
            with patch.object(builtins,'open',changed):self.assertFalse(cache.check_closure(closure,observer,2))

    def test_cold_then_hit_force_replay_corruption_and_changed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root,source=self.fixture(folder);skills=root/'skills';script=skills/'build-cad-pipe-topology/scripts/rebuild_compound_member_projections.py'
            script.parent.mkdir(parents=True);script.write_text('# fixture native owner\n')
            native=root/'native';native.mkdir();result=dict(text='中文01',items=[1])
            from confirm_crossview_paths import encode
            (native/'member-projections.json').write_bytes(encode(result))
            module=types.ModuleType('rebuild_compound_member_projections');module.__file__=str(script);calls=[]
            def verify(_):calls.append(1);return dict(text=source.read_text(encoding='utf8'),items=[1])
            module.verify_output=verify
            @contextlib.contextmanager
            def runtime(_):yield types.SimpleNamespace(stats={})
            with patch.dict(sys.modules,{module.__name__:module}),patch.object(cache,'inventory',return_value=[str(script)]),patch('native_projection_runtime_v1.default_native_runtime',runtime),patch.object(sys,'dont_write_bytecode',True),patch.object(sys,'path',list(sys.path)):
                first=cache.run(skills,module.__name__,native,root/'cache',root/'first',workers=2)
                self.assertTrue(first['native_replay_performed']);self.assertTrue(first['cache_stored']);self.assertEqual(len(calls),1)
                second=cache.run(skills,module.__name__,native,root/'cache',root/'second',workers=2)
                self.assertTrue(second['dependency_checked_reuse'],str(second));self.assertFalse(second['native_replay_performed']);self.assertEqual(len(calls),1)
                self.assertEqual((root/'first/proof.json').read_bytes(),(root/'second/proof.json').read_bytes())
                self.assertFalse(second['human_accepted'])
                cache.run(skills,module.__name__,native,root/'cache',root/'forced',force_native=True,workers=2);self.assertEqual(len(calls),2)
                Path(first['cache_file']).write_text('{corrupt',encoding='utf8')
                repaired=cache.run(skills,module.__name__,native,root/'cache',root/'repaired',workers=2)
                self.assertTrue(repaired['native_replay_performed']);self.assertEqual(len(calls),3)
                before=source.stat();source.write_text('中文02',encoding='utf8');os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
                with self.assertRaisesRegex(ValueError,'artifact replay differs'):
                    cache.run(skills,module.__name__,native,root/'cache',root/'changed',workers=2)
                self.assertEqual(len(calls),4);self.assertFalse((root/'changed').exists())

    def test_unsupported_owner_and_output_in_native_proof_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(sys,'dont_write_bytecode',True):
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'unsupported'):
                cache.run(root,'arbitrary_command',root,root/'cache',root/'out')
            with self.assertRaisesRegex(ValueError,'must not mutate'):
                cache.run(root,next(iter(cache.OWNERS)),root,root/'cache',root/'out')

    def test_pipeline_routes_application_without_wrapping_as_fresh_validation(self):
        import pipeline
        previous=['pipeline.py','reuse-native-artifact','--owner','rebuild_noncompound_main_extents']
        with patch.object(sys,'argv',previous),patch.object(cache,'main',return_value=0) as entry:
            self.assertEqual(pipeline.main(),0);entry.assert_called_once();self.assertIs(sys.argv,previous)

if __name__=='__main__':unittest.main()
