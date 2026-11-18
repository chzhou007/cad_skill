"""Reuse one freshly completed native verification inside a bounded process batch.

No persisted trust flags or preloaded receipts. Record actual file/directory
reads during the first verifier call; validate that closure before each reuse.
Untracked external effects disable reuse. Outside the context every call replays.
"""
import contextlib,contextvars,hashlib,os,stat,sys,threading

_session=contextvars.ContextVar('cad_native_replay_session',default=None)
_trace=contextvars.ContextVar('cad_native_replay_trace',default=None)
_guard=threading.local()
_capture_lock=threading.RLock()
_native_stat=os.stat
_native_lstat=os.lstat


def _file_state(path):
    real=os.path.normcase(os.path.realpath(path))
    try:
        info=os.stat(path)
    except FileNotFoundError:return ('missing',real)
    if not stat.S_ISREG(info.st_mode):return ('unsupported',real)
    with open(path,'rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return ('file',real,digest)


def _dir_state(path):
    try:return ('directory',os.path.normcase(os.path.realpath(path)),tuple(sorted(os.listdir(path))))
    except FileNotFoundError:return ('missing_directory',os.path.normcase(os.path.realpath(path)))


def _environment():
    # Values remain in memory as a digest; no environment values are exported.
    return (os.getcwd(),hashlib.sha256(repr(sorted(os.environ.items())).encode('utf8')).hexdigest())


class _Reads:
    def __init__(self):self.files={};self.directories={};self.probes={};self.cacheable=True
    def observe(self,event,args):
        if event in ('subprocess.Popen','os.system','socket.connect','urllib.Request'):
            self.cacheable=False;return
        if event=='open':
            name,mode,flags=args
            if isinstance(mode,str) and any(c in mode for c in 'wax+'):
                self.cacheable=False
                return
            if mode is None and isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR):
                self.cacheable=False;return
            if not isinstance(name,(str,bytes,os.PathLike)):self.cacheable=False;return
            path=os.path.normcase(os.path.abspath(os.fsdecode(name)));value=_file_state(path)
            if value[0]=='unsupported':self.cacheable=False
            if path in self.files and self.files[path]!=value:self.cacheable=False
            else:self.files[path]=value
        elif event in ('os.listdir','os.scandir'):
            name=args[0] if args else '.'
            if not isinstance(name,(str,bytes,os.PathLike)):self.cacheable=False;return
            path=os.path.normcase(os.path.abspath(os.fsdecode(name)));value=_dir_state(path)
            if path in self.directories and self.directories[path]!=value:self.cacheable=False
            else:self.directories[path]=value
    def unchanged(self):
        return (self.cacheable and bool(self.files) and all(_file_state(p)==v for p,v in self.files.items())
            and all(_dir_state(p)==v for p,v in self.directories.items())
            and all(_probe_state(p,follow)==v for (p,follow),v in self.probes.items()))


def _probe_state(path,follow):
    try:
        info=_native_stat(path,follow_symlinks=follow)
        return ('metadata',info.st_mode,info.st_size,info.st_mtime_ns,info.st_ino)
    except FileNotFoundError:return ('missing',)


def _observe_probe(path,follow,dir_fd):
    trace=_trace.get()
    if trace is None or getattr(_guard,'busy',False):return
    if dir_fd is not None or not isinstance(path,(str,bytes,os.PathLike)):trace.cacheable=False;return
    _guard.busy=True
    try:
        key=(os.path.normcase(os.path.abspath(os.fsdecode(path))),follow);value=_probe_state(*key)
        if key in trace.probes and trace.probes[key]!=value:trace.cacheable=False
        else:trace.probes[key]=value
    except (OSError,ValueError,TypeError):trace.cacheable=False
    finally:_guard.busy=False


def _tracked_stat(path,*,dir_fd=None,follow_symlinks=True):
    _observe_probe(path,follow_symlinks,dir_fd)
    return _native_stat(path,dir_fd=dir_fd,follow_symlinks=follow_symlinks)


def _tracked_lstat(path,*,dir_fd=None):
    _observe_probe(path,False,dir_fd)
    return _native_lstat(path,dir_fd=dir_fd)


def _audit(event,args):
    trace=_trace.get()
    if trace is None or getattr(_guard,'busy',False):return
    _guard.busy=True
    try:trace.observe(event,args)
    except (OSError,ValueError,TypeError):trace.cacheable=False
    finally:_guard.busy=False


sys.addaudithook(_audit)


class Session:
    def __init__(self):self._results={};self.hits=0;self.replays=0;self.invalidations=0
    def statistics(self):return dict(native_replays=self.replays,same_batch_reuses=self.hits,invalidations=self.invalidations,
        dependency_files=sum(len(v[1].files) for v in self._results.values()),persistent_trust=False)


@contextlib.contextmanager
def replay_session():
    session=Session();token=_session.set(session)
    try:yield session
    finally:_session.reset(token);session._results.clear()


def verify_once(directory,verifier):
    session=_session.get()
    if session is None:return verifier(directory)
    key=(os.path.normcase(os.path.abspath(os.fspath(directory))),id(verifier));cached=session._results.get(key)
    if cached:
        result,reads,environment=cached
        if _environment()==environment and reads.unchanged():
            session.hits+=1
            # Consumers may append to ancestry lists; never share mutable results.
            import copy
            return copy.deepcopy(result)
        session.invalidations+=1;del session._results[key]
    reads=_Reads();environment=_environment()
    with _capture_lock:
        previous_stat,previous_lstat=os.stat,os.lstat;os.stat,os.lstat=_tracked_stat,_tracked_lstat
        token=_trace.set(reads)
        try:result=verifier(directory)
        finally:_trace.reset(token);os.stat,os.lstat=previous_stat,previous_lstat
    session.replays+=1
    if _environment()==environment and reads.unchanged():
        import copy
        session._results[key]=(copy.deepcopy(result),reads,environment)
    return result
