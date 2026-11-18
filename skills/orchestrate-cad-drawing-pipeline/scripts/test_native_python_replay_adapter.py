import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from native_replay_session import replay_session,verify_once


class Tests(unittest.TestCase):
    def fixture(self,root):
        entry=root/'producer.py';source=root/'input.json';source.write_text('{"value":1}','utf8')
        entry.write_text("from pathlib import Path\nimport sys,json\nsource=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir()\n(out/'graph.json').write_text(json.dumps(json.loads(source.read_text('utf8'))),'utf8')\n",'utf8')
        pin=dict(path=str(entry),sha256=hashlib.sha256(entry.read_bytes()).hexdigest());calls=[]
        def verify(directory):
            calls.append(1)
            with tempfile.TemporaryDirectory() as scratch:
                out=Path(scratch)/'replay'
                subprocess.run([sys.executable,'-X','utf8',str(entry),str(source),str(out)],check=True,stdout=subprocess.DEVNULL)
                return json.loads((out/'graph.json').read_text('utf8'))
        return entry,source,pin,calls,verify

    def test_explicit_native_child_reads_remain_visible_and_match_a_real_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry,source,pin,calls,verify=self.fixture(root);expected=verify(root);argv=list(sys.argv)
            with replay_session(allow_owned_scratch=True,python_replay_entries=[pin]) as session:
                self.assertEqual(verify_once(root,verify),expected);self.assertEqual(verify_once(root,verify),expected)
                self.assertEqual(session.statistics()['inprocess_replayed_children'],1)
                self.assertEqual(session.statistics()['same_batch_reuses'],1)
                source.write_text('{"value":2}','utf8');self.assertEqual(verify_once(root,verify),{'value':2})
                self.assertEqual(session.statistics()['invalidations'],1)
            self.assertEqual(sys.argv,argv);self.assertEqual(len(calls),3)

    def test_unpinned_or_stale_native_child_cannot_gain_cached_trust(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry,source,pin,calls,verify=self.fixture(root)
            with replay_session(allow_owned_scratch=True) as session:
                verify_once(root,verify);verify_once(root,verify)
                self.assertEqual(session.statistics()['same_batch_reuses'],0)
            with replay_session(allow_owned_scratch=True,python_replay_entries=[pin]):
                verify_once(root,verify);entry.write_text(entry.read_text('utf8')+'\n# changed\n','utf8')
                with self.assertRaisesRegex(ValueError,'producer changed'):verify_once(root,verify)

    def test_real_child_errors_and_controlled_child_errors_cannot_be_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry,source,pin,calls,verify=self.fixture(root)
            entry.write_text('raise SystemExit(3)\n','utf8');pin['sha256']=hashlib.sha256(entry.read_bytes()).hexdigest()
            with replay_session(allow_owned_scratch=True,python_replay_entries=[pin]) as session:
                for _ in range(2):
                    with self.assertRaises(subprocess.CalledProcessError):verify_once(root,verify)
                self.assertEqual(session.statistics()['same_batch_reuses'],0)

if __name__=='__main__':unittest.main()
