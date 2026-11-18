"""Reapply complete-parent third-arm discovery with native topology-only proof."""
import argparse,collections,copy,csv,importlib,json,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from legacy_named_provider_inventory import require
from third_arm_crossview_paths import discover,prove,native_component_profiles

MODE='source_checked_third_arm_complete_crossview_batch_v1'

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as handle:return list(csv.DictReader(handle))

def inherit(original,records):
    result=copy.deepcopy(original);by={r['edge_id']:r for r in result['records']};new=[];added=[]
    require(len({r['mapping_id']for r in records})==len(records),'duplicate third-arm mapping')
    for proof in records:
        eid=proof['axis_edge_id'];row=by[eid]
        require(not row['has_existing_correspondence']and not row['correspondence_observations'],'new third arm competes with an old provider')
        require(row['classification']=='horizontal_only'and proof['physical_values_assigned']==0 and proof['DN_used_for_matching']is False and proof['human_accepted']is False,'third-arm scope or acceptance escaped')
        mapping=result['ordinary_junction_mappings'][str(proof['floor'])]
        for p,a in proof['ordinary_endpoint_pairs']:
            require(not p.startswith('MEMBER:')and not a.startswith('MEMBER:'),'member namespace enters ordinary map')
            require(not(p in mapping and mapping[p]!=a or a in mapping.values()and mapping.get(p)!=a),'third-arm endpoint conflicts with an old anchor')
            if p not in mapping:added.append(dict(floor=proof['floor'],plan_node=p,axis_node=a,mapping_id=proof['mapping_id']))
            mapping[p]=a
        row['has_existing_correspondence']=True
        row['correspondence_observations'].append(dict(provider='native_remaining_T_arm_topology',domain='ordinary_local_graph',mapping_id=proof['mapping_id'],floor=proof['floor'],plan_edges=proof['plan_edges'],grouped_axis_edges=proof['iso_edges'],attribute_adoption_allowed=proof['attribute_adoption_allowed'],source_detail_difference=proof['source_detail_difference']))
        new.append(eid)
    remaining=[]
    for old in original['remaining_horizontal_attributes']:
        row=copy.deepcopy(old)
        if row['edge_id']in new:
            require(row['next_scope']=='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path','third arm was not an unmatched horizontal scope')
            proof=next(p for p in records if p['axis_edge_id']==row['edge_id'])
            row.update(next_scope='known_third_arm_source_detail_difference'if proof['source_detail_difference']else'known_third_arm_topology_attribute_application_pending',existing_mapping_id=proof['mapping_id'],existing_plan_edges=proof['plan_edges'],correspondence_observations=copy.deepcopy(by[row['edge_id']]['correspondence_observations']))
        remaining.append(row)
    result.update(mode=MODE,remaining_horizontal_attributes=remaining,new_third_arm_axis_edges=sorted(new),new_third_arm_ordinary_anchors=added,
        third_arm_source_records=copy.deepcopy(records),all_old_provider_observations_preserved=True,all_old_pipe_attributes_and_components_preserved=True,
        new_correspondences_assigned=len(records),DN_or_length_values_assigned=0,source_graphs_mutated=False,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in by.values()),new_third_arm_correspondences=len(records),new_third_arm_ordinary_anchors=len(added),new_third_arm_source_detail_differences=sum(r['source_detail_difference']for r in records),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='all_old_providers_and_native_third_arm_topology_inherited',records=remaining,remaining_by_next_scope=result['counts']['horizontal_next_scopes']);result['current_horizontal_frontier']=frontier
    require(result['member_domain_observations']==original['member_domain_observations']and result['current_component_inventory']==original['current_component_inventory'],'third arm changed component or member scopes')
    return result

