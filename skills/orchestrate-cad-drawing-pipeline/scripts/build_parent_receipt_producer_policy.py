"""Typed receipt-role projection; keep raw discovery records and original policy checks."""
import argparse,copy,hashlib,json,os,types
from pathlib import Path
import build_producer_input_policy as original
from producer_parent_receipt_observation import receipt_bindings,checked_receipt,sha,key
MODE='qualified_generated_parent_receipt_policy_derivation_v1'
load=original.load;encode=original.encode;pin=original.pin

def compute(result_path,package,seeds):
    result_path,package,seeds=map(lambda p:Path(p).resolve(),(result_path,package,seeds));result=load(result_path)
    reports=[load(x['path'])for x in result['observations']]
    digests={x['input_index_sha256']for x in reports}
    if len(digests)!=1:raise ValueError('one observed producer index required')
    index_path=package/'indexes'/(next(iter(digests))+'.json')
    if not index_path.exists():index_path=package/'logical-input-index.json'
    if sha(index_path)!=next(iter(digests)):raise ValueError('source producer index changed')
    index=load(index_path);work=Path(result.get('actual_work',result_path.parent/'work')).resolve();bindings=receipt_bindings(index,work)
    qualified={name:checked_receipt(value)for name,value in bindings.items()};views={};changes=[]
    for item,report in zip(result['observations'],reports):
        if sha(item['path'])!=item['sha256']:raise ValueError('original discovery receipt changed')
        view=copy.deepcopy(report);kept=[]
        for row in report['unresolved']:
            name=key(row['path'])
            if row['role']=='owned_output'and row['reason']=='owned_read_without_seed_or_successful_writer'and name in qualified:
                if row['state'].get('kind')!='file'or row['state'].get('sha256',bindings[name]['sha256'])!=bindings[name]['sha256']:
                    raise ValueError('discovery producer receipt observed different content')
                changes.append(dict(report=pin(item['path']),original_observation=copy.deepcopy(row),qualified_role=qualified[name]))
            else:kept.append(copy.deepcopy(row))
        view['unresolved']=kept
        for path,state in list(view['immutable_inputs'].items()):
            name=key(path)
            if name in qualified:
                if state.get('kind')!='file'or state.get('sha256',bindings[name]['sha256'])!=bindings[name]['sha256']:
                    raise ValueError('immutable producer receipt state changed')
                del view['immutable_inputs'][path]
        views[key(item['path'])]=view
    def typed_load(path):return copy.deepcopy(views[key(path)])if key(path)in views else load(path)
    inherited=types.FunctionType(original.compute.__code__,dict(original.compute.__globals__,load=typed_load),original.compute.__name__)
    policy,derivation=inherited(result_path,package,seeds)
    if any(key(name)in qualified for name in policy['additional_files']):raise ValueError('fresh producer receipt cannot become fixed package input')
    for name,binding in bindings.items():
        if sha(binding['path'])!=binding['sha256']:raise ValueError('producer receipt changed during derivation')
    return policy,dict(mode=MODE,original_policy_derivation=derivation,qualified_fresh_parent_producer_receipts=list(qualified.values()),
        raw_observations_rewritten=False,typed_role_reclassifications=changes,original_policy_owner_reexecuted=True,original_owned_output_guard_retained=True,
        fresh_producer_receipts_added_as_seeds=0,strict_producer_execution_required=True,human_accepted=False)

def implementations():return dict(entry=sha(__file__),original_policy=sha(original.__file__),receipt_observer=sha(Path(__file__).with_name('producer_parent_receipt_observation.py')))
def produce(result,package,seeds,output):
    output=Path(output);before=implementations()
    if output.exists():raise FileExistsError(output)
    policy,proof=compute(result,package,seeds)
    if before!=implementations():raise ValueError('receipt policy owner changed')
    output.mkdir();(output/'policy.json').write_bytes(encode(policy));(output/'derivation.json').write_bytes(encode(proof))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,producer_result=pin(result),package=str(Path(package).resolve()),seed_manifest=pin(seeds),implementations=before,policy_sha256=sha(output/'policy.json'),derivation_sha256=sha(output/'derivation.json'))));return proof

def verify(output):
    output=Path(output);r=load(output/'receipt.json')
    if r['mode']!=MODE or r['implementations']!=implementations()or any(sha(r[k]['path'])!=r[k]['sha256']for k in('producer_result','seed_manifest')):raise ValueError('receipt policy inputs changed')
    policy,proof=compute(r['producer_result']['path'],r['package'],r['seed_manifest']['path'])
    if encode(policy)!=(output/'policy.json').read_bytes()or encode(proof)!=(output/'derivation.json').read_bytes()or sha(output/'policy.json')!=r['policy_sha256']or sha(output/'derivation.json')!=r['derivation_sha256']:raise ValueError('receipt policy independent replay differs')
    return proof

def main():
    p=argparse.ArgumentParser()
    for n in('producer-result','package','seed-manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();r=verify(a.verify_output)if a.verify_output else produce(a.producer_result,a.package,a.seed_manifest,a.output)
    d=r['original_policy_derivation'];print(dict(mode=MODE,reclassified_receipt_reads=len(r['typed_role_reclassifications']),qualified_receipts=len(r['qualified_fresh_parent_producer_receipts']),input_files=d['input_files'],input_directories=d['input_directories'],negative_probes=d['negative_probes'],strict_producer_execution_required=True),flush=True)
if __name__=='__main__':main()
