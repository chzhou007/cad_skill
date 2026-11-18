"""Source-bound fallback after independent replay of the original valve owner."""
import argparse,csv,importlib,sys
from pathlib import Path
_root=Path(__file__).resolve().parents[2]
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(_root/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from rebuild_native_balancing_valves import verify_output as original_owner
from native_flange_contact_ownership import recover,MODE
from source_readability import read_source

def implementation_hashes():
    return dict(entry=sha(__file__),**{name:sha(importlib.import_module(name).__file__)for name in ('native_flange_contact_ownership','rebuild_native_balancing_valves','native_balancing_valve_recovery','native_inline_coordinates','native_line_path_evidence','source_readability')})

def compute(manifest):
    inputs=manifest['inputs'];paths={key:Path(value['path'])for key,value in inputs.items()}
    def checked():
        if any(sha(paths[key])!=value['sha256']for key,value in inputs.items()):raise ValueError('native flange input changed')
    checked();original=original_owner(paths['original_inventory'].parent)
    if encode(original)!=paths['original_inventory'].read_bytes():raise ValueError('original native valve replay differs')
    for key in ('source','graph'):
        if original['inputs'][key]!=inputs[key]:raise ValueError('flange fallback uses another native source or graph')
    graph=load(paths['graph']);doc,preflight=read_source(paths['source'])
    if graph['metadata']['source_sha256']!=inputs['source']['sha256']:raise ValueError('native flange graph/source differs')
    unresolved=[row['source_handle']for row in original['records']if row['status']in ('no_unique_native_pipe','no_unique_graph_segment')]
    result=recover(doc,graph,original['components'],unresolved)
    if result['components'][:len(original['components'])]!=original['components']:raise ValueError('original source component prefix changed')
    checked()
    return dict(result,inputs=inputs,original_native_owner_replayed=True,source_preflight=preflight,original_unresolved_population=unresolved,flange_population_complete=True,published_graph_changed=False,component_aware_mapping_requalified=False,viewer_index_adopted=False,whole_goal_complete=False)

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest))
    if before!=implementation_hashes():raise ValueError('native flange implementation changed')
    output.mkdir(parents=True);proof=output/'native-flange-contact-ownership.json';proof.write_bytes(encode(result))
    components=output/'edge_device_instances.csv'
    with components.open('w',encoding='utf-8-sig',newline='')as handle:
        writer=csv.DictWriter(handle,fieldnames=list(result['components'][0]));writer.writeheader();writer.writerows(result['components'])
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(proof),components_sha256=sha(components))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');manifest=receipt['manifest'];proof=output/'native-flange-contact-ownership.json';components=output/'edge_device_instances.csv'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(manifest['path'])!=manifest['sha256']or sha(proof)!=receipt['output_sha256']or sha(components)!=receipt['components_sha256']:raise ValueError('native flange receipt or implementation changed')
    result=compute(load(manifest['path']))
    if encode(result)!=proof.read_bytes():raise ValueError('native flange source replay differs')
    with components.open(encoding='utf-8-sig',newline='')as handle:
        if list(csv.DictReader(handle))!=result['components']:raise ValueError('native flange CSV differs')
    return result

def main():
    parser=argparse.ArgumentParser()
    for name in ('manifest','output','verify-output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.verify_output:result=verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
        result=produce(args.manifest,args.output)
    print(result['counts'],flush=True)

if __name__=='__main__':main()