def checked_parent(manifest):
    spec=manifest['inputs']['parent_provider'];snapshot=manifest['inputs']['parent_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-third-arm-parent-')as temporary:
        output=Path(temporary)/'checked';command=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_legacy_named_provider.py'),'--skills-root',str(Path(snapshot['path']).parent/'skills'),'--snapshot',snapshot['path'],'--native-run',str(Path(spec['path']).parent),'--expected-sha256',spec['sha256'],'--output',str(output)]
        execution=subprocess.run(command,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf8')
        require(execution.returncode==0,'complete third-arm parent failed: '+execution.stderr[-5000:])
        raw=(output/'proof.json').read_bytes();meta=load(output/'execution.json')
        require(raw==Path(spec['path']).read_bytes()and meta['owner']=='legacy_named_provider_inventory'and meta['proof_sha256']==spec['sha256'],'third-arm parent identity differs')
        return json.loads(raw)

def compute(manifest,announce=lambda text:None):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():require(all(sha(paths[k])==s['sha256']for k,s in inputs.items()),'third-arm pinned input changed')
    checked();announce('Replaying every current provider in the original immutable legacy runtime');original=checked_parent(manifest)
    graphs_axis=load(paths['axis_graph']);components_axis=csvrows(paths['axis_components']);config=load(paths['current_T_source_config']);floors=[];records=[];native_profiles={}
    require(original['original_provider_inventory_inputs']['axis_graph']==inputs['axis_graph'],'third-arm axis parent differs')
    for floor in(1,2,3):
        f=str(floor);require(original['original_provider_inventory_inputs']['plan_graph_'+f]==inputs['plan_graph_'+f],'third-arm plan parent differs')
        graphs=dict(plan=load(paths['plan_graph_'+f]),iso=graphs_axis);components=dict(plan=csvrows(paths['plan_components_'+f]),iso=components_axis)
        candidates,held=discover(graphs,original,floor,components);qualified=[]
        if candidates:
            docs={};preflight={};hashes={v:dict(source_sha256=inputs[s]['sha256'],graph_sha256=inputs[g]['sha256'])for v,s,g in [('plan','plan_source_'+f,'plan_graph_'+f),('iso','axis_source','axis_graph')]}
            for v,s in [('plan','plan_source_'+f),('iso','axis_source')]:
                docs[v],preflight[v]=read_source(paths[s]);require(graphs[v]['metadata']['source_sha256']==inputs[s]['sha256'],'third-arm source and graph differ')
            profiles={v:native_component_profiles(docs[v],graphs[v],components[v],sorted({r[key]for r in candidates}),v)for v,key in [('plan','plan_edge_id'),('iso','axis_edge_id')]}
            for row in candidates:qualified.append(prove(row,graphs,docs,original,hashes,config,components,manifest['horizontal_directions_degrees'],profiles))
            native_profiles[f]=dict(profiles=profiles,source_preflight=preflight)
        floors.append(dict(floor=floor,qualified_records=qualified,held_candidates=held));records+=qualified
        announce('Floor '+f+': '+str(len(qualified))+' native topology scopes; '+str(len(held))+' held or already-qualified scopes')
    result=inherit(original,records);proof=dict(mode=MODE,inputs=inputs,floors=floors,records=records,native_component_profiles=native_profiles,
        complete_original_provider_replayed=True,current_native_T_and_path_scopes_replayed=True,
        all_old_provider_observations_preserved=True,source_graphs_mutated=False,physical_values_assigned=0,DN_used_for_matching=False,
        component_owners_or_counts_changed=False,whole_plan_topology_composed_or_proved=False,global_cycle_equivalence_claimed=False,
        counts=dict(new_topology_correspondences=len(records),new_ordinary_anchors=len(result['new_third_arm_ordinary_anchors']),source_detail_differences=sum(r['source_detail_difference']for r in records),held_or_already_known=sum(len(f['held_candidates'])for f in floors)),human_accepted=False,whole_goal_complete=False)
    checked();return proof,result

def implementation_hashes():
    root=Path(__file__).resolve().parents[2];names=('third_arm_crossview_paths','legacy_named_provider_inventory','native_ball_contact_reapplication','native_flange_contact_ownership','native_current_junction_reader','batch_native_path_coverage','attach_anchored_floor_main_attributes')
    return dict(entry=sha(__file__),fixed_parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_legacy_named_provider.py'),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh third-arm output');before=implementation_hashes();proof,provider=compute(load(manifest),lambda value:print(value,flush=True));require(before==implementation_hashes(),'third-arm implementation changed');output.mkdir(parents=True)
    outputs={'third-arm-batch.json':proof,'provider-inventory.json':provider,'horizontal-frontier.json':provider['current_horizontal_frontier']}
    for name,data in outputs.items():(output/name).write_bytes(encode(data))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256={name:sha(output/name)for name in outputs},human_accepted=False)))
    return proof,provider

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementation_hashes()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and all(sha(output/n)==h for n,h in receipt['output_sha256'].items()),'third-arm receipt changed')
    proof,provider=compute(load(receipt['manifest']['path']))
    for name,data in [('third-arm-batch.json',proof),('provider-inventory.json',provider),('horizontal-frontier.json',provider['current_horizontal_frontier'])]:require(encode(data)==(output/name).read_bytes(),'third-arm independent native replay differs')
    return proof,provider

def main():
    p=argparse.ArgumentParser()
    for k in('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if a.verify_output:proof,provider=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        proof,provider=produce(a.manifest,a.output)
    print(dict(proof['counts'],complete_correspondence_edges=provider['counts']['existing_correspondence_edges']),flush=True)

if __name__=='__main__':main()
