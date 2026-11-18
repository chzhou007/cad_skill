"""Observe the original vertical-DN worker algorithm inside a native capture.

Only this fixed module's process boundary is projected. Group partitioning,
initializer, worker function, qualifications and final ordering retain their
original code. Private globals prevent worker state leaking into the owner.
Other executors/processes retain their ordinary observer policy.
"""
import concurrent.futures,contextlib,hashlib,importlib,sys,types
from pathlib import Path

MODULE='axis_vertical_DN_batch'

def projected_collect(module,statistics):
    namespace=dict(module.__dict__)
    def clone(fn):return types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
    initialize=clone(module.initialize);job=clone(module.repeated_job)
    class ObservedExecutor:
        def __init__(self,*,max_workers,initializer,initargs):
            if initializer is not initialize or type(max_workers)is not int or not 1<=max_workers<=22:raise ValueError('unsupported vertical native worker initializer')
            self.initializer=initializer;self.initargs=initargs
        def __enter__(self):
            self.initializer(*self.initargs);statistics['native_worker_initializations']+=1;return self
        def __exit__(self,*args):return False
        def submit(self,fn,handles):
            if fn is not job or not isinstance(handles,list)or any(not isinstance(h,str)for h in handles):raise ValueError('unsupported vertical native worker task')
            future=concurrent.futures.Future();statistics['native_worker_groups']+=1
            try:future.set_result(fn(handles))
            except BaseException as exc:future.set_exception(exc)
            return future
    namespace.update(initialize=initialize,repeated_job=job,concurrent=types.SimpleNamespace(futures=types.SimpleNamespace(ProcessPoolExecutor=ObservedExecutor,as_completed=concurrent.futures.as_completed)))
    return clone(module.collect)

@contextlib.contextmanager
def observe_vertical_workers(root,observer):
    module=importlib.import_module(MODULE);path=Path(module.__file__).resolve();expected=Path(root).resolve()/'build-cad-pipe-topology/scripts'/(MODULE+'.py')
    if path!=expected or any(getattr(getattr(module,name),'__module__',None)!=MODULE for name in('collect','initialize','repeated_job')):raise ValueError('vertical worker owner outside original skills')
    original=module.collect;digest=hashlib.sha256(path.read_bytes()).hexdigest();statistics=dict(native_worker_groups=0,native_worker_initializations=0,original_group_partition_preserved=True,generic_processes_exempted=0)
    projected=projected_collect(module,statistics)
    def collect(*args,**kwargs):
        if observer._trace.get()is None:return original(*args,**kwargs)
        Path(__file__).read_bytes()
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('original vertical worker algorithm changed')
        result=projected(*args,**kwargs)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('original vertical worker algorithm changed during reading')
        return result
    aliases=[]
    for item in list(sys.modules.values()):
        namespace=getattr(item,'__dict__',None)
        if not namespace:continue
        for name,value in list(namespace.items()):
            if value is original:namespace[name]=collect;aliases.append((namespace,name,original,collect))
    try:yield statistics
    finally:
        for namespace,name,prior,current in reversed(aliases):
            if namespace.get(name)is current:namespace[name]=prior
