"""Exercise copytree's captured default copy2 through the installed observer."""
import json,os,subprocess,sys,unittest
from pathlib import Path
import delivered_source_input_runtime as adapter
import producer_input_observation as observation
import test_producer_input_observation as fixtures

class CopytreeObservationTests(unittest.TestCase):
    setUp=fixtures.ProducerObservationTests.setUp
    runtime=fixtures.ProducerObservationTests.runtime
    observed=fixtures.ProducerObservationTests.observed

    def execute(self,custom=False):
        source=self.work/'source';source.mkdir();(source/'nested').mkdir();original=source/'nested/app.js';original.write_text('中文源文件\n',encoding='utf8')
        entry=self.work/'entry.py';target=self.work/'output'
        call="shutil.copytree(src,dst,dirs_exist_ok=True)"
        if custom:call="shutil.copytree(src,dst,copy_function=reject,dirs_exist_ok=True)"
        entry.write_text("import shutil\nfrom pathlib import Path\nsrc=Path("+repr(str(source))+")\ndst=Path("+repr(str(target))+")\ndef reject(src,dst):\n raise OSError('custom copy failure')\n"+call+"\nprint((dst/'nested/app.js').read_text(encoding='utf8'))\n",encoding='utf8')
        runtime,_=self.observed(strict=True,owned_seeds={'entry.py':observation.sha(entry),'source/nested/app.js':observation.sha(original)})
        code="""import sys,pkgutil
sys.path.insert(0,sys.argv[1])
from delivered_source_input_runtime import Runtime
Runtime.install_native_fonts=lambda self:None
Runtime.install_multiprocessing=lambda self:None
r=Runtime(sys.argv[2],sys.argv[3],sys.argv[4]);r.execute([sys.argv[5]])
"""
        p=subprocess.run([sys.executable,'-I','-X','utf8','-B','-c',code,str(Path(adapter.__file__).parent),str(self.package),str(self.work),runtime.index_sha256,str(entry)],cwd=self.work,capture_output=True,text=True,encoding='utf8')
        reports=[json.loads(p.read_text('utf8'))for p in(self.work/'producer-observation').glob('*.json')]
        return p,original,target/'nested/app.js',next(x for x in reports if x['pid']!=os.getpid())

    def test_recursive_default_copy_records_each_successful_native_writer(self):
        p,original,target,report=self.execute();self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(target.read_bytes(),original.read_bytes());self.assertEqual(target.stat().st_mtime_ns,original.stat().st_mtime_ns)
        self.assertTrue(report['strict_API_input_gate_passed'])
        writers=[r for r in report['owned_successful_effects']if r['path']==os.path.normcase(str(target))]
        self.assertTrue(any(r['operation']=='shutil.copy2'for r in writers),'copytree default bypassed the observed copy2')

    def test_explicit_custom_copy_failure_never_grants_file_ownership(self):
        p,original,target,report=self.execute(custom=True);self.assertNotEqual(p.returncode,0)
        self.assertIn('custom copy failure',p.stderr);self.assertFalse(target.exists())
        self.assertFalse(any(r['path']==os.path.normcase(str(target))for r in report['owned_successful_effects']))

if __name__=='__main__':unittest.main()
