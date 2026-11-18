"""Content-checked reuse of a complete deterministic native verifier artifact.

This separate application entry does not impersonate a new native replay. The
original validate-* entries remain full native controls. No CAD labels, shell
commands, pickle files or human acceptance flags are executed from the cache.
"""
import argparse,concurrent.futures,contextlib,hashlib,importlib,json,os,sys,sysconfig,time
from pathlib import Path

OWNERS={
    'rebuild_compound_member_projections':'member-projections.json',
    'rebuild_noncompound_main_extents':'main-extents.json',
}
MODE='content_checked_complete_native_artifact_reuse_v1'
SKILLS=('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline',
        'visualize-cad-pipe-topology','extract-cad-building-context')

def encode(value):return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def norm(value):return json.loads(encode(value))
def plain_file(path):
    path=Path(path)
    if path.is_symlink():return False
    return path.is_file() and '__pycache__' not in path.parts and path.suffix.lower() not in ('.pyc','.pyo')

def interpreter_image():
    if os.name=='nt':
        import ctypes
        buffer=ctypes.create_unicode_buffer(32768)
        count=ctypes.windll.kernel32.GetModuleFileNameW(None,buffer,len(buffer))
        if not count or count>=len(buffer):raise OSError('cannot bind actual Windows interpreter image')
        return Path(buffer.value).resolve()
    return Path(sys.executable).resolve()

def inventory(root):
    """Bind complete skill trees and Python/library bytes, not version strings."""
    paths=set();trees=[]
    for skill in SKILLS:
        folder=Path(root)/skill
        if not folder.is_dir():raise ValueError('complete skill tree required: '+skill)
        trees.append(folder.resolve())
    for name in ('stdlib','platstdlib','purelib','platlib'):
        value=sysconfig.get_path(name)
        if value and Path(value).is_dir():trees.append(Path(value).resolve())
    # CPython DLLs/extension modules outside Lib also affect native behavior.
    base=Path(sys.base_prefix)
    paths.update(p.resolve() for p in base.iterdir() if plain_file(p))
    if (base/'DLLs').is_dir():trees.append((base/'DLLs').resolve())
    for tree in dict.fromkeys(trees):
        paths.update(p.resolve() for p in tree.rglob('*') if plain_file(p))
    # Microsoft Store's _base_executable can be a non-readable App Execution
    # Alias. Bind the loaded executable image, plus the actual venv launcher.
    paths.add(interpreter_image())
    if Path(sys.executable).resolve()!=Path(getattr(sys,'_base_executable',sys.executable)).resolve():
        paths.add(Path(sys.executable).resolve())
    return sorted(map(str,paths))

def byte_states(paths,workers):
    # Threads only perform immutable file I/O/hashing; geometry stays isolated.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(paths,pool.map(sha,paths)))

def binding(root,owner,directory,workers):
    files=inventory(root);states=byte_states(files,workers)
    value=dict(mode=MODE,owner=owner,directory=str(Path(directory).resolve()),
        skills_root=str(Path(root).resolve()),cwd=os.getcwd(),python=sys.version,
        executable_path=sys.executable,base_executable_path=getattr(sys,'_base_executable',sys.executable),
        sys_path=list(sys.path),environment_sha256=hashlib.sha256(repr(sorted(os.environ.items())).encode('utf8')).hexdigest(),
        runtime_and_skill_files=states)
    return value,hashlib.sha256(encode(value)).hexdigest()

def closure_payload(reads):
    return norm(dict(files=reads.files,directories=reads.directories,
        probes=[[p,follow,v] for (p,follow),v in reads.probes.items()],
        empty_read_probes=sorted(getattr(reads,'empty_read_probes',set())),
        scratch_roots=sorted(reads.scratch_roots),cacheable=reads.cacheable))

