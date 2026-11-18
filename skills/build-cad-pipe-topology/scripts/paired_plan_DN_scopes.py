"""Read plan DN scopes through independently replayed paired-service topology."""
import argparse,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,native_tee
from match_paired_service_crossview_paths import verify_output as verify_mapping
from match_source_checked_crossview_paths import native_main_corridor,bridge_main_path
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from source_direct_dn_evidence import collect as strict_collect
from calibrated_direct_dn_evidence import collect as calibrated_collect
from source_checked_plan_path_coverage import audit as audit_paths

MODE='paired_service_plan_DN_scopes_v1'


def topology_contract(doc,graph,pair,source_hash,graph_hash,floor):
    nodes,edges,adj=index_graph(graph);equipment=pair['equipment_ids'];mains=[];branches=[];junctions={};excluded=set();corridors={}
    if len(equipment)!=2 or len(set(equipment))!=2 or set(pair['services'])!={'supply','return'}:raise ValueError('paired DN needs both complete services')
    for system,state in pair['services'].items():
        taps=state['taps']['plan']
        if set(taps)!=set(equipment):raise ValueError('paired DN equipment anchors differ')
        corridor,evidence=native_main_corridor(doc,graph,taps,system,floor)
        if evidence!=state['native_corridors']['plan']:raise ValueError('paired DN native through corridor changed')
        route=bridge_main_path(corridor,taps[equipment[0]],taps[equipment[1]],system,floor)
        if route!=state['routes']['plan']:raise ValueError('paired DN main route changed')
        corridors[system]=evidence;mains.extend(route['edges']);branch_at={}
        for did in equipment:
            ids=state['branches']['plan'][did]
            if len(ids)!=1:raise ValueError('paired DN equipment path requires separately normalized branch')
            edge=edges[ids[0]];nid=taps[did]
            if edge['system']!=system or {edge['start_node_id'],edge['end_node_id']}!={did,nid}:raise ValueError('paired DN branch ownership changed')
            branches.append(dict(edge_id=edge['edge_id'],tee=nid,equipment_id=did,system=system));branch_at[nid]=edge['edge_id']
        for nid in route['nodes']:
            node=nodes[nid]
            if node.get('floor')!=floor or node.get('review_required') is True or nid in junctions:raise ValueError('paired DN shared, wrong-floor or unresolved T')
            if len(adj[nid])!=3:raise ValueError('paired DN requires separately normalized degree-two main subdivision')
            proof=native_tee(doc,graph,nid,source_hash,graph_hash)
            rows=proof.get('junctions',[])
            if len(rows)!=1:raise ValueError('paired DN T needs its source-specific through-role reader')
            through={r['edge_id'] for r in rows[0]['source_rays'] if r.get('source_line_handle')==evidence['source_line_handle']}
            off={e['edge_id'] for e in adj[nid]}-through
            if len(through)!=2 or len(off)!=1 or not set(route['edges']).intersection(through):raise ValueError('paired DN native through roles ambiguous')
            if nid in branch_at:
                if off!={branch_at[nid]}:raise ValueError('equipment branch cannot redefine native through pipe')
            else:
                if not through<=set(route['edges']):raise ValueError('interior T main rays leave the selected native corridor')
                excluded.update(off)
            junctions[nid]=proof
    if len(set(mains))!=len(mains) or len({b['edge_id'] for b in branches})!=len(branches):raise ValueError('paired DN scopes overlap')
    return dict(main_edges=mains,branches=branches,junctions=junctions,verified_taps=sorted(junctions),
        branch_frontier_edges=sorted(excluded),native_through_corridors=corridors)


