"""Independently replay the unchanged published 170-feature attribute owner."""
import argparse,hashlib,importlib,json,sys,time
from pathlib import Path
def main():
    p=argparse.ArgumentParser()
    for n in('skills-root','snapshot','native-run','viewer','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=a.skills_root.resolve();snap=json.loads(a.snapshot.read_text('utf-8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def checked():
        if any(sha(root/n)!=h for n,h in snap['files'].items()):raise ValueError('original published attribute owner changed')
    checked();here=Path(__file__).resolve().parent;sys.path=[v for v in sys.path if Path(v or'.').resolve()!=here]
    for n in snap['skills']:sys.path.insert(0,str(root/n/'scripts'))
    owner=importlib.import_module('reapply_complementary_plan_attributes');refresh=importlib.import_module('refresh_complementary_plan_attributes')
    if any(not Path(m.__file__).resolve().is_relative_to(root)for m in(owner,refresh)):raise ValueError('published parent escaped frozen root')
    from native_projection_runtime_v1 import default_native_runtime
    from confirm_crossview_paths import encode
    started=time.perf_counter()
    with default_native_runtime(root):
        values=owner.verify_output(a.native_run);checked();view=refresh.verify_from_native_result(a.viewer,values)
    provider=a.viewer/'complementary-native-attribute-refresh/provider-inventory.json'
    if view.get('artifact_replay')!='passed'or values[0].get('all_historical_main_roles_reapplied')is not True:raise ValueError('published source or adoption failed')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'parent-proof.json').write_bytes(encode(values[0]));(a.output/'provider.json').write_bytes(provider.read_bytes())
    (a.output/'execution.json').write_bytes(encode(dict(owner='reapply_complementary_plan_attributes',snapshot_sha256=sha(a.snapshot),native_proof_sha256=sha(a.native_run/'complementary-plan-attributes.json'),provider_sha256=sha(provider),complete_published_parent_independently_replayed=True,elapsed_seconds=time.perf_counter()-started,human_accepted=False)))
if __name__=='__main__':main()
