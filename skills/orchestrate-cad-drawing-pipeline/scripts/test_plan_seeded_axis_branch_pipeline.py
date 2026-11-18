import subprocess,sys,unittest
from pathlib import Path

class PlanSeededBranchPipelineTests(unittest.TestCase):
    def test_native_reconstruction_and_independent_validation_reach_real_parser(self):
        entry=Path(__file__).with_name('pipeline.py')
        for command,flag in [('reconstruct-plan-seeded-axis-branch-DN','--manifest'),('validate-plan-seeded-axis-branch-DN','--verify-output')]:
            with self.subTest(command=command):
                result=subprocess.run([sys.executable,'-X','utf8','-B',str(entry),command,'--help'],capture_output=True,text=True,encoding='utf8')
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn(flag,result.stdout)
if __name__=='__main__':unittest.main()
