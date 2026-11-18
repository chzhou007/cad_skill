"""Observe the exact shipped Node attribute reader as a bounded read-only call.

Unknown reader code, module versions or Node startup options keep the original
untracked subprocess path. No geometry verification or attribute result is
cached here; the inherited native observer receives every input byte dependency.
"""
import contextlib,functools,hashlib,importlib,json,os,re,shutil,threading
from pathlib import Path
import native_replay_session as observer

READERS=('refresh_attribute_templates','refresh_noncompound_main_attributes')
IMPORTS=re.compile(r"(?:import|export)\s+[^;]+?\sfrom\s*['\"]([^'\"]+)['\"]")


def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def function_fingerprint(fn):
    try:c=fn.__code__
    except AttributeError:return None
    value=dict(bytecode=c.co_code.hex(),constants=c.co_consts,names=c.co_names,
               variables=c.co_varnames,args=c.co_argcount,kwonly=c.co_kwonlyargcount,
               flags=c.co_flags,free=c.co_freevars,defaults=fn.__defaults__)
    try:return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
    except (TypeError,ValueError):return None


class Runtime:
    def __init__(self,root,policy):
        self.root=Path(root).resolve();self.policy_path=Path(policy).resolve()
        self.policy=json.loads(self.policy_path.read_text('utf-8'))
        if self.policy.get('mode')!='shipped_pure_attribute_reader_inputs_v1':raise ValueError('unknown attribute reader policy')
        self.policy_hash=sha(self.policy_path);self.node=shutil.which('node');self.patched=[]
        self.stats=dict(tracked_node_reads=0,original_fallbacks=0,input_files_checked=0)

    def snapshot(self,bundle,fn):
        if threading.current_thread()is not threading.main_thread()or any(os.environ.get(k)for k in('NODE_OPTIONS','NODE_PATH')):
            return None
        if not self.node or shutil.which('node')!=self.node or function_fingerprint(fn)not in self.policy['reader_function_fingerprints']:
            return None
        if sha(self.policy_path)!=self.policy_hash:raise ValueError('trusted attribute reader policy changed')
        # These reads are deliberately inside the original native trace.
        files={str(self.policy_path):self.policy_hash,str(Path(__file__)):sha(__file__)}
        node=Path(self.node);files[str(node)]=sha(node)
        for dll in node.parent.glob('*.dll'):files[str(dll)]=sha(dll)
        base=Path(bundle)/'public';pending=['edge-attributes.js'];seen=set()
        while pending:
            name=pending.pop()
            if name in seen:continue
            if '/'in name or '\\'in name or not name.endswith('.js'):return None
            seen.add(name);path=base/name
            try:raw=path.read_bytes()
            except OSError:return None
            digest=hashlib.sha256(raw).hexdigest()
            if digest not in self.policy['module_sha256'].get(name,[]):return None
            files[str(path)]=digest
            for ref in IMPORTS.findall(raw.decode('utf-8')):
                if not ref.startswith('./')or '/'in ref[2:]or '\\'in ref:return None
                pending.append(ref[2:])
        for name in('graph.json','manifest.json'):
            p=base/'data'/name;files[str(p)]=sha(p)
        # Node consults package.json for .js module type. Negative probes are
        # retained too, so adding a package later invalidates original reuse.
        for folder in(base,*base.parents):
            p=folder/'package.json'
            if p.exists():files[str(p)]=sha(p)
        return files

    def call(self,original,bundle):
        if observer._trace.get()is None:return original(bundle)
        before=self.snapshot(bundle,original)
        if before is None:
            self.stats['original_fallbacks']+=1
            return original(bundle)
        # Only this exact fingerprinted pure function is outside the observer.
        # Its twelve shipped relative modules, graph, context, engine and Node
        # package configuration were read above and are checked again below.
        token=observer._trace.set(None)
        try:result=original(bundle)
        finally:observer._trace.reset(token)
        after=self.snapshot(bundle,original)
        if after!=before:raise ValueError('attribute reader input changed during Node execution')
        self.stats['tracked_node_reads']+=1;self.stats['input_files_checked']+=len(before)
        return result

    def attach(self):
        for name in READERS:
            module=importlib.import_module(name)
            expected=self.root/'visualize-cad-pipe-topology/scripts'/(name+'.py')
            if Path(module.__file__).resolve()!=expected:raise ValueError('attribute reader resolved outside supplied skills')
            original=module.effective_attributes
            @functools.wraps(original)
            def wrapper(bundle,_original=original):return self.call(_original,bundle)
            module.effective_attributes=wrapper;self.patched.append((module,original,wrapper))

    def close(self):
        for module,original,wrapper in reversed(self.patched):
            if module.effective_attributes is wrapper:module.effective_attributes=original


@contextlib.contextmanager
def attribute_read_runtime(root,policy=None):
    root=Path(root).resolve()
    if threading.active_count()!=1:
        yield None;return
    path=Path(policy)if policy else root/'orchestrate-cad-drawing-pipeline/assets/pure-attribute-reader-policy.json'
    runtime=Runtime(root,path)
    try:
        runtime.attach();yield runtime
    finally:runtime.close()
