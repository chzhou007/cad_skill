"""Extend the original bounded Node bridge to exact current reader families.

No graph values are cached. Unknown code, imports, engines or startup settings
retain the original untracked call. Original production readers stay unchanged.
"""
import contextlib,functools,hashlib,importlib,json,os,re,shutil,sys,threading,types
from pathlib import Path
import native_replay_session as observer
from native_attribute_read_runtime import Runtime as OriginalRuntime,sha,function_fingerprint,IMPORTS

MODE='exact_current_attribute_reader_inputs_v1'
SIDE_IMPORT=re.compile(r"\bimport\s*['\"]([^'\"]+)['\"]")
UNSUPPORTED=re.compile(r'\bimport\s*\(|\brequire\s*\(|\bfetch\s*\(|\b(?:process|window|document)\s*\.|\beval\s*\(|\bnew\s+Function\b')

def command(original,bundle):
    """Construct only argv in a private function; dummy values never escape."""
    calls=[]
    def record(argv,**kwargs):calls.append(list(argv));return types.SimpleNamespace(returncode=0,stdout='[]',stderr='')
    proxy=types.SimpleNamespace(run=record,CREATE_NO_WINDOW=getattr(__import__('subprocess'),'CREATE_NO_WINDOW',0))
    fn=types.FunctionType(original.__code__,dict(original.__globals__,subprocess=proxy),original.__name__,original.__defaults__,original.__closure__);fn.__kwdefaults__=original.__kwdefaults__
    fn(bundle)
    if len(calls)!=1:raise ValueError('one readonly attribute command required')
    return calls[0]

def command_inputs(argv,bundle):
    base=(Path(bundle)/'public').resolve()
    if len(argv)<5 or Path(str(argv[0])).name.lower()not in('node','node.exe')or argv[1:3]!=['--input-type=module','-e']or not isinstance(argv[3],str):raise ValueError('unsupported readonly command')
    script=argv[3];args=argv[4:];graph=base/'data/graph.json';manifest=base/'data/manifest.json'
    if len(args)==3:
        entry=Path(args[0]).resolve()
        if [Path(p).resolve()for p in args[1:]]!=[graph,manifest]:raise ValueError('readonly command data inputs differ')
    elif len(args)==2:
        if Path(args[0]).resolve()!=base.parent or not re.fullmatch(r'[A-Za-z0-9_.-]+\.js',str(args[1])):raise ValueError('readonly command root or entry differs')
        entry=base/args[1]
    elif len(args)==1:
        names=set(re.findall(r'/public/([A-Za-z0-9_.-]+\.js)',script))
        if Path(args[0]).resolve()!=base.parent or len(names)!=1:raise ValueError('embedded entry or root differs')
        entry=base/next(iter(names))
    else:raise ValueError('unsupported readonly argument layout')
    if entry.parent!=base or not entry.name.endswith('.js'):raise ValueError('entry leaves local public folder')
    return entry,graph,manifest,hashlib.sha256(script.encode('utf8')).hexdigest()

def module_closure(entry):
    entry=Path(entry);base=entry.parent;pending=[entry.name];result={}
    while pending:
        name=pending.pop()
        if name in result:continue
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.js',name):raise ValueError('attribute import leaves local module scope')
        p=base/name
        if p.is_symlink():raise ValueError('attribute module symlink is outside this mode')
        raw=p.read_bytes();text=raw.decode('utf8')
        if UNSUPPORTED.search(text):raise ValueError('attribute module has unsupported runtime effects')
        result[name]=hashlib.sha256(raw).hexdigest()
        for ref in IMPORTS.findall(text)+SIDE_IMPORT.findall(text):
            if not re.fullmatch(r'\./[A-Za-z0-9_.-]+\.js',ref):raise ValueError('external or nonliteral attribute import')
            pending.append(ref[2:])
    return result

