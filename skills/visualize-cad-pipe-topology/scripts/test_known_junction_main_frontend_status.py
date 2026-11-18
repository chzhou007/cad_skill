import subprocess
import unittest
from pathlib import Path

class FrontendStatusTests(unittest.TestCase):
    def test_native_direct_main_properties_CSV_and_unknown_claim_guards(self):
        result=subprocess.run(['node',str(Path(__file__).with_suffix('.mjs'))],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
