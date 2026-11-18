import os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import native_replay_session as observer
import native_owner_batch_runtime_v2 as runtime


class Tests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);scripts=root/'build-cad-pipe-topology/scripts';scripts.mkdir(parents=True)
        modules=[]
        for name in runtime.OWNERS:
            source='from pathlib import Path\nCALLS=[]\ndef verify_output(directory):\n CALLS.append(1)\n return {"value":(Path(directory)/"source.txt").read_text(encoding="utf8"),"items":[1]}\n'
            path=scripts/(name+'.py');path.write_text(source,encoding='utf8')
            module=types.ModuleType(name);module.__file__=str(path)
            exec(compile(source,str(path),'exec'),module.__dict__);modules.append(module)
        for name in runtime.ENTRIES:(scripts/name).write_text('# entry\n',encoding='utf8')
        (root/'source.txt').write_text('中文01',encoding='utf8')
        return root,modules

    def test_preimported_aliases_share_fresh_proof_and_restore(self):
        with tempfile.TemporaryDirectory()as folder:
            root,modules=self.fixture(folder);module=modules[-1];original=module.verify_output
            consumer=types.ModuleType('test_native_consumer');consumer.prior_alias=original
            with patch.dict(sys.modules,{m.__name__:m for m in modules}|{consumer.__name__:consumer}):
                with runtime.owner_batch_runtime(root)as batch:
                    self.assertIs(consumer.prior_alias,module.verify_output)
                    a=consumer.prior_alias(root);a['items'].append(2)
                    self.assertEqual(module.verify_output(root)['items'],[1]);self.assertEqual(len(module.CALLS),1)
                    source=root/'source.txt';before=source.stat();source.write_text('中文02',encoding='utf8');os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
                    self.assertEqual(consumer.prior_alias(root)['value'],'中文02');self.assertEqual(len(module.CALLS),2)
                    self.assertGreater(batch.stats['imported_aliases_attached'],0)
                self.assertIs(module.verify_output,original);self.assertIs(consumer.prior_alias,original)

    def test_nested_alias_dependency_and_existing_session_invalidate(self):
        with tempfile.TemporaryDirectory()as folder:
            root,modules=self.fixture(folder);parent,child=modules[-2:]
            path=Path(parent.__file__)
            text='CALLS=[]\ndef verify_output(directory):\n CALLS.append(1)\n return child_alias(directory)\n'
            path.write_text(text,encoding='utf8');exec(compile(text,str(path),'exec'),parent.__dict__);parent.child_alias=child.verify_output
            with patch.dict(sys.modules,{m.__name__:m for m in modules}):
                with observer.replay_session(allow_owned_scratch=True):
                    with runtime.owner_batch_runtime(root)as batch:
                        self.assertEqual(parent.verify_output(root)['value'],'中文01');parent.verify_output(root)
                        self.assertEqual((len(parent.CALLS),len(child.CALLS)),(1,1))
                        (root/'source.txt').write_text('changed',encoding='utf8')
                        self.assertEqual(parent.verify_output(root)['value'],'changed')
                        self.assertEqual((len(parent.CALLS),len(child.CALLS)),(2,2))

    def test_new_owner_side_effects_not_reused_and_exception_restores(self):
        with tempfile.TemporaryDirectory()as folder:
            root,modules=self.fixture(folder);module=modules[-1];path=Path(module.__file__)
            text='from pathlib import Path\nCALLS=[]\ndef verify_output(directory):\n CALLS.append(1)\n (Path(directory)/"out.txt").write_text("effect")\n return 1\n'
            path.write_text(text,encoding='utf8');exec(compile(text,str(path),'exec'),module.__dict__);original=module.verify_output;stat=os.stat
            with patch.dict(sys.modules,{m.__name__:m for m in modules}):
                with self.assertRaisesRegex(ValueError,'stop'):
                    with runtime.owner_batch_runtime(root):
                        module.verify_output(root);module.verify_output(root);self.assertEqual(len(module.CALLS),2)
                        raise ValueError('stop')
                self.assertIs(module.verify_output,original);self.assertIs(os.stat,stat)

    def test_missing_or_nonmatching_owner_not_wrapped(self):
        with tempfile.TemporaryDirectory()as folder:
            root,modules=self.fixture(folder);module=modules[-1]
            with patch.dict(sys.modules,{m.__name__:m for m in modules}):
                with patch.dict(os.environ,{'CAD_NATIVE_OWNER_REUSE':'0'}):
                    with runtime.owner_batch_runtime(root)as batch:self.assertIsNone(batch)
                batch=runtime.Batch(root,observer);old=module.verify_output
                Path(module.__file__).write_text('# changed',encoding='utf8');batch.attach(module)
                self.assertIs(module.verify_output,old);batch.close()

    def test_fresh_closure_validation_rehashes_and_merges_without_recursive_tracing(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=root/'source.txt';source.write_text('中文01',encoding='utf8')
            reads=observer._Reads();reads.files[str(source)]=observer._file_state(str(source));parent=observer._Reads();statistics={}
            token=observer._trace.set(parent);original=observer._Reads.unchanged;busy=getattr(observer._guard,'busy',False)
            try:
                with runtime.fresh_closure_validation(observer,statistics):
                    self.assertTrue(reads.unchanged());self.assertEqual(parent.files,reads.files)
                    old=source.stat();source.write_text('中文02',encoding='utf8');os.utime(source,ns=(old.st_atime_ns,old.st_mtime_ns))
                    self.assertFalse(reads.unchanged())
                self.assertIs(observer._Reads.unchanged,original);self.assertEqual(getattr(observer._guard,'busy',False),busy)
                self.assertEqual(statistics['closure_checks'],2)
            finally:observer._trace.reset(token)

    def test_uncacheable_child_closure_disables_enclosing_capture(self):
        reads=observer._Reads();reads.cacheable=False;parent=observer._Reads();token=observer._trace.set(parent)
        try:
            with runtime.fresh_closure_validation(observer,{}):self.assertFalse(reads.unchanged())
            self.assertFalse(parent.cacheable)
        finally:observer._trace.reset(token)

    def test_nested_owner_inherits_known_outer_scratch_without_external_write_bypass(self):
        with tempfile.TemporaryDirectory()as folder:
            root,modules=self.fixture(folder);parent,child=modules[-2:]
            text='from pathlib import Path\nimport tempfile\nCALLS=[]\ndef verify_output(directory):\n CALLS.append(1)\n with tempfile.TemporaryDirectory()as scratch:\n  (Path(scratch)/"source.txt").write_text((Path(directory)/"source.txt").read_text(encoding="utf8"),encoding="utf8")\n  return child_alias(scratch)\n'
            path=Path(parent.__file__);path.write_text(text,encoding='utf8');exec(compile(text,str(path),'exec'),parent.__dict__);parent.child_alias=child.verify_output
            with patch.dict(sys.modules,{m.__name__:m for m in modules}):
                with runtime.owner_batch_runtime(root)as batch:
                    self.assertEqual(parent.verify_output(root)['value'],'中文01')
                    self.assertEqual(parent.verify_output(root)['value'],'中文01')
                    self.assertEqual((len(parent.CALLS),len(child.CALLS)),(1,1))
                    self.assertGreater(batch.stats['inherited_owned_scratch_scopes'],0)
                    self.assertEqual(batch.stats['uncacheable_events'],{})

if __name__=='__main__':unittest.main()
