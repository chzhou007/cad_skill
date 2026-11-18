"""Reconstruct all inherited external member corridors with ordinary anchors."""
import argparse,collections,copy,csv,importlib,json,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require
from source_readability import read_source
from member_external_anchored_routes import MODE,discover,prove


def checked_parent(manifest):
    spec=manifest['inputs']['provider'];snap=manifest['inputs']['provider_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-member-external-parent-')as temporary:
        output=Path(temporary)/'checked'
        command=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_third_arm_provider.py'),'--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],'--native-run',str(Path(spec['path']).parent),'--expected-sha256',spec['sha256'],'--output',str(output)]
        process=subprocess.run(command,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf8')
        require(process.returncode==0,'full original provider replay failed: '+process.stderr[-5000:])
        raw=(output/'proof.json').read_bytes();meta=load(output/'execution.json')
        require(raw==Path(spec['path']).read_bytes()and meta['owner']=='third_arm_crossview_batch'and meta['proof_sha256']==spec['sha256'],'original provider protocol differs')
        return json.loads(raw)


def inherit(original,records,parent,plan):
    result=copy.deepcopy(original);by={r['edge_id']:r for r in result['records']};new=[];ordinary=[];members=[];local=copy.deepcopy(parent['member_local_graph']);node_ids={n['node_id']for n in local['nodes']};pn={n['node_id']:n for n in plan['nodes']}
    require(len({r['axis_edge_id']for r in records})==len(records),'duplicate external route writer')
    for record in records:
        eid=record['axis_edge_id'];row=by[eid];f=str(record['floor']);mapping=result['ordinary_junction_mappings'][f]
        require(not row['has_existing_correspondence']and not row['correspondence_observations'],'new external route competes with old provider')
        require(record['physical_values_assigned']==0 and record['attribute_adoption_allowed']is False and record['human_accepted']is False,'external topology writer changes values or acceptance')
        external=record['kind']=='member_to_ordinary_external_route'
        if external:
            pairs=[[record['plan_remote'],record['axis_remote']]];plan_edges=[record['plan_member_edge_id']];domain='member_external_interface_path'
            require(row['classification']=='mixed_horizontal_vertical','external mixed corridor requires separate segment ownership')
            nid=record['plan_remote']
            if nid not in node_ids:local['nodes'].append(copy.deepcopy(pn[nid]));node_ids.add(nid)
            local['edges'].append(dict(edge_id=record['plan_member_edge_id'],start_node_id=record['member_node_id'],end_node_id=nid,system=record['system'],floor_start=record['floor'],floor_end=record['floor'],attribute_paths=copy.deepcopy(record['plan_attribute_paths']),source_parent_plan_edge=record['plan_source_edge_id'],source_mapping_id=record['mapping_id'],path_domain='mixed_axis_route_separate_source_owners',installed_whole_length_mm=None,whole_edge_DN_mm=None))
            members.append(dict(provider='member_external_anchored_routes',axis_edge_id=eid,member_edge_id=record['plan_member_edge_id'],anchors=dict(member_node_id=record['member_node_id'],plan_remote=nid,axis_remote=record['axis_remote'])))
        else:
            require(record['kind']=='ordinary_anchored_neighbor'and row['classification']=='horizontal_only','ordinary adjacent route is not purely horizontal')
            pairs=record['ordinary_endpoint_pairs'];plan_edges=[record['plan_edge_id']];domain='ordinary_local_graph'
        for p,a in pairs:
            require(not p.startswith('MEMBER:')and not a.startswith('MEMBER:'),'member node cannot become ordinary anchor')
            require(not(p in mapping and mapping[p]!=a or a in mapping.values()and mapping.get(p)!=a),'external remote anchor conflicts')
            if p not in mapping:ordinary.append(dict(floor=record['floor'],plan_node=p,axis_node=a,mapping_id=record['mapping_id']))
            mapping[p]=a
        observation=dict(provider='member_external_anchored_routes',domain=domain,mapping_id=record['mapping_id'],floor=record['floor'],plan_edges=plan_edges,grouped_axis_edges=[eid],attribute_adoption_allowed=False)
        if external:observation['source_plan_edges']=[record['plan_source_edge_id']]
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(observation);new.append(eid)
    remaining=[]
    for old in original['remaining_horizontal_attributes']:
        row=copy.deepcopy(old)
        if row['edge_id']in new:
            record=next(r for r in records if r['axis_edge_id']==row['edge_id']);require(record['kind']=='ordinary_anchored_neighbor','mixed route enters horizontal frontier')
            row.update(next_scope='known_member_external_adjacent_native_attributes_pending',existing_mapping_id=record['mapping_id'],existing_plan_edges=[record['plan_edge_id']],correspondence_observations=copy.deepcopy(by[row['edge_id']]['correspondence_observations']))
        remaining.append(row)
    local['external_ports']=[p for p in local.get('external_ports',[])if p['axis_edge_id']not in new]
    result.update(mode=MODE,records=list(by.values()),remaining_horizontal_attributes=remaining,member_domain_observations=copy.deepcopy(original['member_domain_observations'])+members,
        new_member_external_records=copy.deepcopy(records),new_member_external_axis_edges=sorted(new),new_member_external_ordinary_anchors=ordinary,
        all_old_provider_observations_preserved=True,DN_or_length_values_assigned=0,source_graphs_mutated=False,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in by.values()),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)),new_member_external_correspondences=len(new))
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='inherited_provider_with_source_checked_external_member_routes',records=remaining,remaining_by_next_scope=result['counts']['horizontal_next_scopes']);result['current_horizontal_frontier']=frontier
    require(result['current_component_inventory']==original['current_component_inventory'],'external routing changed component inventory')
    return result,local