def compute(paths,policy):
    for key in ('source','graph','mapping','mapping_receipt','calibration_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('paired DN input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping']).resolve()!=folder/'mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':raise ValueError('noncanonical paired mapping')
    mapping=verify_mapping(folder);source_hash=sha(paths['source']);graph_hash=sha(paths['graph'])
    if mapping['plan_graph_sha256']!=graph_hash or mapping['source_sha256']['plan']!=source_hash:raise ValueError('paired DN source differs from correspondence')
    if not policy.get('expert_T_inheritance_rule'):raise ValueError('missing inherited expert T/DN rule')
    config=policy.get('groups',[]);by={g['pair_id']:g for g in config};pairs=mapping['evidence']['paired_services']
    if len(by)!=len(config) or set(by)!={p['pair_id'] for p in pairs} or any(set(g)-{'pair_id','seeds','line_F_frames'} for g in config):raise ValueError('explicit paired DN group scope differs')
    graph=load(paths['graph']);doc,preflight=read_source(paths['source']);contracts={p['pair_id']:topology_contract(doc,graph,p,source_hash,graph_hash,mapping['floor']) for p in pairs}
    ids=[eid for c in contracts.values() for eid in c['main_edges']+[b['edge_id'] for b in c['branches']]]
    if len(ids)!=len(set(ids)):raise ValueError('paired DN output edges overlap')
    texts,inventory=catalog(doc,graph,ids,source_hash,graph_hash);calibration=load(paths['calibration_policy']);allowed={s['text_handle']:s for s in calibration['selections']}
    def direct(doc,current,selection,sh,gh):
        selected=selection['selections']
        if all(s['text_handle'] in allowed for s in selected):
            if any(s!=allowed[s['text_handle']] for s in selected):raise ValueError('paired calibrated DN seed differs')
            return calibrated_collect(doc,current,dict(calibration,selections=selected),sh,gh)
        if any(s['text_handle'] in allowed for s in selected):
            # The inherited collectors need separate calls. Merge only after
            # each literal source binding has independently replayed.
            records=[]
            for spec in selected:records.extend(direct(doc,current,dict(selection,selections=[spec]),sh,gh)['observations'])
            return dict(observations=records)
        return strict_collect(doc,current,selection,sh,gh)
    component=None;component_strokes=()
    if policy.get('qualified_component_DN'):
        from qualified_inline_DN_evidence import collect
        component=collect(doc,graph,policy['qualified_component_DN'],source_hash,graph_hash)
        texts=[t for t in texts if t['handle'] not in set(component['consumed_DN_text_handles'])];component_strokes=component['consumed_leader_handles'];inventory['qualified_component_DN']=component
    results=[]
    for pair in pairs:
        pid=pair['pair_id'];contract=contracts[pid];settings=by[pid]
        group=dict(group_id=pid,floor=mapping['floor'],main_edges=contract['main_edges'],branches=contract['branches'],seeds=settings['seeds'],line_F_frames=settings.get('line_F_frames',[]))
        result=attribute_checked_scope(doc,graph,group,texts,source_hash,graph_hash,set(inventory['F_text_handles']),
            junctions=contract['junctions'],verified_taps=contract['verified_taps'],branch_frontier_edges=contract['branch_frontier_edges'],
            direct_collector=direct,path_auditor=audit_paths,verified_nonpipe_annotation_strokes=component_strokes)
        result['paired_topology_contract']=contract;results.append(result)
    return dict(mode=MODE,status='source_checked_plan_DN_scopes_human_pending',source_sha256=source_hash,graph_sha256=graph_hash,mapping_sha256=sha(paths['mapping']),
        source_preflight=preflight,source_annotation_inventory=inventory,groups=results,records=[r for g in results for r in g['records']],
        local_graph_mutated=False,scope='native_floor_plan_drawn_pipe_paths_only_not_unshown_drops_or_equipment_connectors',
        expert_rule=policy['expert_T_inheritance_rule'],physical_values_fused=False,human_accepted=False)


def implementation_hashes():
    from plan_calibrated_DN_scopes import implementation_hashes as inherited
    hashes=inherited()
    for name in ('paired_plan_DN_scopes.py','checked_plan_DN_scope_attributes.py','match_paired_service_crossview_paths.py','crossview_equipment_branch_inventory_v2.py','native_exploded_endpoint_evidence.py'):
        hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'plan-DN-scope-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('paired DN implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('paired DN input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'plan-DN-scopes.json').read_bytes() or sha(directory/'plan-DN-scopes.json')!=receipt['output_sha256']:raise ValueError('paired DN native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','mapping','mapping-receipt','calibration-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={k:getattr(a,k) for k in ('source','graph','mapping','mapping_receipt','calibration_policy','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'plan-DN-scopes.json').write_bytes(encode(result))
    (a.output/'plan-DN-scope-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'plan-DN-scopes.json'),human_accepted=False)))
    print(dict(records=len(result['records']),known_DN=sum(r['nominal_mm'] is not None for r in result['records']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
