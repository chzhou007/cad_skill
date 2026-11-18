import subprocess,sys,unittest
from pathlib import Path
class InheritedEntryViewerPipeline(unittest.TestCase):
    def test_publisher_and_independent_validator_have_public_entrypoints(self):
        for command,flag in [('refresh-inherited-branch-attribute-viewer','--parent-provider'),('validate-inherited-branch-attribute-viewer','--verify-output')]:
            result=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('pipeline.py')),command,'--help'],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn(flag,result.stdout)
if __name__=='__main__':unittest.main()
