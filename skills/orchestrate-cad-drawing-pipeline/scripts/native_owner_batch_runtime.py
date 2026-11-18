"""Content-checked, job-local reuse for pinned immutable native owner functions.

Original owner modules and receipts stay unchanged. Nested captures propagate
their complete file/probe/scratch closure to the caller; external effects still
disable reuse. Never use this context around concurrent geometry threads.
"""
import contextlib,contextvars,copy,functools,hashlib,importlib.abc,importlib.machinery,os,sys
from collections import OrderedDict
from pathlib import Path

OWNERS=('crossview_equipment_branch_inventory_v2','crossview_equipment_branch_inventory',
    'reconstruct_native_block_branches','normalize_plan_circle_paths',
    'calibrated_equipment_interface_ownership','resolve_rotated_equipment_labels',
    'reconstruct_sideview_equipment_ownership')
ENTRIES=('attach_confirmed_gap_joints.py','canonicalize_confirmed_sideviews.py',
    'reconstruct_batch_circle_junctions.py','reconstruct_confirmed_equipment_pairs.py')
_active=contextvars.ContextVar('cad_native_owner_batch',default=None)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def merge_reads(parent,child):
    if parent is None:return
    parent.cacheable=parent.cacheable and child.cacheable
    parent.scratch_roots.update(child.scratch_roots)
    for name in('files','directories','probes'):
        target=getattr(parent,name)
        for key,value in getattr(child,name).items():
            if key in target and target[key]!=value:parent.cacheable=False
            else:target[key]=value

class Batch:
    def __init__(self,root,observer,max_entries=24):
        self.root=Path(root);self.observer=observer;self.max_entries=max_entries
        self.references={name:sha(self.root/'build-cad-pipe-topology/scripts'/(name+'.py'))for name in OWNERS}
        self.cache=OrderedDict();self.patched=[]
        self.stats=dict(native_owner_replays=0,content_checked_reuses=0,invalidations=0,uncacheable=0,persisted_trust=False)

    def invoke(self,module,original,directory):
        obs=self.observer;parent=obs._trace.get();path=Path(module.__file__).resolve()
        if sha(path)!=self.references[module.__name__]:raise ValueError('native owner implementation changed during batch')
        key=(str(path),os.path.normcase(os.path.abspath(os.fspath(directory))),id(original));environment=obs._environment()
        if key in self.cache:
            result,reads,prior=self.cache[key]
            if environment==prior and reads.unchanged():
                merge_reads(parent,reads);self.cache.move_to_end(key);self.stats['content_checked_reuses']+=1
                return copy.deepcopy(result)
            del self.cache[key];self.stats['invalidations']+=1
        reads=obs._Reads(allow_owned_scratch=True)
        with obs._capture_lock:
            previous_stat,previous_lstat=os.stat,os.lstat;os.stat,os.lstat=obs._tracked_stat,obs._tracked_lstat
            token=obs._trace.set(reads)
            try:
                # Include the owner pin itself in every enclosing closure.
                if sha(path)!=self.references[module.__name__]:raise ValueError('native owner code changed')
                result=original(directory)
            finally:
                obs._trace.reset(token);os.stat,os.lstat=previous_stat,previous_lstat
                merge_reads(parent,reads)
        self.stats['native_owner_replays']+=1
        if obs._environment()==environment and reads.unchanged():
            self.cache[key]=(copy.deepcopy(result),reads,environment)
            while len(self.cache)>self.max_entries:self.cache.popitem(last=False)
        else:self.stats['uncacheable']+=1
        return result

    def attach(self,module):
        name=module.__name__;path=getattr(module,'__file__',None);original=getattr(module,'verify_output',None)
        if name not in self.references or path is None or sha(path)!=self.references[name] or not callable(original):return
        if getattr(original,'_native_owner_batch',False):return
        @functools.wraps(original)
        def verify(directory,*args,**kwargs):
            if args or kwargs or _active.get() is not self:return original(directory,*args,**kwargs)
            return self.invoke(module,original,directory)
        verify._native_owner_batch=True;module.verify_output=verify;self.patched.append((module,original,verify))

    def close(self):
        for module,original,wrapper in reversed(self.patched):
            if module.verify_output is wrapper:module.verify_output=original
        self.cache.clear()

class Finder(importlib.abc.MetaPathFinder):
    def __init__(self,batch):self.batch=batch
    def find_spec(self,fullname,path=None,target=None):
        if fullname not in self.batch.references:return None
        spec=None
        # Preserve the projection runtime's existing loader instead of hiding
        # it behind a new PathFinder lookup.
        for finder in sys.meta_path[sys.meta_path.index(self)+1:]:
            if not hasattr(finder,'find_spec'):continue
            spec=finder.find_spec(fullname,path,target)
            if spec is not None:break
        if spec is None:return None
        original=spec.loader;batch=self.batch
        class Loader(importlib.abc.Loader):
            def create_module(self,spec):return original.create_module(spec)if hasattr(original,'create_module')else None
            def exec_module(self,module):original.exec_module(module);batch.attach(module)
        spec.loader=Loader();return spec

@contextlib.contextmanager
def owner_batch_runtime(root):
    current=_active.get()
    if current is not None:yield current;return
    if os.environ.get('CAD_NATIVE_OWNER_REUSE','1')=='0':yield None;return
    import native_replay_session as observer
    if not all(hasattr(observer,name)for name in('_Reads','_trace','_capture_lock','_tracked_stat','_tracked_lstat','_environment')):
        yield None;return
    root=Path(root);batch=Batch(root,observer);token=_active.set(batch);finder=Finder(batch);sys.meta_path.insert(0,finder)
    for name in OWNERS:
        if name in sys.modules:batch.attach(sys.modules[name])
    pins=[dict(path=str(root/'build-cad-pipe-topology/scripts'/n),sha256=sha(root/'build-cad-pipe-topology/scripts'/n))for n in ENTRIES]
    session=contextlib.nullcontext()if observer._session.get() is not None else observer.replay_session(allow_owned_scratch=True,python_replay_entries=pins)
    try:
        with session:yield batch
    finally:
        sys.meta_path.remove(finder);batch.close();_active.reset(token)
