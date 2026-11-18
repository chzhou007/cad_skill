"""Run the original complete component-provider owner in its immutable runtime."""
import argparse,hashlib,json,sys,time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    for key in ('skills-root','snapshot','native-run','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True);args=parser.parse_args();root=args.skills_root.resolve();snapshot=json.loads(args.snapshot.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def checked():
        if any(sha(root/name)!=value for name,value in snapshot['files'].items()):raise ValueError('fixed published parent runtime changed')
        if sha(args.native_run/'provider-inventory.json')!=args.expected_sha256:raise ValueError('fixed published provider changed')
    checked()
    # A fixed path order prevents unrelated importing callers from changing the
    # original owner's already checked subprocess/cache binding environment.
    own=Path(__file__).resolve().parent
    sys.path=[p for p in sys.path if Path(p or '.').resolve()!=own]
    for name in ('visualize-cad-pipe-topology','orchestrate-cad-drawing-pipeline','build-cad-pipe-topology'):
        sys.path.insert(0,str(root/name/'scripts'))
    from recovered_component_provider_inventory import verify_output
    start=time.perf_counter();result=verify_output(args.native_run);raw=(args.native_run/'provider-inventory.json').read_bytes()
    if result!=json.loads(raw):raise ValueError('fixed native parent replay differs')
    checked();args.output.mkdir(parents=True,exist_ok=False);(args.output/'proof.json').write_bytes(raw)
    (args.output/'execution.json').write_text(json.dumps(dict(status='original_complete_component_provider_natively_rechecked',owner='recovered_component_provider_inventory',proof_sha256=args.expected_sha256,skills_root=str(root),snapshot_sha256=sha(args.snapshot),elapsed_seconds=time.perf_counter()-start,human_accepted=False),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
