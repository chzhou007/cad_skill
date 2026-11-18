"""Complete local DN using source detail T evidence independently of owners."""
import argparse,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from rebuild_main_continuity_full_plan_DN import compute as previous_compute,implementation_hashes as previous_hashes,canonical,checked
from local_detail_plan_DN import collect

MODE='complete_local_plan_native_DN_unowned_detail_T_v7'

def compute(manifest,announce=lambda x:None):
    namespace=dict(previous_compute.__globals__);namespace['collect']=collect
    reader=types.FunctionType(previous_compute.__code__,namespace,previous_compute.__name__)
    result=reader(manifest,announce);result['previous_main_continuity_mode']=result['mode'];result['mode']=MODE
    return result

def implementation_hashes():
    result=previous_hashes()
    for name in('native_local_detail_T_evidence.py','local_detail_plan_DN.py','canonicalize_confirmed_sideviews.py','native_line_path_evidence.py',Path(__file__).name):
        result['local_detail_T:'+name]=sha(Path(__file__).with_name(name))
    return result

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'local-detail-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('local detail T DN implementation changed')
    target=directory/'local-detail-plan-DN-results.json'
    if sha(target)!=receipt['output_sha256']:raise ValueError('local detail T DN result changed')
    result=compute(load(checked(receipt['manifest'])))
    if canonical(result)!=canonical(load(target)):raise ValueError('local detail T complete-plan independent replay differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);args=p.parse_args()
    if args.verify_output:
        if args.manifest or args.output:p.error('verification cannot replace inputs')
        print(verify_output(args.verify_output)['counts']);return
    if not args.manifest or not args.output:p.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda s:print(s,flush=True));args.output.mkdir(parents=True)
    target=args.output/'local-detail-plan-DN-results.json';target.write_bytes(encode(result))
    (args.output/'local-detail-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)

if __name__=='__main__':main()
