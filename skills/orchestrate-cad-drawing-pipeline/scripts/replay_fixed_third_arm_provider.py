"""Execute the complete qualified provider in its pinned original runtime."""
import argparse,hashlib,json,sys,time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    for key in('skills-root','snapshot','native-run','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True);args=parser.parse_args();root=args.skills_root.resolve()
    snapshot=json.loads(args.snapshot.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def checked():
        if any(sha(root/name)!=value for name,value in snapshot['files'].items()):raise ValueError('fixed third-arm runtime changed')
        if sha(args.native_run/'provider-inventory.json')!=args.expected_sha256:raise ValueError('fixed third-arm provider changed')
    checked();own=Path(__file__).resolve().parent;sys.path=[p for p in sys.path if Path(p or'.').resolve()!=own]
    for name in('visualize-cad-pipe-topology','orchestrate-cad-drawing-pipeline','build-cad-pipe-topology'):sys.path.insert(0,str(root/name/'scripts'))
    from rebuild_third_arm_crossview_batch import verify_output
    from confirm_crossview_paths import encode
    started=time.perf_counter();proof,result=verify_output(args.native_run);raw=(args.native_run/'provider-inventory.json').read_bytes()
    if encode(result)!=raw or proof['complete_original_provider_replayed']is not True:raise ValueError('complete original third-arm provider replay differs')
    checked();args.output.mkdir(parents=True,exist_ok=False);(args.output/'proof.json').write_bytes(raw)
    (args.output/'execution.json').write_text(json.dumps(dict(owner='third_arm_crossview_batch',proof_sha256=args.expected_sha256,snapshot_sha256=sha(args.snapshot),elapsed_seconds=time.perf_counter()-started,human_accepted=False),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
