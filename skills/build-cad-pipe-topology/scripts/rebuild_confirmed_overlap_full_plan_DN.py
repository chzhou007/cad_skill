"""Versioned complete-plan DN entry using original overlap owner evidence."""
import argparse,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from rebuild_user_circle_full_plan_DN import compute as previous_compute,implementation_hashes as previous_hashes,canonical,checked
from confirmed_overlap_plan_DN import collect

MODE='complete_local_plan_native_DN_confirmed_overlap_roles_v5'


def compute(manifest,announce=lambda x:None):
    owners={}
    for item in manifest['plans']:
        entries=item.get('confirmed_overlap_owners',[])
        for entry in entries:
            for spec in entry.values():checked(spec)
        owners[item['inputs']['graph']['sha256']]=entries
    namespace=dict(previous_compute.__globals__)
    namespace['collect']=lambda d,g,sh,gh,seeds,log,circle,config,parents,review:collect(d,g,sh,gh,seeds,log,circle,config,parents,review,owners[gh])
    reader=types.FunctionType(previous_compute.__code__,namespace,previous_compute.__name__)
    result=reader(manifest,announce)
    result['previous_user_circle_mode']=result['mode'];result['mode']=MODE
    for item in manifest['plans']:
        for entry in item.get('confirmed_overlap_owners',[]):
            for spec in entry.values():checked(spec)
    return result


def implementation_hashes():
    result=previous_hashes()
    from native_confirmed_overlap_rays import implementation_hashes as overlap_hashes
    result.update({'confirmed_overlap:'+name:value for name,value in overlap_hashes().items()})
    result['overlap_plan_DN']=sha(Path(__file__).with_name('confirmed_overlap_plan_DN.py'))
    result['overlap_entry']=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'confirmed-overlap-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('confirmed-overlap complete-plan implementation changed')
    target=directory/'confirmed-overlap-plan-DN-results.json'
    if sha(target)!=receipt['output_sha256']:raise ValueError('confirmed-overlap complete-plan result changed')
    result=compute(load(checked(receipt['manifest'])))
    if canonical(result)!=canonical(load(target)):raise ValueError('confirmed-overlap complete-plan independent native replay differs')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);args=p.parse_args()
    if args.verify_output:
        if args.manifest or args.output:p.error('verification cannot replace inputs')
        print(verify_output(args.verify_output)['counts']);return
    if not args.manifest or not args.output:p.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda s:print(s,flush=True));args.output.mkdir(parents=True)
    target=args.output/'confirmed-overlap-plan-DN-results.json';target.write_bytes(encode(result))
    (args.output/'confirmed-overlap-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)


if __name__=='__main__':main()
