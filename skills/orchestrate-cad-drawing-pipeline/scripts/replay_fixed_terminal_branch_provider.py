"""Replay the frozen published branch source owner and actual provider."""
import argparse,hashlib,importlib,json,sys,time
from pathlib import Path
def main():
    p=argparse.ArgumentParser()
    for n in('skills-root','snapshot','native-run','viewer','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=a.skills_root.resolve();snap=json.loads(a.snapshot.read_text('utf-8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def checked():
        if any(sha(root/n)!=h for n,h in snap['files'].items()):raise ValueError('published branch owner changed')
    checked();here=Path(__file__).resolve().parent;sys.path=[x for x in sys.path if Path(x or'.').resolve()!=here]
    for n in snap['skills']:sys.path.insert(0,str(root/n/'scripts'))
    owner=importlib.import_module('reapply_anchored_terminal_branches');refresh=importlib.import_module('refresh_anchored_terminal_branches')
    if any(not Path(x.__file__).resolve().is_relative_to(root)for x in(owner,refresh)):raise ValueError('published owner escaped frozen root')
    from native_projection_runtime_v1 import default_native_runtime
    from confirm_crossview_paths import encode
    start=time.perf_counter()
    with default_native_runtime(root):proof=owner.verify_output(a.native_run);view=refresh.verify_from_native_result(a.viewer,proof)
    if view.get('artifact_replay')!='passed':raise ValueError('original published branch adoption differs')
    checked();provider=a.viewer/'anchored-terminal-branch-refresh/provider-inventory.json';a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'parent-proof.json').write_bytes(encode(proof));(a.output/'provider.json').write_bytes(provider.read_bytes())
    (a.output/'execution.json').write_bytes(encode(dict(owner='reapply_anchored_terminal_branches',snapshot_sha256=sha(a.snapshot),native_proof_sha256=sha(a.native_run/'anchored-terminal-branches.json'),provider_sha256=sha(provider),complete_published_parent_independently_replayed=True,elapsed_seconds=time.perf_counter()-start,human_accepted=False)))
if __name__=='__main__':main()
