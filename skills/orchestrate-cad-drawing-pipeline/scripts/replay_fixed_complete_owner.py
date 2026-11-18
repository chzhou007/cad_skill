"""Replay a declared original owner and compare every canonical result output."""
import argparse,hashlib,importlib,json,re,sys,time
from pathlib import Path
def main():
    p=argparse.ArgumentParser()
    for key in('skills-root','snapshot','native-run','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--owner',required=True);p.add_argument('--result-files',required=True);a=p.parse_args()
    root=a.skills_root.resolve();snapshot=json.loads(a.snapshot.read_text(encoding='utf8'));files=json.loads(a.result_files);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if not re.fullmatch('[a-z][a-z0-9_]*',a.owner)or not files or any(Path(n).name!=n or not n.endswith('.json')for n in files):raise ValueError('explicit original module and plain canonical output names required')
    before={n:sha(a.native_run/n)for n in files}
    def checked():
        if any(sha(root/n)!=h for n,h in snapshot['files'].items())or any(sha(a.native_run/n)!=h for n,h in before.items()):raise ValueError('original runtime or result changed')
    checked();own=Path(__file__).resolve().parent;sys.path=[v for v in sys.path if Path(v or'.').resolve()!=own]
    for name in snapshot['skills']:sys.path.insert(0,str(root/name/'scripts'))
    module=importlib.import_module(a.owner);source=Path(module.__file__).resolve()
    if not source.is_relative_to(root)or source.relative_to(root).as_posix()not in snapshot['files']:raise ValueError('owner escaped pinned runtime')
    from confirm_crossview_paths import encode
    started=time.perf_counter();values=module.verify_output(a.native_run)
    if len(files)==1:values=[values]
    if not isinstance(values,(tuple,list))or len(values)!=len(files):raise ValueError('original owner result arity differs')
    for name,value in zip(files,values):
        if encode(value)!=(a.native_run/name).read_bytes():raise ValueError('canonical original owner output differs: '+name)
    checked();a.output.mkdir(parents=True,exist_ok=False)
    for name in files:(a.output/name).write_bytes((a.native_run/name).read_bytes())
    (a.output/'execution.json').write_text(json.dumps(dict(owner=a.owner,files=before,snapshot_sha256=sha(a.snapshot),elapsed_seconds=time.perf_counter()-started,human_accepted=False),indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
