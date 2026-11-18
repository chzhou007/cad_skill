"""Independently replay the source inventory before batch owner correction."""
import argparse,csv,importlib,sys
from pathlib import Path
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from rebuild_native_flange_contact_ownership import verify_output as inventory_owner
from native_ball_contact_reapplication import reapply,MODE
from source_readability import read_source

def implementation_hashes():
    return dict(entry=sha(__file__),**{name:sha(importlib.import_module(name).__file__)for name in ('native_ball_contact_reapplication','native_flange_contact_ownership','rebuild_native_flange_contact_ownership','native_inline_coordinates','native_line_path_evidence','source_readability')})

def compute(manifest):
    inputs=manifest['inputs'];paths={key:Path(value['path'])for key,value in inputs.items()}
    def checked():
        if any(sha(paths[key])!=value['sha256']for key,value in inputs.items()):raise ValueError('native ball contact input changed')
    checked();original=inventory_owner(paths['original_inventory'].parent)
    if encode(original)!=paths['original_inventory'].read_bytes():raise ValueError('complete native component inventory replay differs')
    if any(original['inputs'][key]!=inputs[key]for key in ('source','graph')):raise ValueError('ball ownership source ancestry differs')
    doc,preflight=read_source(paths['source']);graph=load(paths['graph'])
    if graph['metadata']['source_sha256']!=inputs['source']['sha256']:raise ValueError('native ball graph/source differs')
    result=reapply(doc,graph,original['components']);checked()
    return dict(result,inputs=inputs,original_native_inventory_replayed=True,complete_source_family_scanned=True,source_preflight=preflight,component_aware_mapping_requalified=False,viewer_index_adopted=False,whole_goal_complete=False)

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest))
    if before!=implementation_hashes():raise ValueError('native ball ownership implementation changed')
    output.mkdir(parents=True);proof=output/'native-ball-contact-owners.json';proof.write_bytes(encode(result))
    components=output/'edge_device_instances.csv'
    with components.open('w',encoding='utf-8-sig',newline='')as handle:
        writer=csv.DictWriter(handle,fieldnames=list(result['components'][0]));writer.writeheader();writer.writerows(result['components'])
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(proof),components_sha256=sha(components))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');manifest=receipt['manifest'];proof=output/'native-ball-contact-owners.json';components=output/'edge_device_instances.csv'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(manifest['path'])!=manifest['sha256']or sha(proof)!=receipt['output_sha256']or sha(components)!=receipt['components_sha256']:raise ValueError('native ball ownership receipt or code changed')
    result=compute(load(manifest['path']))
    if encode(result)!=proof.read_bytes():raise ValueError('native ball ownership source replay differs')
    with components.open(encoding='utf-8-sig',newline='')as handle:
        if list(csv.DictReader(handle))!=result['components']:raise ValueError('native ball ownership CSV differs')
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ('manifest','output','verify-output'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.verify_output:result=verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
        result=produce(args.manifest,args.output)
    print(result['counts'],flush=True)

if __name__=='__main__':main()