def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():require(all(sha(paths[k])==v['sha256']for k,v in inputs.items()),'pinned external route input changed')
    checked();announce('Replaying complete original provider and all its native dependencies');original=checked_parent(manifest)
    parent=load(paths['member_bridges']);interfaces=load(paths['member_interfaces']);vm=load(paths['viewer_manifest'])
    require(vm['sourceHashes']['compound_member_bridge_proof']==inputs['member_bridges']['sha256']and vm['sourceHashes']['compound_member_interface_proof']==inputs['member_interfaces']['sha256'],'member route model is not the actual published member source')
    for key in('plan_source','axis_source','plan_graph','axis_graph'):require(parent['source_hashes'][key]==inputs[key]['sha256']and interfaces['source_hashes'][key]==inputs[key]['sha256'],'member model has different native input '+key)
    require(original['original_provider_inventory_inputs']['axis_graph']==inputs['axis_graph']and original['original_provider_inventory_inputs']['plan_graph_'+str(manifest['floor'])]==inputs['plan_graph'],'external graph does not belong to complete provider')
    graphs={v:load(paths[v+'_graph'])for v in('plan','axis')};rows,held=discover(graphs['plan'],graphs['axis'],parent,interfaces,original,manifest['floor']);announce(str(len(rows))+' independently bounded external candidates; '+str(len(held))+' held')
    docs={};preflight={}
    for v in graphs:
        docs[v],preflight[v]=read_source(paths[v+'_source']);require(graphs[v]['metadata']['source_sha256']==inputs[v+'_source']['sha256'],'external graph/source mismatch')
    components={}
    for v in graphs:
        with paths[v+'_components'].open(encoding='utf-8-sig',newline='')as handle:components[v]=list(csv.DictReader(handle))
    records,profiles=prove(rows,graphs,docs,original,inputs,load(paths['current_T_source_config']),components,manifest['horizontal_directions_degrees'])
    provider,local=inherit(original,records,parent,graphs['plan']);checked()
    proof=dict(mode=MODE,inputs=inputs,records=records,held=held,native_component_profiles=profiles,source_preflight=preflight,complete_current_provider_natively_replayed=True,
        complete_external_port_cohort_screened=True,new_native_routes_and_junctions_replayed=True,all_old_provider_observations_preserved=True,
        source_graphs_mutated=False,component_owners_changed=False,physical_values_assigned=0,DN_used_for_mapping=False,global_plan_topology_complete=False,human_accepted=False,
        counts=dict(screened_external_ports=len(rows)+len(held),qualified_external_routes=len(rows),qualified_ordinary_neighbors=sum(r['kind']=='ordinary_anchored_neighbor'for r in records),new_correspondences=len(records),new_ordinary_anchors=len(provider['new_member_external_ordinary_anchors']),held_external_ports=len(held)))
    return proof,provider,local


def implementations():
    root=Path(__file__).resolve().parents[2];names=('member_external_anchored_routes','third_arm_crossview_paths','native_line_path_evidence','source_readability','batch_native_path_coverage','native_current_junction_reader','crossview_equipment_branch_inventory','native_ball_contact_reapplication','native_flange_contact_ownership','legacy_named_provider_inventory','attach_anchored_floor_main_attributes')
    return dict(entry=sha(__file__),parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_third_arm_provider.py'),**{name:sha(importlib.import_module(name).__file__)for name in names})


def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh external route output');before=implementations();proof,provider,local=compute(load(manifest),lambda value:print(value,flush=True));require(before==implementations(),'external route implementation changed during run');output.mkdir(parents=True)
    values={'external-member-routes.json':proof,'provider-inventory.json':provider,'member-local-graph.json':local,'horizontal-frontier.json':provider['current_horizontal_frontier']}
    for name,value in values.items():(output/name).write_bytes(encode(value))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256={name:sha(output/name)for name in values},human_accepted=False)))
    return proof,provider,local


def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and all(sha(output/name)==value for name,value in receipt['output_sha256'].items()),'external route receipt changed')
    proof,provider,local=compute(load(receipt['manifest']['path']))
    for name,value in [('external-member-routes.json',proof),('provider-inventory.json',provider),('member-local-graph.json',local),('horizontal-frontier.json',provider['current_horizontal_frontier'])]:require(encode(value)==(output/name).read_bytes(),'independent native external route replay differs')
    return proof,provider,local


def main():
    parser=argparse.ArgumentParser()
    for key in('manifest','output','verify-output'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.verify_output:proof,_,_=verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
        proof,_,_=produce(args.manifest,args.output)
    print(proof['counts'],flush=True)

if __name__=='__main__':main()
