"""Keep deterministic concurrency coverage outside the byte-locked old fixture."""
import threading,types,unittest
from unittest.mock import patch
from feature_impact import run_selected

class Tests(unittest.TestCase):
    def test_four_workers_reach_barrier_without_hidden_failure_or_duplicate_case(self):
        active=0;peak=0;lock=threading.Lock();environments=[];started=threading.Barrier(4)
        def invoke(command,**kwargs):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active);environments.append(kwargs['env'])
            started.wait(timeout=10)
            with lock:active-=1
            return types.SimpleNamespace(returncode=7 if 'test_07'in command else 0,stdout='中文',stderr='')
        expected=['test_%02d'%i for i in range(30)]
        with patch('feature_impact.subprocess.run',side_effect=invoke):
            rows=run_selected(dict(tests=['one/scripts/'+n+'.py'for n in expected],fallback_full_suites=False),workers=4)
        self.assertEqual(sorted(n for row in rows for n in row['command'][3:]),expected)
        self.assertEqual(len(rows),4);self.assertEqual(peak,4);self.assertEqual(sum(r['exit_code']!=0 for r in rows),1)
        self.assertTrue(all(e['CAD_NATIVE_WORKERS']==e['CAD_TEST_WORKERS']=='1'for e in environments))

if __name__=='__main__':unittest.main()
