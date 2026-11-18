import concurrent.futures,types,unittest
import observed_vertical_DN_workers as runtime
_TEST_STATE='original'
def initialize(value):
    global _TEST_STATE
    _TEST_STATE=value
def repeated_job(handles):return dict(value=_TEST_STATE,handles=handles[:])
def collect(value,workers=7):
    groups=[['H'+str(i)]for i in range(workers)];result=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,initializer=initialize,initargs=(value,))as pool:
        futures={pool.submit(repeated_job,group):i for i,group in enumerate(groups)}
        for future in concurrent.futures.as_completed(futures):result.append(dict(batch=futures[future],value=future.result()))
    return sorted(result,key=lambda r:r['batch'])
class Tests(unittest.TestCase):
    def test_exact_worker_and_group_code_reused_with_private_globals(self):
        module=types.SimpleNamespace(**globals());statistics=dict(native_worker_groups=0,native_worker_initializations=0);original_executor=concurrent.futures.ProcessPoolExecutor;f=runtime.projected_collect(module,statistics);out=f('private',7)
        self.assertIs(f.__code__,collect.__code__);self.assertIs(f.__globals__['repeated_job'].__code__,repeated_job.__code__);self.assertIs(f.__globals__['initialize'].__code__,initialize.__code__);self.assertEqual([x['batch']for x in out],list(range(7)));self.assertEqual([x['value']['handles']for x in out],[['H'+str(i)]for i in range(7)]);self.assertTrue(all(x['value']['value']=='private'for x in out));self.assertEqual(_TEST_STATE,'original');self.assertIs(concurrent.futures.ProcessPoolExecutor,original_executor);self.assertEqual(statistics,dict(native_worker_groups=7,native_worker_initializations=1))
    def test_unknown_task_or_initializer_is_not_exempted(self):
        statistics=dict(native_worker_groups=0,native_worker_initializations=0);f=runtime.projected_collect(types.SimpleNamespace(**globals()),statistics);factory=f.__globals__['concurrent'].futures.ProcessPoolExecutor;init=f.__globals__['initialize']
        with self.assertRaises(ValueError):factory(max_workers=7,initializer=initialize,initargs=('x',))
        with factory(max_workers=7,initializer=init,initargs=('x',))as executor:
            with self.assertRaises(ValueError):executor.submit(lambda x:x,['H'])
        self.assertEqual(_TEST_STATE,'original')
if __name__=='__main__':unittest.main()
