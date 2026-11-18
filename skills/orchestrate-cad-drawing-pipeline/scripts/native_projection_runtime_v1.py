"""Accelerate original projection calls with fresh, input-bound process batches.

Original module files and receipts stay immutable. Only matching native kernels
and unmodified on-disk source/graph values qualify. Results are ephemeral within
this isolated job; all original owner verifiers still execute and compare their
original output receipts. Unknown or transformed scopes use the original call.
"""
import contextlib,contextvars,copy,hashlib,importlib.abc,importlib.machinery,json,os,subprocess,sys,time,threading
from collections import OrderedDict
from pathlib import Path
from native_projection_value_runtime_v1 import projected as projected_value,clear_projection_serializations
from native_source_snapshot_runtime import source_snapshot_runtime
from native_path_serialization_runtime import path_serialization_runtime
from native_json_graph_copy_acceleration import accelerated_graph_copy

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
NAMES=('reconstruct_native_block_branches.py','native_path_coverage_audit.py','native_line_path_evidence.py','source_readability.py')
_active=contextvars.ContextVar('cad_native_parallel_projection_runtime',default=None)

def worker_count():
    value=int(os.environ.get('CAD_NATIVE_WORKERS',min(22,max(1,(os.cpu_count() or 2)-2))))
    if not 1<=value<=32:raise ValueError('CAD_NATIVE_WORKERS must be1..32')
    return value

def enabled():return os.environ.get('CAD_NATIVE_PARALLEL','1')!='0'

