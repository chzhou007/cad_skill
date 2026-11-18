import json,os,shutil,tempfile,unittest
from pathlib import Path
from native_replay_session import replay_session,verify_once


class Tests(unittest.TestCase):
    def test_fresh_deleted_native_replay_outputs_can_be_reused_and_inputs_still_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.json';source.write_text('{"n":1}','utf8');calls=[]
            def verify(directory):
                calls.append(1);value=json.loads(source.read_text('utf8'))
                with tempfile.TemporaryDirectory() as scratch:
                    out=Path(scratch)/'replay';out.mkdir();p=out/'graph.json';p.write_text(json.dumps(value),'utf8')
                    self.assertTrue(p.is_file());self.assertEqual([p.name],os.listdir(out))
                    return json.loads(p.read_text('utf8'))
            with replay_session(allow_owned_scratch=True) as session:
                self.assertEqual(verify_once(root,verify),{'n':1});self.assertEqual(verify_once(root,verify),{'n':1})
                self.assertEqual(len(calls),1);self.assertEqual(session.statistics()['same_batch_reuses'],1)
                source.write_text('{"n":2}','utf8');self.assertEqual(verify_once(root,verify),{'n':2})
                self.assertEqual(len(calls),2);self.assertEqual(session.statistics()['invalidations'],1)
                self.assertGreater(session.statistics()['owned_scratch_scopes'],0)

    def test_default_strict_mode_does_not_ignore_temporary_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.write_text('source','utf8')
            def verify(directory):
                value=source.read_text('utf8')
                with tempfile.TemporaryDirectory() as scratch:(Path(scratch)/'out').write_text(value,'utf8')
                return value
            with replay_session() as session:
                verify_once(root,verify);verify_once(root,verify)
                self.assertEqual(session.statistics()['same_batch_reuses'],0)

    def test_preexisting_temp_inputs_are_dependencies_and_persistent_new_temp_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'existing';source.write_text('one','utf8');calls=[]
            def verify(directory):calls.append(1);return source.read_text('utf8')
            with replay_session(allow_owned_scratch=True) as session:
                verify_once(root,verify);source.write_text('two','utf8')
                self.assertEqual(verify_once(root,verify),'two');self.assertEqual(len(calls),2)
            scratch=[]
            def persistent(directory):
                value=source.read_text('utf8');scratch.append(tempfile.mkdtemp());return value
            try:
                with replay_session(allow_owned_scratch=True) as session:
                    verify_once(root,persistent);verify_once(root,persistent)
                    self.assertEqual(session.statistics()['same_batch_reuses'],0)
            finally:
                for p in scratch:shutil.rmtree(p)

    def test_external_writes_and_renames_are_never_covered_by_owned_temporary_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input';source.write_text('value','utf8')
            def writer(directory):
                value=source.read_text('utf8')
                with tempfile.TemporaryDirectory() as scratch:
                    (Path(scratch)/'out').write_text(value,'utf8');(root/'external').write_text(value,'utf8')
                return value
            def rename(directory):
                value=source.read_text('utf8');a=root/'a';b=root/'b';a.rename(b);b.rename(a);return value
            (root/'a').write_text('a','utf8')
            for fn in [writer,rename]:
                with self.subTest(fn=fn.__name__),replay_session(allow_owned_scratch=True) as session:
                    verify_once(root,fn);verify_once(root,fn);self.assertEqual(session.statistics()['same_batch_reuses'],0)

    def test_temporary_symlink_to_an_existing_input_cannot_hide_source_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.write_text('one','utf8');calls=[]
            try:
                trial=root/'trial';trial.symlink_to(source);trial.unlink()
            except OSError as exc:self.skipTest(str(exc))
            def verify(directory):
                calls.append(1)
                with tempfile.TemporaryDirectory() as scratch:
                    link=Path(scratch)/'link';link.symlink_to(source);return link.read_text('utf8')
            with replay_session(allow_owned_scratch=True) as session:
                verify_once(root,verify);source.write_text('two','utf8')
                self.assertEqual(verify_once(root,verify),'two');self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
