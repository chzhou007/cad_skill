import subprocess,sys,unittest
from pathlib import Path
class PlanBranchViewerPipeline(unittest.TestCase):
    def test_viewer_entries_reach_real_parsers(self):
        for command,flag in [('refresh-plan-seeded-branch-DN-viewer','--parent-provider'),('validate-plan-seeded-branch-DN-viewer','--verify-output')]:
            result=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('pipeline.py')),command,'--help'],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn(flag,result.stdout)
if __name__=='__main__':unittest.main()
