"""Replay all local plans, retaining every inherited reader and projected role."""
import argparse,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from rebuild_local_detail_full_plan_DN import compute as previous_compute,implementation_hashes as previous_hashes,canonical,checked
from native_projected_circle_main_role import authorities
from projected_circle_plan_DN import make_reader
MODE='complete_local_plan_native_DN_explicit_projected_circle_v8'
def compute(manifest,announce=lambda x:None):
    allowed=authorities(manifest['projected_circle_expert_authorities'])
    namespace=dict(previous_compute.__globals__);namespace['collect']=make_reader(allowed)
    reader=types.FunctionType(previous_compute.__code__,namespace,previous_compute.__name__)
    result=reader(manifest,announce);result['previous_local_detail_mode']=result['mode'];result['mode']=MODE;result['projected_circle_expert_authorities']=allowed
    return result
def implementation_hashes():
    result=previous_hashes()
    for name in ('native_projected_circle_main_role.py','projected_circle_plan_DN.py',Path(__file__).name):result['projected_circle:'+name]=sha(Path(__file__).with_name(name))
    return result
def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'local-detail-plan-DN-receipt.json');target=directory/'local-detail-plan-DN-results.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('projected circle local DN implementation changed')
    if sha(target)!=receipt['output_sha256']:raise ValueError('projected circle local DN result changed')
    result=compute(load(checked(receipt['manifest'])))
    if canonical(result)!=canonical(load(target)):raise ValueError('complete projected-circle DN native replay differs')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification cannot replace inputs')
        print(verify_output(a.verify_output)['counts']);return
    if not a.manifest or not a.output:p.error('fixed manifest and new output required')
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(load(a.manifest),lambda s:print(s,flush=True));a.output.mkdir(parents=True);target=a.output/'local-detail-plan-DN-results.json';target.write_bytes(encode(result))
    (a.output/'local-detail-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(a.manifest.resolve()),sha256=sha(a.manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)
if __name__=='__main__':main()