class Runtime(OriginalRuntime):
    def __init__(self,root,policy):
        self.root=Path(root).resolve();self.policy_path=Path(policy).resolve();self.policy=json.loads(self.policy_path.read_text(encoding='utf8'))
        if self.policy.get('mode')!=MODE:raise ValueError('unknown current attribute reader policy')
        self.policy_hash=sha(self.policy_path);self.node=shutil.which('node');self.patched=[];self.originals={};self.stats=dict(tracked_node_reads=0,original_fallbacks=0,input_files_checked=0,fallback_reasons={},unknown_module_versions={})

    def held(self,reason):
        counts=self.stats['fallback_reasons'];counts[reason]=counts.get(reason,0)+1
        return None

    def snapshot(self,bundle,fn):
        if threading.current_thread()is not threading.main_thread()or any(os.environ.get(k)for k in('NODE_OPTIONS','NODE_PATH')):return self.held('thread_or_startup_options')
        row=self.originals.get(fn)
        if row is None or function_fingerprint(fn)!=row['function_fingerprint']:return self.held('function_identity_or_fingerprint')
        expected=self.root/'visualize-cad-pipe-topology/scripts'/(row['module']+'.py')
        if Path(fn.__code__.co_filename).resolve()!=expected or sha(expected)!=row['module_sha256']:return self.held('module_source_binding')
        if not self.node or shutil.which('node')!=self.node:return self.held('engine_resolution')
        if sha(self.policy_path)!=self.policy_hash:raise ValueError('trusted current reader policy changed')
        try:
            argv=command(fn,bundle);entry,graph,manifest,script=command_inputs(argv,bundle)
            if script not in row['cli_script_sha256']:return self.held('command_script_fingerprint')
            modules=module_closure(entry)
        except (ValueError,OSError)as exc:return self.held('unsupported_command_or_module:'+str(exc))
        unknown={name:h for name,h in modules.items()if h not in self.policy['module_sha256'].get(name,[])}
        if unknown:
            for name,h in unknown.items():self.stats['unknown_module_versions'].setdefault(name,[]).append(h)
            return self.held('unqualified_module_version')
        files={str(self.policy_path):self.policy_hash,str(Path(__file__)):sha(__file__),str(expected):row['module_sha256']}
        # The inherited call() and fingerprint/import helpers are input code too.
        import native_attribute_read_runtime as prior
        files[str(Path(prior.__file__))]=sha(prior.__file__)
        node=Path(self.node);files[str(node)]=sha(node)
        for dll in node.parent.glob('*.dll'):files[str(dll)]=sha(dll)
        for name,h in modules.items():files[str(entry.parent/name)]=h
        for p in [graph,manifest]:files[str(p)]=sha(p)
        app=entry.parent/'app.js'
        if app.exists():files[str(app)]=sha(app)
        for folder in(entry.parent,*entry.parent.parents):
            p=folder/'package.json'
            if p.exists():files[str(p)]=sha(p)
        return files

    def attach(self):
        replacements={}
        for row in self.policy['readers']:
            module=importlib.import_module(row['module']);expected=self.root/'visualize-cad-pipe-topology/scripts'/(row['module']+'.py')
            if Path(module.__file__).resolve()!=expected or sha(expected)!=row['module_sha256']:raise ValueError('reader module version differs from trusted policy')
            fn=getattr(module,row['function'])
            if function_fingerprint(fn)!=row['function_fingerprint']:raise ValueError('reader function version differs from trusted policy')
            self.originals[fn]=row
            @functools.wraps(fn)
            def wrapper(bundle,_original=fn):return self.call(_original,bundle)
            replacements[fn]=wrapper
        # Import aliases already held by native owners must use the same bridge.
        for module in list(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if not filename:continue
            try:inside=Path(filename).resolve().is_relative_to(self.root)
            except (ValueError,OSError):continue
            if not inside:continue
            for name,value in list(vars(module).items()):
                if isinstance(value,types.FunctionType)and value in replacements:
                    wrapper=replacements[value];setattr(module,name,wrapper);self.patched.append((module,name,value,wrapper))

    def close(self):
        # A module imported during the verifier may retain a wrapped export.
        # Restore those late aliases too, without overwriting foreign changes.
        reverse={wrapper:original for _,_,original,wrapper in self.patched}
        for module in list(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if not filename:continue
            try:inside=Path(filename).resolve().is_relative_to(self.root)
            except (ValueError,OSError):continue
            if inside:
                for name,value in list(vars(module).items()):
                    if isinstance(value,types.FunctionType)and value in reverse:setattr(module,name,reverse[value])
        for module,name,original,wrapper in reversed(self.patched):
            if getattr(module,name,None)is wrapper:setattr(module,name,original)

@contextlib.contextmanager
def current_attribute_read_runtime(root,policy):
    if threading.active_count()!=1:yield None;return
    runtime=Runtime(root,policy)
    try:runtime.attach();yield runtime
    finally:runtime.close()
