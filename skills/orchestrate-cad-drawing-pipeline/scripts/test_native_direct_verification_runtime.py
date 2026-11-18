import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from native_direct_verification_runtime import SUPPORTED_CACHE_LIBRARY_SHA256


class Tests(unittest.TestCase):
    def child(self,body):
        result=subprocess.run([sys.executable,'-c',body],cwd=Path(__file__).resolve().parent,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(result.returncode,0,result.stderr);return json.loads(result.stdout)

    def test_every_request_reopens_changed_native_input_and_propagates_verifier_errors(self):
        result=self.child("""
import tempfile,json
from pathlib import Path
from native_direct_verification_runtime import install,SUPPORTED_CACHE_LIBRARY_SHA256
info=install(SUPPORTED_CACHE_LIBRARY_SHA256)
import native_replay_session as runtime
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'source.txt';p.write_text('first');calls=[]
 def verify(directory):calls.append(str(directory));return {'native':p.read_text()}
 a=runtime.verify_once(tmp,verify);p.write_text('changed');b=runtime.verify_once(tmp,verify)
 assert a=={'native':'first'} and b=={'native':'changed'} and len(calls)==2
 with runtime.replay_session() as session:
  runtime.verify_once(tmp,verify);runtime.verify_once(tmp,verify)
  assert session.statistics()['native_replays']==2 and session.statistics()['same_batch_reuses']==0
 try:runtime.verify_once(tmp,lambda directory:(_ for _ in ()).throw(ValueError('native source changed')))
 except ValueError as error:assert str(error)=='native source changed'
 else:raise AssertionError('Native failure was suppressed')
 print(json.dumps(info()))
""")
        self.assertEqual(result['verify_once_requests'],5);self.assertEqual(result['cached_results_reused'],0)
        self.assertFalse(result['optional_cache_read_tracking']);self.assertTrue(result['all_requested_verifiers_called'])

    def test_runtime_never_replaces_an_imported_legacy_library(self):
        result=self.child("""
import json,native_replay_session
from native_direct_verification_runtime import install,SUPPORTED_CACHE_LIBRARY_SHA256
original=native_replay_session.verify_once
try:install(SUPPORTED_CACHE_LIBRARY_SHA256)
except RuntimeError:pass
else:raise AssertionError('Active runtime was replaced')
assert native_replay_session.verify_once is original
print(json.dumps({'legacy_unchanged':True}))
""")
        self.assertTrue(result['legacy_unchanged'])

    def test_unknown_library_version_is_rejected_before_installing_backend(self):
        result=self.child("""
import json,sys
from native_direct_verification_runtime import install
try:install('0'*64)
except ValueError:pass
else:raise AssertionError('Unknown cache library accepted')
assert 'native_replay_session' not in sys.modules
print(json.dumps({'unknown_version_rejected':True}))
""")
        self.assertTrue(result['unknown_version_rejected'])

    def test_worker_retains_native_failure_as_a_failed_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);job=folder/'job.json';report=folder/'report.json'
            job.write_text(json.dumps(dict(operation='verify_lower_parent',run=str(folder/'missing-run'),expected_output_graph_sha256='0'*64,expected_cache_library_sha256=SUPPORTED_CACHE_LIBRARY_SHA256)),'utf8')
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('native_direct_worker.py')),'--job',str(job),'--report',str(report)],capture_output=True,text=True,encoding='utf8')
            self.assertNotEqual(result.returncode,0);data=json.loads(report.read_text('utf8'))
            self.assertEqual(data['status'],'failed');self.assertIn('FileNotFoundError',data['error']);self.assertEqual(data['runtime']['cached_results_reused'],0)

    def test_new_cache_options_do_not_enable_reuse_in_explicit_direct_backend(self):
        result=self.child("""
import json
from native_direct_verification_runtime import install,SUPPORTED_CACHE_LIBRARY_SHA256
info=install(SUPPORTED_CACHE_LIBRARY_SHA256)
import native_replay_session as runtime
calls=[]
def verify(directory):calls.append(directory);return len(calls)
with runtime.replay_session(allow_owned_scratch=True,python_replay_entries=[]) as session:
 assert runtime.verify_once('input',verify)==1
 assert runtime.verify_once('input',verify)==2
 assert session.statistics()['same_batch_reuses']==0
print(json.dumps(info()))
""")
        self.assertEqual(result['verify_once_requests'],2);self.assertEqual(result['cached_results_reused'],0)


if __name__=='__main__':unittest.main()
