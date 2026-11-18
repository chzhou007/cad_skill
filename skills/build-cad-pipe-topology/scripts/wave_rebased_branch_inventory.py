"""Rebuild plan branch evidence after a separately replayed wave reconstruction.

The old v3 inventory is replayed as history. Its unchanged axis evidence remains
valid on the exact same axis/source/component version; every plan service is
checked anew against the new local graph. Historical owners are never forged.
"""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,inspect_branch,_caption,unresolved_identity_candidates
from inherited_circle_branch_inventory import MODE as PARENT_MODE,inspect as inspect_circle,verify_output as verify_parent
from inherited_wave_pair_continuity import MODE as WAVE_MODE,verify_output as verify_wave

MODE='wave_rebased_plan_branch_inventory_v4'


def check_transition(before,after,source_hash,old_hash):
    old_nodes,old_edges,_=index_graph(before);nodes,edges,_=index_graph(after);wave=after.get('sourceInheritedWavePairContinuity',{})
    if (wave.get('mode')!=WAVE_MODE or wave.get('source_sha256')!=source_hash or wave.get('input_graph_sha256')!=old_hash
        or wave.get('human_accepted') is not False or wave.get('dependent_mapping_attributes_and_HIL_invalidated') is not True):raise ValueError('native wave transition required')
    removed={n['node_id'] for n in wave['retired_node_snapshots']};records=wave['records']
    if (len(removed)!=2*len(records) or not records or nodes!={nid:n for nid,n in old_nodes.items() if nid not in removed}
        or any(old_nodes.get(nid,{}).get('node_type')!='virtual_equipment' or old_nodes[nid].get('subtype')!='unresolved_source_terminal' for nid in removed)):
        raise ValueError('wave transition removed or changed real equipment/T objects')
    changed={eid for r in records for eid in r['edge_ids']};retired=set(wave['edge_id_mapping'])
    if (set(old_edges)-set(edges)!=retired or set(edges)-set(old_edges)
        or any(edges.get(eid)!=edge for eid,edge in old_edges.items() if eid not in changed)
        or any(after[k]!=v for k,v in before.items() if k not in ('nodes','edges','metadata'))):raise ValueError('unrelated source topology or owner roots changed')
    return dict(retired_nonphysical_nodes=sorted(removed),changed_or_retired_edges=sorted(changed),equipment_and_owner_roots_preserved=True)


def rebuild(doc,graph,before,parent,circle_policy,source_hash,old_hash,new_hash):
    transition=check_transition(before,graph,source_hash,old_hash);nodes,_,_=index_graph(graph);output=copy.deepcopy(parent)
    if (parent.get('status')!='source_comparison_inventory_not_mapping' or parent.get('local_graphs_mutated') is not False
        or parent.get('mapped_paths')!=0 or parent.get('human_accepted') is not False or parent.get('hil_ready') is not False):raise ValueError('complete source inventory parent required')
    selection={(r['equipment_id'],r['system']):r for r in circle_policy['selections']}
    if len(selection)!=len(circle_policy['selections']):raise ValueError('duplicate inherited source branch scope')
    extension=output['inherited_circle_branch_extension'];expected={(r['equipment_id'],r['system']) for r in extension['records']}
    if set(selection)!=expected or extension.get('mode')!=PARENT_MODE:raise ValueError('inherited circle source family changed')
    rebuilt={};previous={r['equipment_id']:r for r in parent['records']};checked=[]
    for row in output['records']:
        did=row['equipment_id'];floor=row['floor'];captions=[e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text()==did]
        if len(captions)!=1:
            row['views']['plan']=dict(status='missing_or_ambiguous_native_caption')
        else:
            caption=_caption(doc,captions[0].dxf.handle,did);node=nodes.get(did)
            if not node or node.get('node_type') not in ('equipment','physical_equipment') or node.get('floor')!=floor:
                candidates=unresolved_identity_candidates(doc,graph,did,floor)
                row['views']['plan']=dict(status='unresolved_equipment_identity_candidates' if candidates else 'missing_or_floor_conflicting_equipment',
                    caption=caption,retained_native_equipment_candidates=candidates)
            else:
                services={}
                for system in ('supply','return'):
                    key=(did,system)
                    if key in selection:
                        current=inspect_circle(doc,graph,did,system,source_hash,new_hash,circle_policy)
                        if current['trace']['tee']!=selection[key]['node_id'] or current['trace']['edges']!=[selection[key]['edge_id']]:raise ValueError('inherited current branch scope changed')
                    else:current=inspect_branch(doc,graph,did,system,dict(source_sha256=source_hash,graph_sha256=new_hash),'plan',[])
                    services[system]=current;rebuilt[key]=current
                    checked.append(dict(equipment_id=did,system=system,ready=current.get('ready_for_mapping_comparison',False),reader='inherited_circle' if key in selection else 'historical_native_branch'))
                row['views']['plan']=dict(status='native_caption_read',caption=caption,services=services)
        row['ready_for_mapping_comparison']=all(row['views'].get(v,{}).get('services',{}).get(s,{}).get('ready_for_mapping_comparison',False) for v in ('plan','iso') for s in ('supply','return'))
        old=previous[did]
        if row['views'].get('iso')!=old['views'].get('iso'):raise ValueError('unchanged native axis evidence was altered')
        if old['ready_for_mapping_comparison'] and not row['ready_for_mapping_comparison']:raise ValueError('previously ready equipment failed fresh plan replay '+did)
        for system,state in old['views'].get('plan',{}).get('services',{}).items():
            if state.get('ready_for_mapping_comparison') and not rebuilt.get((did,system),{}).get('ready_for_mapping_comparison'):raise ValueError('previously ready source service regressed '+did+'/'+system)
    for row in extension['records']:
        key=(row['equipment_id'],row['system'])
        if key not in rebuilt:raise ValueError('inherited source extension lost equipment')
        row['source_evidence']=copy.deepcopy(rebuilt[key])
    output['counts']=dict(equipment=len(output['records']),ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in output['records']))
    output['inventory_mode']=MODE
    output['wave_reconstruction_inventory_rebase']=dict(mode=MODE,old_plan_graph_sha256=old_hash,plan_graph_sha256=new_hash,transition=transition,
        plan_service_checks=checked,axis_evidence_preserved_on_identical_inputs=True,local_graphs_mutated=False,mapped_paths=0,
        physical_values_assigned=0,physical_ports_verified=False,human_accepted=False)
    return output


