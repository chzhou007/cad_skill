import contextlib,io,json,sys,tempfile,time,unittest
from pathlib import Path
from run_native_task_batch import run,validate,sha

class Tests(unittest.TestCase):
    def test_isolated_jobs_share_budget_keep_utf8_and_block_only_failed_descendants(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);script=root/'job.py';script.write_text("import os,sys,time,json\nfrom pathlib import Path\ntime.sleep(.15)\nPath(sys.argv[1]).write_text(json.dumps(dict(workers=os.environ['CAD_NATIVE_WORKERS'],test_workers=os.environ['CAD_TEST_WORKERS'])),encoding='utf8')\nprint('中文输出')\nraise SystemExit(int(sys.argv[2]))\n",encoding='utf8')
            def job(ident,code=0,deps=()):return dict(id=ident,cores=1,cwd=str(root),command=[sys.executable,'-X','utf8','-B',str(script),str(root/(ident+'.json')),str(code)],depends_on=list(deps),inputs={str(script):sha(script)},outputs=[str(root/(ident+'.json'))])
            with contextlib.redirect_stdout(io.StringIO()):report=run(dict(schema_version=1,jobs=[job('a',3),job('b'),job('c',deps=['a']),job('d',deps=['b'])]),root/'logs',2)
            self.assertEqual([row['status']for row in report['jobs']],['failed','passed','blocked_by_dependency','passed'])
            self.assertEqual(report['peak_allocated_core_slots'],2);self.assertFalse((root/'c.json').exists())
            self.assertEqual(json.loads((root/'b.json').read_text()),dict(workers='1',test_workers='1'))
            self.assertIn('中文输出',(root/'logs/b.log').read_text(encoding='utf8'))
    def test_cycles_output_collisions_changed_inputs_and_budget_fail_before_execution(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=root/'source';source.write_text('before');row=dict(id='a',command=[sys.executable,'-V'],cwd=str(root),inputs={str(source):sha(source)})
            for jobs in ([dict(row,cores=3)],[dict(row,depends_on=['a'])],[row,dict(row,id='b',outputs=[str(root/'out')]),dict(row,id='c',outputs=[str(root/'out/child')])]):
                with self.assertRaises(ValueError):validate(dict(schema_version=1,jobs=jobs),2)
            source.write_text('after')
            with self.assertRaisesRegex(ValueError,'input changed'):validate(dict(schema_version=1,jobs=[row]),2)
    def test_zero_exit_missing_output_is_failure(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);job=dict(id='a',cwd=str(root),command=[sys.executable,'-V'],outputs=[str(root/'missing')])
            with contextlib.redirect_stdout(io.StringIO()):report=run(dict(schema_version=1,jobs=[job]),root/'logs',1)
            self.assertEqual(report['jobs'][0]['status'],'failed');self.assertIn('omitted',report['jobs'][0]['error']['message'])
if __name__=='__main__':unittest.main()
