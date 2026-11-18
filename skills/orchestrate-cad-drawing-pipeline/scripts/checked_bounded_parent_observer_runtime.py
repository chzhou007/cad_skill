"""Compose one fixed checked-child closure into its original native caller.

Do not ignore pipe opens in general. Only the unchanged, fixed-owner bounded
parent application may cross this boundary. Its original checks/child execute,
complete proof bytes and capsule integrity are verified, the child's entire
current dependency closure is merged, and job-local reuse rechecks it afresh.
The enclosing engine still binds complete Python/library bytes and environment.
"""
import contextlib,copy,hashlib,importlib,json,sys
from pathlib import Path
import reuse_verified_native_artifact as engine
from native_owner_batch_runtime import merge_reads

OWNER='rebuild_bounded_main_complete_extents'
MODULE='checked_bounded_attribute_parent'

def _tuple(value):return tuple(_tuple(x)for x in value)if isinstance(value,list)else value

def child_closure(report,result,proof,spec,observer,workers=16):
    """An execution receipt alone never establishes a reusable child."""
    from confirm_crossview_paths import encode as native_encode
    if (report.get('owner')!=OWNER or spec.get('owner')!=OWNER or report.get('mode')!=engine.MODE
        or report.get('human_accepted')is not False or report.get('proof_sha256')!=spec['proof_sha256']
        or type(report.get('native_replay_performed'))is not bool or type(report.get('dependency_checked_reuse'))is not bool
        or report.get('source_graphs_mutated')is not False or report.get('native_replay_performed')==report.get('dependency_checked_reuse')):raise ValueError('checked child owner, mode or execution state differs')
    raw=native_encode(result)
    if raw!=Path(proof).read_bytes()or hashlib.sha256(raw).hexdigest()!=spec['proof_sha256']:raise ValueError('checked child complete proof differs')
    cache=report.get('cache_file')
    if not cache:return None
    p=Path(cache).resolve();root=Path(spec['cache_root']).resolve()
    if p.parent!=root or p.name!=report['binding_sha256']+'.json':raise ValueError('checked child capsule outside fixed cache domain')
    capsule=engine.load(p);payload=capsule['payload']
    if (capsule['payload_sha256']!=hashlib.sha256(engine.encode(payload)).hexdigest()or payload['mode']!=engine.MODE
        or payload['binding_sha256']!=report['binding_sha256']or payload['proof_sha256']!=spec['proof_sha256']
        or native_encode(payload['result'])!=raw):raise ValueError('checked child capsule changed')
    closure=payload['closure']
    if not engine.check_closure(closure,observer,workers):return None
    reads=observer._Reads(allow_owned_scratch=True)
    reads.files={k:_tuple(v)for k,v in closure['files'].items()};reads.directories={k:_tuple(v)for k,v in closure['directories'].items()};reads.probes={(p,f):_tuple(v)for p,f,v in closure['probes']};reads.scratch_roots=set(closure['scratch_roots']);reads.cacheable=True;reads.empty_read_probes=set(map(tuple,closure.get('empty_read_probes',[])))
    # Bind the capsule itself too. Native inputs remain in the merged closure;
    # replacing a child capsule cannot silently retain an old enclosing hit.
    reads.files[str(p).lower()if sys.platform=='win32'else str(p)]=observer._file_state(p)
    return reads

class Runtime:
    def __init__(self,root,observer):
        self.root=Path(root).resolve();self.observer=observer;self.module=importlib.import_module(MODULE);self.original=self.module.apply;self.memo={};self.aliases=[]
        if Path(self.module.__file__).resolve()!=self.root/'orchestrate-cad-drawing-pipeline/scripts'/(MODULE+'.py')or self.original.__module__!=MODULE or Path(self.original.__code__.co_filename).resolve()!=Path(self.module.__file__).resolve():raise ValueError('fixed bounded parent owner resolved outside original skills')
        self.original_sha=engine.sha(self.module.__file__);self.stats=dict(original_child_executions=0,content_checked_job_reuses=0,uncacheable_children=0,child_dependency_files=0,generic_subprocesses_exempted=0)
    def call(self,spec,current_root):
        obs=self.observer;outer=obs._trace.get()
        if outer is None:return self.original(spec,current_root)
        if engine.sha(self.module.__file__)!=self.original_sha:raise ValueError('original checked parent implementation changed')
        # Both original check passes run under the enclosing capture. They bind
        # the complete immutable child skill tree, inherited algorithms, fixed
        # environment policy, current root and exact original complete proof.
        _,proof,_=self.module.check(spec,current_root)
        Path(__file__).read_bytes()
        environment=obs._environment();key=hashlib.sha256(engine.encode([spec,str(Path(current_root).resolve()),environment])).hexdigest();memo=self.memo.get(key)
        if memo is not None:
            value,reads,report=memo
            if reads.unchanged():
                merge_reads(outer,reads)
                if hasattr(outer,'empty_read_probes'):outer.empty_read_probes.update(reads.empty_read_probes)
                self.module.check(spec,current_root);self.module.LAST_APPLICATION.clear();self.module.LAST_APPLICATION.update(copy.deepcopy(report));self.stats['content_checked_job_reuses']+=1
                return copy.deepcopy(value)
            del self.memo[key]
        # This is the exact original application, including its own child
        # native/content checks, proof equality and final inherited-code check.
        token=obs._trace.set(None)
        try:value=self.original(spec,current_root)
        finally:obs._trace.reset(token)
        self.stats['original_child_executions']+=1;report=copy.deepcopy(self.module.LAST_APPLICATION)
        reads=child_closure(report,value[0],proof,spec,obs)
        self.module.check(spec,current_root)
        if obs._environment()!=environment:raise ValueError('checked parent environment changed')
        if reads is None:
            outer.cacheable=False;self.stats['uncacheable_children']+=1
        else:
            merge_reads(outer,reads)
            if hasattr(outer,'empty_read_probes'):outer.empty_read_probes.update(reads.empty_read_probes)
            self.memo[key]=(copy.deepcopy(value),reads,report);self.stats['child_dependency_files']+=len(reads.files)
        return value
    def attach(self):
        wrapper=self.call
        for module in list(sys.modules.values()):
            namespace=getattr(module,'__dict__',None)
            if not namespace:continue
            for key,value in list(namespace.items()):
                if value is self.original:namespace[key]=wrapper;self.aliases.append((namespace,key,self.original,wrapper))
    def close(self):
        for namespace,key,original,wrapper in reversed(self.aliases):
            if namespace.get(key)is wrapper:namespace[key]=original
        self.aliases.clear();self.memo.clear()

@contextlib.contextmanager
def bounded_parent_runtime(root,observer):
    runtime=Runtime(root,observer);runtime.attach()
    try:yield runtime
    finally:runtime.close()