def compute(paths,policy):
    for key in ('parent_inventory','parent_receipt','wave_graph','wave_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('wave inventory dependency changed '+key)
    parent_dir=Path(paths['parent_inventory']).resolve().parent;wave_dir=Path(paths['wave_graph']).resolve().parent
    if (Path(paths['parent_inventory']).resolve()!=parent_dir/'inventory.json' or Path(paths['parent_receipt']).resolve()!=parent_dir/'inventory-receipt.json'
        or Path(paths['wave_graph']).resolve()!=wave_dir/'graph_with_edges.json' or Path(paths['wave_receipt']).resolve()!=wave_dir/'inherited-wave-receipt.json'):
        raise ValueError('noncanonical native inventory/wave parents')
    parent_receipt=load(paths['parent_receipt'])
    if parent_receipt.get('mode')!=PARENT_MODE:raise ValueError('complete inherited v3 inventory required')
    parent=verify_parent(parent_dir);wave=verify_wave(wave_dir)
    local=load(parent_receipt['inputs']['parent_receipt']['path'])['inputs']
    for item in local.values():
        if sha(item['path'])!=item['sha256']:raise ValueError('original local source/axis dependency changed')
    if (wave['inputs']['graph']['sha256']!=local['plan_graph']['sha256'] or wave['inputs']['source']['sha256']!=local['plan_source']['sha256']
        or wave['output_graph_sha256']!=sha(paths['wave_graph'])):raise ValueError('wave reconstruction is not the current inventory plan child')
    source=Path(local['plan_source']['path']);doc,preflight=read_source(source);graph=load(paths['wave_graph']);old=load(local['plan_graph']['path'])
    result=rebuild(doc,graph,old,parent,load(parent_receipt['inputs']['policy']['path']),sha(source),local['plan_graph']['sha256'],sha(paths['wave_graph']))
    result['source_preflight']['plan']=preflight
    result['source_evidence_implementation_sha256'][Path(__file__).name]=sha(__file__)
    bindings={k:copy.deepcopy(local[k]) for k in ('plan_source','iso_source','plan_graph','iso_graph','iso_devices')}
    bindings['plan_graph']=dict(path=str(Path(paths['wave_graph']).resolve()),sha256=sha(paths['wave_graph']))
    bindings['plan_devices']=dict(path=str((wave_dir/'assigned_edge_device_instances.csv').resolve()),sha256=sha(wave_dir/'assigned_edge_device_instances.csv'))
    result['wave_reconstruction_inventory_rebase'].update(previous_inventory_sha256=sha(paths['parent_inventory']),wave_receipt_sha256=sha(paths['wave_receipt']))
    return result,bindings


def implementation_hashes():
    from inherited_circle_branch_inventory import implementation_hashes as parent_hashes
    from inherited_wave_pair_continuity import implementation_hashes as wave_hashes
    result=parent_hashes();result.update(wave_hashes());result[Path(__file__).name]=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inventory-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('wave inventory implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('wave inventory input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result,local=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'inventory.json').read_bytes() or sha(directory/'inventory.json')!=receipt['output_sha256'] or local!=receipt['local_inputs']:
        raise ValueError('wave inventory native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-inventory','wave-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_inventory=a.parent_inventory/'inventory.json',parent_receipt=a.parent_inventory/'inventory-receipt.json',
        wave_graph=a.wave_run/'graph_with_edges.json',wave_receipt=a.wave_run/'inherited-wave-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result,local=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'inventory.json';target.write_bytes(encode(result))
    (a.output/'inventory-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        local_inputs=local,implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(equipment=result['counts']['equipment'],ready_equipment=result['counts']['ready_for_mapping_comparison'],mapped_paths=0),flush=True)


if __name__=='__main__':main()