def check_closure(closure,observer,workers):
    if closure.get('cacheable') is not True or not closure.get('files'):return False
    # ezdxf's default plot style tries open('', 'r') and catches ENOENT.
    # Reproduce that rejection; never reinterpret it as a directory read.
    for mode,flags in closure.get('empty_read_probes',[]):
        if mode!='r' or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):return False
        try:
            with open('',mode):pass
        except FileNotFoundError:pass
        except OSError:return False
        else:return False
    if any(os.path.lexists(p) for p in closure.get('scratch_roots',[])):return False
    files=closure['files']
    def check(item):
        path,expected=item
        try:return norm(observer._file_state(path))==expected
        except (OSError,ValueError):return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        if not all(pool.map(check,files.items())):return False
    try:
        return (all(norm(observer._dir_state(p))==v for p,v in closure['directories'].items())
            and all(norm(observer._probe_state(p,follow))==v for p,follow,v in closure['probes']))
    except (OSError,ValueError):return False

def checked_capsule(path,key,proof_path,observer,workers):
    try:
        cap=load(path);payload=cap['payload']
        if cap['payload_sha256']!=hashlib.sha256(encode(payload)).hexdigest():return None,'capsule_digest_changed'
        if payload['mode']!=MODE or payload['binding_sha256']!=key:return None,'binding_changed'
        # Re-encode with the exact original owner encoder, not the cache encoder.
        from confirm_crossview_paths import encode as native_encode
        raw=native_encode(payload['result'])
        if hashlib.sha256(raw).hexdigest()!=payload['proof_sha256'] or raw!=Path(proof_path).read_bytes():return None,'proof_bytes_changed'
        if not check_closure(payload['closure'],observer,workers):return None,'dependency_closure_changed'
        return payload,None
    except (OSError,ValueError,KeyError,TypeError):return None,'cache_missing_or_invalid'

@contextlib.contextmanager
def capture(observer):
    # Inherited verify_once owns nested traces. Merge every complete child
    # closure and scratch policy rather than treating a nested pass as opaque.
    from native_owner_batch_runtime_v2 import fresh_closure_validation
    statistics={};reads=observer._Reads(allow_owned_scratch=True);reads.capture_statistics=statistics;reads.empty_read_probes=set()
    previous_stat,previous_lstat=os.stat,os.lstat
    with fresh_closure_validation(observer,statistics),observer._capture_lock:
        original_observe=observer._Reads.observe
        def observe(current,event,args):
            if event=='open' and len(args)==3:
                name,mode,flags=args
                if name=='' and mode=='r' and type(flags)is int and not flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                    reads.empty_read_probes.add((mode,flags));return
            return original_observe(current,event,args)
        observer._Reads.observe=observe
        os.stat,os.lstat=observer._tracked_stat,observer._tracked_lstat
        token=observer._trace.set(reads)
        try:yield reads
        finally:
            observer._trace.reset(token);os.stat,os.lstat=previous_stat,previous_lstat
            observer._Reads.observe=original_observe

