import os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import native_replay_session as observer
from native_owner_batch_runtime import Batch,OWNERS,merge_reads

class Tests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);scripts=root/'build-cad-pipe-topology/scripts';scripts.mkdir(parents=True)
        for name in OWNERS:(scripts/(name+'.py')).write_text('# pinned owner '+name,encoding='utf8')
        batch=Batch(root,observer);modules=[types.SimpleNamespace(__name__=name,__file__=str(scripts/(name+'.py')))for name in OWNERS[:2]]
        return root,batch,modules

    def test_reuse_private_result_and_same_metadata_content_change_replays(self):
        with tempfile.TemporaryDirectory()as folder:
            root,batch,(module,_)=self.fixture(folder);p=root/'原始证据.txt';p.write_text('中文01',encoding='utf8');calls=[]
            def owner(directory):calls.append(1);return dict(value=p.read_text(encoding='utf8'),items=[1])
            a=batch.invoke(module,owner,root);a['items'].append(2)
            self.assertEqual(batch.invoke(module,owner,root)['items'],[1]);self.assertEqual(len(calls),1)
            before=p.stat();p.write_text('中文02',encoding='utf8');os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
            self.assertEqual(batch.invoke(module,owner,root)['value'],'中文02');self.assertEqual(len(calls),2)
            self.assertEqual(batch.stats['invalidations'],1);batch.close()

    def test_nested_dependency_closure_invalidates_outer_owner(self):
        with tempfile.TemporaryDirectory()as folder:
            root,batch,(parent,child)=self.fixture(folder);p=root/'deep.txt';p.write_text('first');calls=[]
            def inner(directory):calls.append('child');return p.read_text()
            def outer(directory):calls.append('parent');return batch.invoke(child,inner,directory)
            self.assertEqual(batch.invoke(parent,outer,root),'first')
            self.assertEqual(batch.invoke(parent,outer,root),'first');self.assertEqual(calls,['parent','child'])
            p.write_text('other');self.assertEqual(batch.invoke(parent,outer,root),'other')
            self.assertEqual(calls,['parent','child','parent','child']);batch.close()

    def test_negative_probe_new_file_and_owner_code_change_block_reuse(self):
        with tempfile.TemporaryDirectory()as folder:
            root,batch,(module,_)=self.fixture(folder);p=root/'optional.txt';calls=[]
            def owner(directory):calls.append(1);return p.exists()
            self.assertFalse(batch.invoke(module,owner,root));self.assertFalse(batch.invoke(module,owner,root));self.assertEqual(len(calls),1)
            p.write_text('new');self.assertTrue(batch.invoke(module,owner,root));self.assertEqual(len(calls),2)
            Path(module.__file__).write_text('changed')
            with self.assertRaisesRegex(ValueError,'implementation changed'):batch.invoke(module,owner,root)
            batch.close()

    def test_external_effects_uncacheable_and_failure_restores_stat_and_trace(self):
        with tempfile.TemporaryDirectory()as folder:
            root,batch,(module,_)=self.fixture(folder);calls=[];p=root/'external.txt'
            def owner(directory):calls.append(1);p.write_text('effect');return 1
            batch.invoke(module,owner,root);batch.invoke(module,owner,root);self.assertEqual(len(calls),2)
            original=os.stat;trace=observer._trace.get()
            def fail(directory):raise ValueError('native failed')
            with self.assertRaisesRegex(ValueError,'native failed'):batch.invoke(module,fail,root)
            self.assertIs(os.stat,original);self.assertIs(observer._trace.get(),trace);batch.close()

    def test_nested_closure_merges_into_existing_original_replay_session(self):
        with tempfile.TemporaryDirectory()as folder:
            root,batch,(module,_)=self.fixture(folder);p=root/'deep.txt';p.write_text('first');calls=[]
            def owner(directory):return p.read_text()
            def parent(directory):calls.append(1);return batch.invoke(module,owner,directory)
            with observer.replay_session(allow_owned_scratch=True):
                self.assertEqual(observer.verify_once(root,parent),'first');self.assertEqual(observer.verify_once(root,parent),'first');self.assertEqual(len(calls),1)
                p.write_text('new');self.assertEqual(observer.verify_once(root,parent),'new');self.assertEqual(len(calls),2)
            batch.close()

if __name__=='__main__':unittest.main()
