import threading,time,types,unittest
from unittest.mock import patch
from feature_impact import run_selected

class Tests(unittest.TestCase):
    def test_parallel_subprocesses_preserve_order_failure_and_all_results(self):
        lock=threading.Lock();active=0;peak=0
        def run(cmd,**kwargs):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.04)
            with lock:active-=1
            return types.SimpleNamespace(returncode=3 if 'test_b'in cmd else 0,stdout='中文',stderr='')
        data=dict(tests=['a/scripts/test_a.py','b/scripts/test_b.py','c/scripts/test_c.py'],fallback_full_suites=False)
        with patch('feature_impact.subprocess.run',side_effect=run):r=run_selected(data,workers=2)
        self.assertEqual([x['skill']for x in r],['a','b','c']);self.assertEqual([x['exit_code']for x in r],[0,3,0]);self.assertEqual(peak,2);self.assertEqual(r[0]['stdout'],'中文')
    def test_worker_bound_serial_and_invalid_output_still_fail(self):
        data=dict(tests=['a/scripts/test_a.py'],fallback_full_suites=False)
        with patch('feature_impact.subprocess.run',side_effect=UnicodeDecodeError('utf8',b'\xff',0,1,'bad')):self.assertEqual(run_selected(data,workers=1)[0]['exit_code'],1)
        for workers in (0,True,33):
            with self.assertRaises(ValueError):run_selected(data,workers=workers)
if __name__=='__main__':unittest.main()