def run(root,owner,directory,cache_root,output,*,force_native=False,workers=16):
    if owner not in OWNERS:raise ValueError('unsupported deterministic artifact owner')
    if type(workers)is not int or not 1<=workers<=32:raise ValueError('hash workers must be1..32')
    if sys.dont_write_bytecode is not True:raise ValueError('run this isolated entry with python -B')
    started=time.perf_counter();root=Path(root).resolve();directory=Path(directory).resolve()
    output=Path(output).resolve();cache_root=Path(cache_root).resolve()
    if output.exists():raise FileExistsError(output)
    if cache_root==directory or directory in cache_root.parents or output==directory or directory in output.parents:
        raise ValueError('cache/output must not mutate the native proof directory')
    cache_root.mkdir(parents=True,exist_ok=True)
    proof_path=directory/OWNERS[owner]
    if not proof_path.is_file():raise ValueError('complete original native proof required')
    # The caller must supply the current complete sibling skills explicitly.
    expected=[str(root/x/'scripts') for x in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline')]
    for path in reversed(expected):
        if path not in sys.path:sys.path.insert(0,path)
    import native_replay_session as observer
    from native_projection_runtime_v1 import default_native_runtime
    from confirm_crossview_paths import encode as native_encode
    bound,key=binding(root,owner,directory,workers);path=cache_root/(key+'.json')
    payload,reason=(None,'forced_native_replay') if force_native else checked_capsule(path,key,proof_path,observer,workers)
    native=payload is None;stats={};stored=False
    if native:
        module=importlib.import_module(owner)
        if Path(module.__file__).resolve()!=root/'build-cad-pipe-topology/scripts'/(owner+'.py'):
            raise ValueError('native owner resolved outside supplied skills')
        with default_native_runtime(root) as runtime:
            with capture(observer) as reads:result=module.verify_output(directory)
            stats=runtime.stats if runtime else {}
        raw=native_encode(result)
        if raw!=proof_path.read_bytes():raise ValueError('complete original native artifact replay differs')
        closure=closure_payload(reads)
        # Recheck all runtime/code bytes and all transitive dependencies AFTER
        # native execution. Changed bytes are never installed into the cache.
        after,after_key=binding(root,owner,directory,workers)
        if after_key!=key:raise ValueError('runtime or skill bytes changed during native replay')
        if check_closure(closure,observer,workers):
            payload=dict(mode=MODE,binding_sha256=key,result=result,proof_sha256=hashlib.sha256(raw).hexdigest(),closure=closure)
            capsule=dict(payload=payload,payload_sha256=hashlib.sha256(encode(payload)).hexdigest())
            temporary=cache_root/(key+'.'+str(os.getpid())+'.tmp')
            try:
                with temporary.open('xb') as stream:stream.write(encode(capsule))
                os.replace(temporary,path);stored=True
            finally:
                if temporary.exists():temporary.unlink()
        else:payload=dict(result=result,proof_sha256=hashlib.sha256(raw).hexdigest(),closure=closure)
    else:
        raw=native_encode(payload['result'])
        # A hit is explicitly reuse, with one final fresh closure check before
        # exposing any artifact. A late change fails rather than using old data.
        if not check_closure(payload['closure'],observer,workers):raise ValueError('native dependencies changed during reuse')
    elapsed=time.perf_counter()-started
    report=dict(mode=MODE,status='complete_native_replay_passed' if native else 'complete_native_artifact_reused_after_current_content_checks',
        native_replay_performed=native,dependency_checked_reuse=not native,cache_stored=stored,cache_miss_reason=reason,
        elapsed_seconds=elapsed,owner=owner,native_directory=str(directory),proof_sha256=payload['proof_sha256'],
        binding_sha256=key,runtime_and_skill_files=len(bound['runtime_and_skill_files']),
        dependency_files=len(payload['closure']['files']),dependency_directories=len(payload['closure']['directories']),
        dependency_probes=len(payload['closure']['probes']),cache_file=str(path) if stored or not native else None,
        hash_workers=workers,statistics=stats,source_graphs_mutated=False,human_accepted=False,whole_goal_complete=False)
    output.mkdir(parents=True,exist_ok=False);(output/'proof.json').write_bytes(raw)
    if native and not stored:
        (output/'cache-not-stored-dependencies.json').write_bytes(encode(dict(closure=payload['closure'],capture_statistics=reads.capture_statistics)))
    (output/'execution.json').write_bytes(encode(report))
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',choices=sorted(OWNERS),required=True)
    for name in ('native-run','cache-root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--skills-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--hash-workers',type=int,default=min(16,max(1,os.cpu_count() or 1)))
    p.add_argument('--force-native',action='store_true');a=p.parse_args()
    result=run(a.skills_root,a.owner,a.native_run,a.cache_root,a.output,force_native=a.force_native,workers=a.hash_workers)
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
