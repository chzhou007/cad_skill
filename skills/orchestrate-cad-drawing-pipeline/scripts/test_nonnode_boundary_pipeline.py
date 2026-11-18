import subprocess,sys,unittest
from pathlib import Path

class NonNodeBoundaryEntryTests(unittest.TestCase):
    def test_native_and_viewer_commands_reach_their_real_parsers(self):
        entry=Path(__file__).with_name('pipeline.py')
        for name,flag in [('reconstruct-nonnode-boundary-branches','--manifest'),('validate-nonnode-boundary-branches','--verify-output'),('refresh-nonnode-boundary-viewer','--parent-provider'),('validate-nonnode-boundary-viewer','--verify-output')]:
            with self.subTest(command=name):
                p=subprocess.run([sys.executable,'-X','utf8','-B',str(entry),name,'--help'],capture_output=True,text=True,encoding='utf8')
                self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn(flag,p.stdout)

if __name__=='__main__':unittest.main()
