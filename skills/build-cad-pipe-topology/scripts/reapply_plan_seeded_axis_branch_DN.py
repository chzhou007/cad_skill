"""Replay original plan-main owners before batch third-arm DN qualification."""
import argparse,csv,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_air_vent_attribute_items import collect as normalized_items
from native_replay_session import verify_once
from reviewed_uniform_subroute_DN import verify_output as uniform_owner
from reapply_received_scope_attributes import verify_output as received_owner
from refresh_reviewed_ring_partition_DN import effective
from plan_seeded_axis_branch_DN import collect,MODE,require

def compute(manifest):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'fixed plan-seeded branch input changed')
    checked()
    print('Replaying complete original floor-plan main DN owners',flush=True)
    uniform=verify_once(Path(inputs['uniform_proof']['path']).parent,uniform_owner)
    received=verify_once(Path(inputs['received_proof']['path']).parent,received_owner)
    for result,name in[(uniform,'uniform_proof'),(received,'received_proof')]:
        require(encode(result)==Path(inputs[name]['path']).read_bytes(),'fresh original plan-main owner replay differs')
    require(received['inputs']['original_uniform_proof']==inputs['uniform_proof'],'received main proof has another original parent')
    require(uniform['inputs']['routing_proof']==inputs['routing'],'original main owner uses another direction inventory')
    route=load(inputs['routing']['path']);graph=load(inputs['axis_graph']['path'])
    require(route['inputs']['graph']==inputs['axis_graph']and route['inputs']['source']==inputs['axis_source'],
            'source-plan owners and current axis namespace differ')
    vm=load(inputs['viewer_manifest']['path']);values=load(inputs['current_effective']['path'])
    viewer=Path(inputs['viewer_manifest']['path']).parents[2]
    require(encode(effective(viewer))==encode(values),'actual current reader and frozen effective values differ')
    records=[]
    for key,source in [('reviewed_uniform_subroute_DN',uniform),('received_scope_uniform_DN',received)]:
        rows=vm['attributeValueContext'][key]['records']
        require(encode(rows)==encode(source['records']),'actual current source-plan main context differs from fresh owner')
        records.extend(rows)
    provider=load(inputs['provider']['path'])
    for key in('axis_source','axis_graph'):require(provider['inputs'][key]==inputs[key],'current provider source namespace differs')
    doc,preflight=read_source(inputs['axis_source']['path'])
    with Path(inputs['canonical_components']['path']).open(encoding='utf-8-sig',newline='')as stream:
        inventory=list(csv.DictReader(stream))
    items,normalization=normalized_items(doc,graph,inventory)
    result=collect(doc,graph,route,records,{r['edge_id']:r['values']for r in values},items,
                   inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
    checked();result.update(inputs=inputs,source_preflight=preflight,inherited_air_vent_normalization=normalization,
        complete_original_plan_main_owners_independently_replayed=True,actual_current_main_contexts_exact=True,
        viewer_adoption_pending=True)
    return result

def implementations():
    names=('plan_seeded_axis_branch_DN','native_air_vent_attribute_items','reviewed_uniform_subroute_DN',
        'reapply_received_scope_attributes','crossview_equipment_branch_inventory','inherited_marker_and_crossover_evidence',
        'native_drawing_marker_ports','axis_unbranched_vertical_DN','compound_member_interfaces','native_paired_caption_geometry','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh plan-seeded branch output required');code=implementations()
    result=compute(load(manifest));require(code==implementations(),'plan-seeded branch implementation changed')
    output.mkdir(parents=True);target=output/'plan-seeded-axis-branch-DN.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');target=output/'plan-seeded-axis-branch-DN.json'
    require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()
        and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(target)==receipt['output_sha256'],
        'plan-seeded branch source, code or receipt changed')
    fresh=compute(load(receipt['manifest']['path']));require(encode(fresh)==target.read_bytes(),'independent native plan-seeded branch replay differs')
    return fresh

def main():
    parser=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify_output(args.verify_output)if args.verify_output else produce(args.manifest,args.output)
    print(dict(mode=MODE,counts=result['counts'],pending=result['pending']),flush=True)
if __name__=='__main__':main()
