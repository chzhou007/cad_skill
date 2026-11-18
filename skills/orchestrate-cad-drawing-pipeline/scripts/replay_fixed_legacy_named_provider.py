"""Re-execute the original full legacy provider in its frozen import domain."""
import argparse,hashlib,json,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for k in('skills-root','snapshot','native-run','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-sha256',required=True);a=p.parse_args();root=a.skills_root.resolve();snapshot=json.loads(a.snapshot.read_text(encoding='utf8'));sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
    def checked():
        if any(sha(root/n)!=h for n,h in snapshot['files'].items()):raise ValueError('fixed legacy runtime changed')
        if sha(a.native_run/'provider-inventory.json')!=a.expected_sha256:raise ValueError('fixed legacy provider changed')
    checked();own=Path(__file__).resolve().parent;sys.path=[v for v in sys.path if Path(v or'.').resolve()!=own]
    for n in('visualize-cad-pipe-topology','orchestrate-cad-drawing-pipeline','build-cad-pipe-topology'):sys.path.insert(0,str(root/n/'scripts'))
    from legacy_named_provider_inventory import verify_output
    from confirm_crossview_paths import encode
    start=time.perf_counter();result=verify_output(a.native_run);raw=(a.native_run/'provider-inventory.json').read_bytes()
    if encode(result)!=raw:raise ValueError('original complete legacy provider replay differs')
    checked();a.output.mkdir(parents=True,exist_ok=False);(a.output/'proof.json').write_bytes(raw)
    (a.output/'execution.json').write_text(json.dumps(dict(owner='legacy_named_provider_inventory',status='original_complete_legacy_provider_natively_rechecked',proof_sha256=a.expected_sha256,snapshot_sha256=sha(a.snapshot),elapsed_seconds=time.perf_counter()-start,human_accepted=False),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
