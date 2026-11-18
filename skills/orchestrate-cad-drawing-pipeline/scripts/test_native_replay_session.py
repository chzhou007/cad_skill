import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from native_replay_session import replay_session,verify_once


class Tests(unittest.TestCase):
    def fixture(self,root):
        source=root/'source.json';source.write_text('{"value":1}','utf8');calls=[]
        def verify(directory):
            calls.append(directory);return dict(native=json.loads(source.read_text('utf8')),source_output=[]) 
        return source,calls,verify
    def test_same_batch_reuses_only_fresh_verified_reads_and_keeps_mutations_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,verify=self.fixture(root)
            with replay_session() as session:
                first=verify_once(root,verify);first['source_output'].append('consumer change')
                second=verify_once(root,verify)
                self.assertEqual(second['source_output'],[]);self.assertEqual(len(calls),1)
                self.assertEqual(session.statistics()['same_batch_reuses'],1);self.assertGreater(session.statistics()['dependency_files'],0)
            verify_once(root,verify);self.assertEqual(len(calls),2)
    def test_changed_source_or_code_and_expired_batch_require_native_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,verify=self.fixture(root)
            with replay_session() as session:
                verify_once(root,verify);source.write_text('{"value":2}','utf8')
                self.assertEqual(verify_once(root,verify)['native']['value'],2);self.assertEqual(len(calls),2)
                self.assertEqual(session.statistics()['invalidations'],1)
            with replay_session():verify_once(root,verify)
            self.assertEqual(len(calls),3)
    def test_missing_dependency_appearance_and_directory_changes_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,base=self.fixture(root);optional=root/'optional.txt'
            def verify(directory):
                result=base(directory);result['files']=sorted(os.listdir(root))
                try:result['optional']=optional.read_text('utf8')
                except FileNotFoundError:result['optional']=None
                return result
            with replay_session() as session:
                self.assertIsNone(verify_once(root,verify)['optional']);optional.write_text('present','utf8')
                self.assertEqual(verify_once(root,verify)['optional'],'present');self.assertEqual(len(calls),2)
                self.assertEqual(session.statistics()['invalidations'],1)
    def test_failed_native_replay_is_never_cached_and_external_effects_disable_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,base=self.fixture(root)
            def fail(directory):base(directory);raise ValueError('source mismatch')
            with replay_session():
                for _ in range(2):
                    with self.assertRaises(ValueError):verify_once(root,fail)
            self.assertEqual(len(calls),2)
            def external(directory):
                import sys
                result=base(directory);sys.audit('subprocess.Popen','not_executed',[],None,None);return result
            with replay_session() as session:
                verify_once(root,external);verify_once(root,external)
                self.assertEqual(session.statistics()['same_batch_reuses'],0)
    def test_environment_change_invalidates_without_exporting_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,verify=self.fixture(root)
            with replay_session() as session:
                verify_once(root,verify)
                with patch.dict(os.environ,{'CAD_TEST_CONTEXT':'changed'}):verify_once(root,verify)
                self.assertEqual(len(calls),2);self.assertNotIn('CAD_TEST_CONTEXT',str(session.statistics()))

    def test_stat_only_absence_checks_are_dependencies_and_writers_are_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,calls,base=self.fixture(root);optional=root/'appears-later.txt'
            def verify(directory):
                result=base(directory);result['exists']=optional.exists();return result
            with replay_session() as session:
                self.assertFalse(verify_once(root,verify)['exists']);optional.write_text('new','utf8')
                self.assertTrue(verify_once(root,verify)['exists']);self.assertEqual(session.statistics()['invalidations'],1)
            def writer(directory):
                result=base(directory);(root/'side-effect.txt').write_text('written','utf8');return result
            with replay_session() as session:
                verify_once(root,writer);verify_once(root,writer);self.assertEqual(session.statistics()['same_batch_reuses'],0)


if __name__=='__main__':unittest.main()