class Runtime:
    def __init__(self,root,workers=22):
        self.root=Path(root).resolve();self.workers=workers;self.reference={n:sha(self.root/'build-cad-pipe-topology/scripts'/n)for n in NAMES}
        self.cache=OrderedDict();self.graphs=OrderedDict();self.service=None;self.patched=[];self.min_parallel_edges=16;self.stats=dict(native_batches=0,fresh_edge_projections=0,same_job_projection_reuses=0,serial_fallbacks=0,source_invalidations=0,workers=workers)
    def start(self):
        if self.service is None:
            self.service=subprocess.Popen([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('native_projection_service_v1.py')),'--workers',str(self.workers)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def context(self,doc,graph,source_hash):
        source=getattr(doc,'filename',None)
        if not source or not Path(source).is_file():return None
        if sha(source)!=source_hash:
            self.stats['source_invalidations']+=1;raise RuntimeError('native source changed during accelerated job')
        frame=sys._getframe(2);candidates=[]
        for _ in range(24):
            if frame is None:break
            for name in ('paths','inputs','local'):
                values=frame.f_locals.get(name)
                if type(values)is not dict:continue
                for key in ('graph','iso_graph','plan_graph'):
                    value=values.get(key)
                    if type(value)is dict:value=value.get('path')
                    if isinstance(value,(str,Path))and Path(value).is_file():candidates.append(str(Path(value).resolve()))
            frame=frame.f_back
        for path in dict.fromkeys(candidates):
            gh=sha(path);key=(path,gh)
            if key not in self.graphs:
                value=load(path)
                if type(value)is not dict or not isinstance(value.get('edges'),list):continue
                self.graphs[key]=value
                while len(self.graphs)>16:self.graphs.popitem(last=False)
            if self.graphs[key]==graph:return str(Path(source).resolve()),path,gh
        return None
    def attach(self,module):
        path=Path(module.__file__).resolve();root=path.parents[2]
        if any(not(root/'build-cad-pipe-topology/scripts'/n).is_file()or sha(root/'build-cad-pipe-topology/scripts'/n)!=h for n,h in self.reference.items()):return
        original=module.projected_coverage
        if getattr(original,'_parallel_native_projection',False):return
        def projected(doc,graph,eid,source_hash):
            if len(graph.get('edges',[]))<self.min_parallel_edges:
                self.stats['serial_fallbacks']+=1;return projected_value(module,doc,graph,eid,source_hash,original)
            found=self.context(doc,graph,source_hash)
            if found is None:
                self.stats['serial_fallbacks']+=1
                return projected_value(module,doc,graph,eid,source_hash,original)
            source,graph_path,gh=found;code={n:sha(root/'build-cad-pipe-topology/scripts'/n)for n in NAMES}
            if code!=self.reference:raise RuntimeError('native projection kernel changed during job')
            key=(str(root),source,source_hash,graph_path,gh)
            if key not in self.cache:
                ids=[e['edge_id']for e in graph['edges']if e.get('attribute_paths')and(e.get('source_insert_handle')or e.get('source_native_block_branch'))]
                if eid not in ids:ids.append(eid)
                self.start();request=dict(root=str(root),source=source,graph=graph_path,source_sha256=source_hash,graph_sha256=gh,edge_ids=ids)
                self.service.stdin.write(json.dumps(request,ensure_ascii=False)+'\n');self.service.stdin.flush();line=self.service.stdout.readline()
                if not line:raise RuntimeError('native projection service stopped: '+self.service.stderr.read()[-2000:])
                response=json.loads(line)
                if response['status']!='ok':
                    # Unsupported optional candidate families must not change
                    # an original call's outcome; run that exact call instead.
                    self.stats['serial_fallbacks']+=1
                    return projected_value(module,doc,graph,eid,source_hash,original)
                if sha(source)!=source_hash or sha(graph_path)!=gh:raise RuntimeError('native projection input changed during parallel batch')
                if set(response['records'])!=set(ids):raise RuntimeError('parallel projection outcome partition differs')
                self.cache[key]=response['records'];self.stats['native_batches']+=1;self.stats['fresh_edge_projections']+=len(ids)
                while len(self.cache)>64:self.cache.popitem(last=False)
            else:self.stats['same_job_projection_reuses']+=1
            if eid not in self.cache[key]or self.cache[key][eid]['status']!='ok':
                self.stats['serial_fallbacks']+=1
                return projected_value(module,doc,graph,eid,source_hash,original)
            return copy.deepcopy(self.cache[key][eid]['proof'])
        projected._parallel_native_projection=True;module.projected_coverage=projected;self.patched.append((module,original))
    def close(self):
        for module,original in reversed(self.patched):module.projected_coverage=original
        clear_projection_serializations()
        if self.service is not None:
            self.service.stdin.write('{"command":"close"}\n');self.service.stdin.flush();self.service.stdin.close();self.service.wait(timeout=60)
            if self.service.returncode:raise RuntimeError('native service did not close cleanly')

class Finder(importlib.abc.MetaPathFinder):
    def __init__(self,runtime):self.runtime=runtime
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='reconstruct_native_block_branches':return None
        spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
        if spec is None:return None
        original=spec.loader;runtime=self.runtime
        class Loader(importlib.abc.Loader):
            def create_module(self,spec):return original.create_module(spec)if hasattr(original,'create_module')else None
            def exec_module(self,module):original.exec_module(module);runtime.attach(module)
        spec.loader=Loader();return spec

@contextlib.contextmanager
def default_graph_copy():
    if os.environ.get('CAD_NATIVE_GRAPH_COPY','1')=='0' or threading.active_count()!=1:
        yield dict(enabled=False,graph_copies=0,fallbacks=0);return
    with accelerated_graph_copy()as statistics:
        statistics['enabled']=True
        yield statistics

@contextlib.contextmanager
def accelerated_native_runtime(root,workers=None):
    current=_active.get()
    if current is not None:
        yield current;return
    runtime=Runtime(root,worker_count()if workers is None else workers);token=_active.set(runtime);finder=Finder(runtime);sys.meta_path.insert(0,finder)
    existing=sys.modules.get('reconstruct_native_block_branches')
    if existing is not None:runtime.attach(existing)
    with source_snapshot_runtime()as source_stats,path_serialization_runtime(root)as path_stats,default_graph_copy()as copy_stats:
        runtime.stats['source_reads']=source_stats
        runtime.stats['path_serialization']=path_stats
        runtime.stats['graph_copy']=copy_stats
        try:yield runtime
        finally:
            sys.meta_path.remove(finder)
            try:runtime.close()
            finally:_active.reset(token)

@contextlib.contextmanager
def default_native_runtime(root):
    if not enabled():yield None;return
    with accelerated_native_runtime(root)as runtime:
        if os.environ.get('CAD_NATIVE_OWNER_BATCH_VERSION','1')=='1':
            from native_owner_batch_runtime import owner_batch_runtime
        else:
            from native_owner_batch_runtime_v2 import owner_batch_runtime
        # Start the isolated service before observing native owner dependencies;
        # its process creation is an owned runtime effect, not a source read.
        if os.environ.get('CAD_NATIVE_OWNER_REUSE','1')!='0':runtime.start()
        with owner_batch_runtime(root)as batch:
            if batch is not None:runtime.stats['owner_batch']=batch.stats
            yield runtime
