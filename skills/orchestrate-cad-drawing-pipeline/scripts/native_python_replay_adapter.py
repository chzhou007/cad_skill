"""Run only explicitly hash-bound legacy Python replay producers in-process.

This keeps actual child input/code reads visible to the dependency observer.
Unknown commands retain ordinary subprocess behavior and disable cache reuse.
The caller still compares every reconstructed native artifact with its receipt.
"""
import contextlib,hashlib,io,os,runpy,subprocess,sys
from pathlib import Path


def pin_entries(entries):
    result={}
    for item in entries:
        if not isinstance(item,dict) or set(item)!={'path','sha256'}:raise ValueError('exact native Python entry pin required')
        path=Path(item['path']).resolve()
        if path.suffix!='.py' or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('native Python replay entry changed')
        key=os.path.normcase(str(path))
        if key in result:raise ValueError('duplicate native Python replay entry')
        result[key]=dict(path=str(path),sha256=item['sha256'])
    return result


@contextlib.contextmanager
def adapt(session,active):
    original=subprocess.run
    def run(command,*args,**kwargs):
        if (not active() or args or not isinstance(command,(list,tuple)) or len(command)<4
            or any(not isinstance(x,str) for x in command) or command[:3]!=[sys.executable,'-X','utf8']
            or set(kwargs)-{'check','stdout'} or kwargs.get('check') is not True or kwargs.get('stdout')!=subprocess.DEVNULL):
            return original(command,*args,**kwargs)
        key=os.path.normcase(str(Path(command[3]).resolve()));spec=session.python_replay_entries.get(key)
        if spec is None:return original(command,*args,**kwargs)
        if hashlib.sha256(Path(spec['path']).read_bytes()).hexdigest()!=spec['sha256']:raise ValueError('authorized native replay producer changed')
        previous_argv=list(sys.argv);previous_path=list(sys.path);session.inprocess_children+=1
        try:
            sys.argv=[spec['path'],*command[4:]];sys.path.insert(0,str(Path(spec['path']).parent))
            with contextlib.redirect_stdout(io.StringIO()):
                try:runpy.run_path(spec['path'],run_name='__main__')
                except SystemExit as exc:
                    if exc.code not in (None,0):raise subprocess.CalledProcessError(exc.code,command) from exc
            return subprocess.CompletedProcess(command,0)
        finally:sys.argv=previous_argv;sys.path[:]=previous_path
    subprocess.run=run
    try:yield
    finally:subprocess.run=original
