"""Requalify a complete original two-arm runtime before extending its provider."""
import argparse,hashlib,importlib,json,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for name in('skills-root','snapshot','native-run','provider','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=a.skills_root.resolve();snapshot=json.loads(a.snapshot.read_text(encoding='utf-8'))
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    expected_sha=sha(a.provider);started=time.perf_counter()
    def checked():
        if any(sha(root/n)!=h for n,h in snapshot['files'].items())or sha(a.provider)!=expected_sha:raise ValueError('original complete two-arm runtime or adopted provider changed')
    checked();here=Path(__file__).resolve().parent;sys.path=[v for v in sys.path if Path(v or'.').resolve()!=here]
    for name in snapshot['skills']:sys.path.insert(0,str(root/name/'scripts'))
    module=importlib.import_module('rebuild_current_two_arm_circle_routes')
    if not Path(module.__file__).resolve().is_relative_to(root):raise ValueError('two-arm provider escaped frozen native runtime')
    from native_projection_runtime_v1 import default_native_runtime
    from confirm_crossview_paths import encode
    with default_native_runtime(root):proof,provider,local,outputs=module.verify_output(a.native_run)
    if json.loads(encode(provider))!=json.loads(a.provider.read_text(encoding='utf-8')):raise ValueError('current adopted provider differs from original complete native replay')
    checked();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'provider-inventory.json').write_bytes(a.provider.read_bytes())
    (a.output/'execution.json').write_bytes(encode(dict(owner='rebuild_current_two_arm_circle_routes',snapshot_sha256=sha(a.snapshot),
        provider_sha256=expected_sha,native_proof_sha256=sha(a.native_run/'current-two-arm-routes.json'),
        elapsed_seconds=time.perf_counter()-started,all_original_providers_replayed=True,human_accepted=False)))

if __name__=='__main__':main()
