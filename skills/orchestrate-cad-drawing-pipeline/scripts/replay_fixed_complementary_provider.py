"""Replay the original corrected complementary-chain owner in its frozen tree."""
import argparse,hashlib,importlib,json,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for name in('skills-root','snapshot','native-run','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=a.skills_root.resolve();snap=json.loads(a.snapshot.read_text(encoding='utf-8'))
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest();names=['complementary-chains.json','provider-inventory.json'];before={n:sha(a.native_run/n)for n in names}
    def checked():
        if any(sha(root/n)!=h for n,h in snap['files'].items())or any(sha(a.native_run/n)!=h for n,h in before.items()):raise ValueError('frozen corrected complementary owner or source result changed')
    checked();here=Path(__file__).resolve().parent;sys.path=[v for v in sys.path if Path(v or'.').resolve()!=here]
    for n in snap['skills']:sys.path.insert(0,str(root/n/'scripts'))
    owner=importlib.import_module('rebuild_complementary_anchor_chains')
    if not Path(owner.__file__).resolve().is_relative_to(root):raise ValueError('complementary owner escaped frozen native runtime')
    from confirm_crossview_paths import encode
    from native_projection_runtime_v1 import default_native_runtime
    started=time.perf_counter()
    with default_native_runtime(root):values=owner.verify_output(a.native_run)
    for name,value in zip(names,values):
        if encode(value)!=(a.native_run/name).read_bytes():raise ValueError('corrected complete parent replay differs')
    if values[0].get('all_current_plans_known_exploded_ball_population_screened')is not True:raise ValueError('obsolete zero-profile native parent is not adoptable')
    checked();a.output.mkdir(parents=True,exist_ok=False)
    for n in names:(a.output/n).write_bytes((a.native_run/n).read_bytes())
    (a.output/'execution.json').write_bytes(encode(dict(owner='rebuild_complementary_anchor_chains',snapshot_sha256=sha(a.snapshot),files=before,
        elapsed_seconds=time.perf_counter()-started,complete_corrected_parent_replayed=True,human_accepted=False)))

if __name__=='__main__':main()
