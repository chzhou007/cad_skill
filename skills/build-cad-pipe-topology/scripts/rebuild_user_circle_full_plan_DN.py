"""Versioned complete-plan entry for the inherited user-circle corner schema."""
import argparse,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from rebuild_current_circle_full_plan_DN import compute as previous_compute,implementation_hashes as previous_hashes,canonical,checked
from user_circle_endpoint_plan_DN import collect

MODE='complete_local_plan_native_DN_user_circle_endpoint_rays_v4'


def compute(manifest,announce=lambda x:None):
    reviews={}
    for item in manifest['plans']:
        review=item.get('circle_endpoint_review')
        if review is not None:checked(review)
        reviews[item['inputs']['graph']['sha256']]=review
    namespace=dict(previous_compute.__globals__)
    namespace['collect']=lambda d,g,sh,gh,seeds,log,circle,config,parents:collect(d,g,sh,gh,seeds,log,circle,config,parents,reviews[gh])
    reader=types.FunctionType(previous_compute.__code__,namespace,previous_compute.__name__)
    result=reader(manifest,announce)
    result['previous_circle_mode']=result['mode'];result['mode']=MODE
    for item in manifest['plans']:
        if item.get('circle_endpoint_review')is not None:checked(item['circle_endpoint_review'])
    return result


def implementation_hashes():
    result=previous_hashes()
    from native_user_circle_endpoint_rays import implementation_hashes as endpoint_hashes
    result.update({'user_circle_endpoint:'+name:value for name,value in endpoint_hashes().items()})
    result['endpoint_plan_DN']=sha(Path(__file__).with_name('user_circle_endpoint_plan_DN.py'))
    result['endpoint_entry']=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'user-circle-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('user-circle endpoint DN implementation changed')
    target=directory/'user-circle-plan-DN-results.json'
    if sha(target)!=receipt['output_sha256']:raise ValueError('user-circle endpoint DN result changed')
    result=compute(load(checked(receipt['manifest'])))
    if canonical(result)!=canonical(load(target)):raise ValueError('user-circle full-plan DN independent native replay differs')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);args=p.parse_args()
    if args.verify_output:
        if args.manifest or args.output:p.error('verification cannot replace inputs')
        print(verify_output(args.verify_output)['counts']);return
    if not args.manifest or not args.output:p.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda s:print(s,flush=True));args.output.mkdir(parents=True)
    target=args.output/'user-circle-plan-DN-results.json';target.write_bytes(encode(result))
    (args.output/'user-circle-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)


if __name__=='__main__':main()
