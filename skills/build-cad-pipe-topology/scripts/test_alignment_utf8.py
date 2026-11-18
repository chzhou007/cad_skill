import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import run_alignment

class AlignmentUTF8Test(unittest.TestCase):
    def test_all_children_receive_strict_utf8_streams(self):
        proof={'status':'PASS_STRICT_NATIVE_TEXT','source_sha256':'test','actual_read_codec':'utf-8','native_chinese_entity_count':1}
        with patch('run_alignment.read_source',return_value=(None,proof)), patch('run_alignment.subprocess.run') as run:
            run_alignment.run(Path('fixture'),Path('output'),Path('viewer'))
        self.assertEqual(run.call_count,3)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs['env']['PYTHONUTF8'],'1')
            self.assertEqual(call.kwargs['env']['PYTHONIOENCODING'],'utf-8:strict')

    def test_environment_produces_roundtrip_chinese_bytes(self):
        proof={'status':'PASS_STRICT_NATIVE_TEXT','source_sha256':'test','actual_read_codec':'utf-8','native_chinese_entity_count':1}
        with patch('run_alignment.read_source',return_value=(None,proof)), patch('run_alignment.subprocess.run') as run:
            run_alignment.run(Path('fixture'),Path('output'))
        env=run.call_args_list[0].kwargs['env']
        p=subprocess.run([sys.executable,'-c',"print('\u7ba1\u5f84')"],env=env,capture_output=True,check=True)
        self.assertEqual(p.stdout.decode('utf-8').strip(),'\u7ba1\u5f84')

    def test_unreadable_source_stops_before_children(self):
        with patch('run_alignment.read_source',side_effect=ValueError('unreadable')), patch('run_alignment.subprocess.run') as run:
            with self.assertRaises(ValueError):run_alignment.run(Path('fixture'),Path('output'))
        run.assert_not_called()

if __name__=='__main__':unittest.main()
