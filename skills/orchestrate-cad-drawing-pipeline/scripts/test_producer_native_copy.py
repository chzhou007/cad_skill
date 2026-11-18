"""Real copying, failed copying and installed Windows native copy provenance."""
import json,os,shutil,subprocess,sys,unittest
from pathlib import Path
import test_producer_input_observation as fixtures
import delivered_source_input_runtime as adapter
import producer_input_observation as observation

class ProducerNativeCopyTests(unittest.TestCase):
    setUp=fixtures.ProducerObservationTests.setUp
    runtime=fixtures.ProducerObservationTests.runtime
    observed=fixtures.ProducerObservationTests.observed
    finish=fixtures.ProducerObservationTests.finish

    def test_real_native_copy_resolves_delivered_source_and_proves_output(self):
        runtime,obs=self.observed(strict=True);target=self.work/'component.csv'
        result=obs.copy_file('shutil.copy2',shutil.copy2,self.host,target,follow_symlinks=True)
        self.assertEqual(result,target);self.assertEqual(target.read_bytes(),self.delivered.read_bytes())
        with obs.call('io.open',runtime.io_open,(target,'rb'),{})as f:self.assertEqual(f.read(),self.delivered.read_bytes())
        report=self.finish(obs);self.assertTrue(report['strict_API_input_gate_passed'])
        self.assertEqual(report['events'][-1]['provenance']['writer']['operation'],'shutil.copy2')

    def test_copy_to_directory_records_actual_file_not_directory(self):
        runtime,obs=self.observed(strict=True)
        result=obs.copy_file('shutil.copy2',shutil.copy2,self.host,self.work,follow_symlinks=True)
        target=Path(result);self.assertTrue(target.is_file())
        report=self.finish(obs);self.assertEqual(report['owned_successful_effects'][0]['path'],runtime.key(target))

    def test_failed_copy_retains_real_exception_and_creates_no_writer(self):
        runtime,obs=self.observed(strict=True);target=self.work/'missing/failed.csv'
        with self.assertRaises(FileNotFoundError)as direct:shutil.copy2(self.delivered,target)
        with self.assertRaises(FileNotFoundError)as actual:obs.copy_file('shutil.copy2',shutil.copy2,self.host,target,follow_symlinks=True)
        self.assertEqual(actual.exception.errno,direct.exception.errno)
        report=self.finish(obs);self.assertEqual(report['owned_successful_effects'],[])
        self.assertEqual(report['events'][-1]['outcome'],'raised')

    def test_external_destination_and_unqualified_owned_source_stay_held(self):
        runtime,obs=self.observed(strict=True)
        with self.assertRaises(PermissionError):obs.copy_file('shutil.copy2',shutil.copy2,self.host,self.root/'outside.csv')
        old=self.work/'unproved.csv';old.write_text('existing does not mean produced')
        with self.assertRaises(PermissionError):obs.copy_file('shutil.copy2',shutil.copy2,old,self.work/'not-produced.csv')
        self.assertFalse((self.root/'outside.csv').exists());self.assertFalse((self.work/'not-produced.csv').exists())
        self.assertEqual(self.finish(obs)['owned_successful_effects'],[])

    def test_installed_real_copy2_roundtrip_retains_native_source_metadata(self):
        entry=self.work/'entry.py';output=self.work/'copied.txt'
        entry.write_text("import shutil\nfrom pathlib import Path\np=shutil.copy2("+repr(str(self.host))+","+repr(str(output))+")\nprint(Path(p).read_text(encoding='utf8'))\n",encoding='utf8')
        runtime,_=self.observed(strict=True,owned_seeds={'entry.py':observation.sha(entry)})
        code="""import sys,pkgutil
sys.path.insert(0,sys.argv[1])
from delivered_source_input_runtime import Runtime
Runtime.install_native_fonts=lambda self:None
Runtime.install_multiprocessing=lambda self:None
r=Runtime(sys.argv[2],sys.argv[3],sys.argv[4]);r.execute([sys.argv[5]])
"""
        result=subprocess.run([sys.executable,'-I','-X','utf8','-B','-c',code,str(Path(adapter.__file__).parent),
            str(self.package),str(self.work),runtime.index_sha256,str(entry)],cwd=self.work,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(output.read_bytes(),self.delivered.read_bytes())
        self.assertEqual(output.stat().st_mtime_ns,self.delivered.stat().st_mtime_ns)
        reports=[json.loads(p.read_text('utf8'))for p in(self.work/'producer-observation').glob('*.json')]
        actual=next(x for x in reports if x['pid']!=os.getpid())
        self.assertTrue(actual['strict_API_input_gate_passed'])
        self.assertTrue(any(x['operation']=='shutil.copy2'and x['outcome']=='returned'for x in actual['events']))
if __name__=='__main__':unittest.main()
