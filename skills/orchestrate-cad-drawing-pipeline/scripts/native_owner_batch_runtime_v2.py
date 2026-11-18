"""Batch immutable native ancestry, including already imported verifier aliases.

The original verifier executes before reuse; its transitive observed dependency
closure is rehashed on each reuse. No result persists across jobs. Unknown side
effects disable reuse, and consumers receive independent values.
"""
import contextlib
import contextvars
import functools
import hashlib
import importlib.abc
import importlib.machinery
import os
import sys
import time
from pathlib import Path
from native_owner_batch_runtime import Batch as OriginalBatch, ENTRIES, OWNERS as ORIGINAL_OWNERS, merge_reads

OWNERS = ORIGINAL_OWNERS + (
    'attach_reviewed_interface_owners', 'reconstruct_reviewed_plan_gaps',
    'reconstruct_wave_main_cohorts', 'apply_crossview_rule_batch',
    'rebuild_wave_cohort_crossview_batch', 'extend_native_main_chain_batch',
    'rebuild_full_plan_DN', 'rebuild_inherited_full_plan_DN',
    'rebuild_main_continuity_full_plan_DN', 'rebuild_confirmed_overlap_full_plan_DN',
    'rebuild_user_circle_full_plan_DN', 'rebuild_current_circle_full_plan_DN',
    'rebuild_local_detail_full_plan_DN', 'rebuild_projected_circle_full_plan_DN',
    'confirmed_compound_pipe_lanes', 'confirmed_member_plan_paths',
    'ordered_group_plan_lengths', 'ordered_anchor_branch_paths',
    'rebuild_anchor_bounded_main_batch', 'rebuild_compound_member_projections',
)
_active = contextvars.ContextVar('cad_native_owner_batch_v2', default=None)


class Batch(OriginalBatch):
    def __init__(self, root, observer, max_entries=64):
        super().__init__(root, observer, max_entries=max_entries)
        scripts=Path(root)/'build-cad-pipe-topology/scripts'
        for name in OWNERS:
            path=scripts/(name+'.py')
            if path.is_file():self.references[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        self.aliases=[];self.wrappers={}
        self.stats.update(imported_aliases_attached=0,by_owner={})

    def invoke(self, module, original, directory):
        counts=self.stats['by_owner'].setdefault(module.__name__,dict(calls=0,inclusive_seconds=0.0))
        counts['calls']+=1
        started=time.perf_counter()
        try:return super().invoke(module,original,directory)
        finally:counts['inclusive_seconds']+=time.perf_counter()-started

    def attach(self,module):
        name=module.__name__;path=getattr(module,'__file__',None);original=getattr(module,'verify_output',None)
        if name not in self.references or not path or not callable(original):return
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=self.references[name]:return
        if getattr(original,'_native_owner_batch',False):return
        # Only the module's own single-directory verifier, never an imported
        # verifier, arbitrary method, or another runtime's wrapper.
        if getattr(original,'__module__',None)!=name or not hasattr(original,'__code__'):return
        if Path(original.__code__.co_filename).resolve()!=Path(path).resolve():return
        @functools.wraps(original)
        def verify(directory,*args,**kwargs):
            if args or kwargs or _active.get() is not self:return original(directory,*args,**kwargs)
            return self.invoke(module,original,directory)
        verify._native_owner_batch=True
        module.verify_output=verify;self.patched.append((module,original,verify))
        self.wrappers[id(original)]=(original,verify)

    def attach_aliases(self,module):
        namespace=getattr(module,'__dict__',{})
        for name,value in list(namespace.items()):
            pair=self.wrappers.get(id(value))
            if pair and value is pair[0]:
                namespace[name]=pair[1];self.aliases.append((namespace,name,value,pair[1]))
                self.stats['imported_aliases_attached']+=1

    def close(self):
        for namespace,name,original,wrapper in reversed(self.aliases):
            if namespace.get(name)is wrapper:namespace[name]=original
        self.aliases.clear();self.wrappers.clear();super().close()


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self,batch):self.batch=batch
    def find_spec(self,fullname,path=None,target=None):
        if fullname not in self.batch.references:return None
        spec=None
        for finder in sys.meta_path[sys.meta_path.index(self)+1:]:
            if not hasattr(finder,'find_spec'):continue
            spec=finder.find_spec(fullname,path,target)
            if spec is not None:break
        if spec is None:return None
        original=spec.loader;batch=self.batch
        class Loader(importlib.abc.Loader):
            def create_module(self,spec):return original.create_module(spec)if hasattr(original,'create_module')else None
            def exec_module(self,module):
                original.exec_module(module);batch.attach(module);batch.attach_aliases(module)
        spec.loader=Loader();return spec


