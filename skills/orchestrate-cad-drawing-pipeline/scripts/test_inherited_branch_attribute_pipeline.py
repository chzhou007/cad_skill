import subprocess,sys,unittest
from pathlib import Path
class InheritedBranchEntryPipeline(unittest.TestCase):
    def test_reconstruct_and_independent_validate_reach_original_arguments(self):
        for command,flag in [('reconstruct-inherited-branch-attributes','--manifest'),('validate-inherited-branch-attributes','--verify-output')]:
            p=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('pipeline.py')),command,'--help'],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn(flag,p.stdout)
if __name__=='__main__':unittest.main()
