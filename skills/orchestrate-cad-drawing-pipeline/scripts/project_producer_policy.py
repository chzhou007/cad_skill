"""Project typed physical policy paths between byte-checked package roots.

Original source JSON, indexes and derivation receipts remain unchanged. This
does not certify a new execution, relocate logical CAD identities, or declare
the rest of a reconstruction package complete.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os

def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text('utf8'))
def encode(j):return(json.dumps(j,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def pin(p):return dict(path=str(Path(p).resolve()),sha256=sha(p))
def require(value,message):
    if not value:raise ValueError(message)
def compute(source_policy,source_receipt,source_package,target_package):
    source_policy,source_receipt,source_package,target_package=map(lambda p:Path(p).resolve(),(source_policy,source_receipt,source_package,target_package))
    require(source_package.is_dir()and target_package.is_dir(),'Existing source and target packages required')
    require(not source_package.is_relative_to(target_package)and not target_package.is_relative_to(source_package),'Package roots must be disjoint')
    initial=[pin(source_policy),pin(source_receipt)];policy=load(source_policy);receipt=load(source_receipt)
    require(set(policy)=={'mode','owned_seeds','additional_files','directories','negative'},'Unknown policy fields require explicit projection support')
    require(policy['mode']=='producer_API_input_enforcement_v1','An explicit strict source policy is required')
    require(receipt['mode']=='producer_API_policy_derivation_receipt_v1'and receipt['policy_sha256']==sha(source_policy),'Source policy receipt differs')
    require(Path(receipt['package']).resolve()==source_package,'Receipt source package differs')
    source_bindings=[receipt['producer_result'],receipt['seed_manifest']]
    require(all(sha(x['path'])==x['sha256']for x in source_bindings),'Original policy source bindings changed')
    projected=dict(mode=policy['mode'],owned_seeds=dict(policy['owned_seeds']),additional_files={},directories={},negative=[])
    for relative,digest in policy['owned_seeds'].items():
        require(isinstance(relative,str)and relative and '\\'not in relative and ':'not in relative and not PurePosixPath(relative).is_absolute()
            and all(p not in ('','.','..')for p in relative.split('/'))and isinstance(digest,str)and len(digest)==64,'Invalid unchanged relative seed binding')
    def target(path):
        require(isinstance(path,str)and os.path.isabs(path),'Absolute physical policy path required')
        original=Path(path).resolve();require(original.is_relative_to(source_package),'Positive policy path is outside source package')
        result=(target_package/original.relative_to(source_package)).resolve()
        require(result.is_relative_to(target_package),'Projected input escaped target package')
        return original,result,os.path.normcase(str(result))
    files=[];directories=[];external=[]
    for path,digest in policy['additional_files'].items():
        original,new,key=target(path)
        require(sha(original)==digest,'Original source bytes changed')
        require(new.is_file()and sha(new)==digest,'Independent target bytes differ or are missing')
        require(key not in projected['additional_files']or projected['additional_files'][key]==digest,'Projected file identity collision')
        projected['additional_files'][key]=digest;files.append(dict(source=pin(original),target=pin(new)))
    for path,members in policy['directories'].items():
        original,new,key=target(path)
        require(os.listdir(original)==members,'Original directory members changed')
        require(new.is_dir()and os.listdir(new)==members,'Independent directory members differ')
        projected['directories'][key]=members;directories.append(dict(source=str(original),target=str(new),entries=members))
    for path in policy['negative']:
        require(isinstance(path,str)and os.path.isabs(path),'Absolute absence probe required')
        original=Path(path).resolve()
        if original.is_relative_to(source_package):
            new=(target_package/original.relative_to(source_package)).resolve()
            require(new.is_relative_to(target_package),'Absence probe escaped target package')
        else:new=original;external.append(str(original))
        for candidate in [original,new]:
            try:os.stat(candidate)
            except FileNotFoundError:pass
            else:raise ValueError('Previously absent probe now exists')
        projected['negative'].append(os.path.normcase(str(new)))
    projected['negative']=sorted(set(projected['negative']))
    require(all(sha(x['path'])==x['sha256']for x in initial+source_bindings),'Source declarations changed during projection')
    proof=dict(mode='typed_physical_package_policy_namespace_projection_v1',source_policy=initial[0],source_derivation_receipt=initial[1],
        source_package=str(source_package),target_package=str(target_package),original_source_bindings=source_bindings,
        files=files,directories=directories,external_negative_probes_retained=external,
        relative_seed_bindings_unchanged=True,original_JSON_and_proofs_rewritten=False,source_policy_rederivation_performed=False,
        new_producer_execution_required=True,independent_raw_reconstruction_verified=False,raw_CAD_values_assigned=0,human_accepted=False)
    return projected,proof
def produce(source_policy,source_receipt,source_package,target_package,output):
    output=Path(output).resolve();require(not output.exists(),'Fresh projection output required')
    require(not output.is_relative_to(Path(source_package).resolve())and not output.is_relative_to(Path(target_package).resolve()),'Projection output must not modify either package')
    policy,proof=compute(source_policy,source_receipt,source_package,target_package);output.mkdir()
    (output/'policy.json').write_bytes(encode(policy));(output/'projection.json').write_bytes(encode(proof))
    receipt=dict(mode='typed_producer_policy_projection_receipt_v1',implementation_sha256=sha(__file__),source_policy=pin(source_policy),
        source_receipt=pin(source_receipt),source_package=str(Path(source_package).resolve()),target_package=str(Path(target_package).resolve()),
        policy_sha256=sha(output/'policy.json'),projection_sha256=sha(output/'projection.json'))
    (output/'receipt.json').write_bytes(encode(receipt));return proof
def verify(output):
    output=Path(output).resolve();receipt=load(output/'receipt.json')
    require(receipt['mode']=='typed_producer_policy_projection_receipt_v1'and receipt['implementation_sha256']==sha(__file__),'Projection owner changed')
    require(all(sha(receipt[k]['path'])==receipt[k]['sha256']for k in ['source_policy','source_receipt']),'Original projection sources changed')
    policy,proof=compute(receipt['source_policy']['path'],receipt['source_receipt']['path'],receipt['source_package'],receipt['target_package'])
    require((output/'policy.json').read_bytes()==encode(policy)and sha(output/'policy.json')==receipt['policy_sha256'],'Projected policy differs on independent verification')
    require((output/'projection.json').read_bytes()==encode(proof)and sha(output/'projection.json')==receipt['projection_sha256'],'Projection evidence differs')
    return proof
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source-policy','source-receipt','source-package','target-package','output','verify-output']:p.add_argument('--'+key,type=Path)
    a=p.parse_args()
    if not a.verify_output and not all([a.source_policy,a.source_receipt,a.source_package,a.target_package,a.output]):p.error('Source policy/receipt, both packages and fresh output required')
    proof=verify(a.verify_output)if a.verify_output else produce(a.source_policy,a.source_receipt,a.source_package,a.target_package,a.output)
    print(json.dumps(dict(mode=proof['mode'],files=len(proof['files']),directories=len(proof['directories']),new_producer_execution_required=True)))
if __name__=='__main__':main()