@contextlib.contextmanager
def fresh_closure_validation(observer,statistics):
    """Hash every dependency once per check, without tracing the check itself.

    Internal open/stat probes otherwise recursively hash each file again into
    the enclosing capture. The complete original dependency closure is instead
    explicitly merged; no metadata-only shortcut or historical digest is used.
    """
    original=observer._Reads.unchanged
    original_init=observer._Reads.__init__
    original_observe=observer._Reads.observe
    statistics.update(closure_checks=0,closure_dependency_file_entries=0,closure_check_seconds=0.0)
    statistics.update(inherited_owned_scratch_scopes=0,uncacheable_events={})
    def initialize(reads,*args,**kwargs):
        original_init(reads,*args,**kwargs)
        parent=observer._trace.get()
        if reads.allow_owned_scratch and parent is not None and parent.allow_owned_scratch:
            reads.scratch_roots.update(parent.scratch_roots)
            if parent.scratch_roots:statistics['inherited_owned_scratch_scopes']+=1
    def observe(reads,event,args):
        before=reads.cacheable;original_observe(reads,event,args)
        if before and not reads.cacheable:
            counts=statistics['uncacheable_events'];counts[event]=counts.get(event,0)+1
    def unchanged(reads):
        started=time.perf_counter();busy=getattr(observer._guard,'busy',False)
        observer._guard.busy=True
        try:result=original(reads)
        finally:
            observer._guard.busy=busy
            statistics['closure_checks']+=1
            statistics['closure_dependency_file_entries']+=len(reads.files)
            statistics['closure_check_seconds']+=time.perf_counter()-started
        parent=observer._trace.get()
        if parent is not reads:merge_reads(parent,reads)
        return result
    observer._Reads.unchanged=unchanged;observer._Reads.__init__=initialize;observer._Reads.observe=observe
    try:yield
    finally:
        observer._Reads.unchanged=original;observer._Reads.__init__=original_init;observer._Reads.observe=original_observe


@contextlib.contextmanager
def owner_batch_runtime(root):
    current=_active.get()
    if current is not None:yield current;return
    if os.environ.get('CAD_NATIVE_OWNER_REUSE','1')=='0':yield None;return
    import native_replay_session as observer
    if not all(hasattr(observer,n)for n in('_Reads','_trace','_capture_lock','_tracked_stat','_tracked_lstat','_environment')):
        yield None;return
    root=Path(root);batch=Batch(root,observer);finder=Finder(batch);token=_active.set(batch)
    sys.meta_path.insert(0,finder)
    pins=[dict(path=str(root/'build-cad-pipe-topology/scripts'/n),sha256=hashlib.sha256((root/'build-cad-pipe-topology/scripts'/n).read_bytes()).hexdigest())for n in ENTRIES]
    session=contextlib.nullcontext()if observer._session.get()is not None else observer.replay_session(allow_owned_scratch=True,python_replay_entries=pins)
    try:
        for name in batch.references:
            if name in sys.modules:batch.attach(sys.modules[name])
        for module in list(sys.modules.values()):
            if module is not None:batch.attach_aliases(module)
        with session,fresh_closure_validation(observer,batch.stats):yield batch
    finally:
        sys.meta_path.remove(finder);batch.close();_active.reset(token)
