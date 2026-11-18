"""Recompute DN scopes after native junction correspondence refinement.

An added link is through pipe at the target pair and a non-through branch at
the parent pair. Reuse the attribution kernel with only the target's verified
Ts: its annotation may seed the link, but cannot flow back into the parent.
"""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from paired_plan_DN_scopes import verify_output as verify_base_DN,implementation_hashes as base_DN_hashes
from refine_paired_service_path_correspondence import MODE as MAPPING_MODE,implementation_hashes as mapping_hashes,refine
from native_paired_junction_correspondence import collect as collect_junctions
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph
from native_path_coverage_audit import audit as audit_native_paths
from source_checked_plan_path_coverage import audit as audit_paths
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from source_direct_dn_evidence import collect as strict_collect
from calibrated_direct_dn_evidence import collect as calibrated_collect

MODE='paired_service_junction_refined_plan_DN_scopes_v1'


def extension_contracts(graph,base_DN,mapping):
    """Validate scope roles against already replayed mapping and DN contracts."""
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('local_graphs_mutated') is not False
        or mapping.get('physical_values_fused') is not False or mapping.get('human_accepted') is not False):
        raise ValueError('refined DN requires an unmodified, independently checked correspondence')
    groups={g['group_id']:g for g in base_DN['groups']}
    if len(groups)!=len(base_DN['groups']):raise ValueError('duplicate base DN group')
    nodes,edges,_=index_graph(graph);contracts={};promotions=[];claimed=set()
    witnesses={m['junction_mapping_id']:(row,m) for row in mapping['evidence']['native_junction_correspondence']['records'] for m in row['matches']}
    for record in mapping['records']:
        if record.get('decision_basis')!='native_offcorridor_branch_to_first_independently_checked_equipment_T':continue
        if len(record['plan_edges'])!=1 or len(record.get('junction_correspondence_ids',[]))!=1:
            raise ValueError('refined DN link needs a separately normalized single native edge')
        eid=record['plan_edges'][0];edge=edges[eid];origin=groups[record['parent_pair_id']];target=groups[record['target_pair_id']]
        key=record['junction_correspondence_ids'][0]
        if key not in witnesses:raise ValueError('link lacks its native branch-target witness')
        proof,match=witnesses[key];view=match['views']['plan'];system=record['system'];start=record['plan_start'];end=record['plan_end']
        if (proof.get('complete') is not True or proof['parent_pair_id']!=origin['group_id'] or proof['system']!=system
            or match['target_pair_id']!=target['group_id'] or match['target_equipment_id']!=record['target_equipment_id']
            or view['parent_node']!=start or view['route']['start']!=start or view['route']['end']!=end
            or view['route']['edges']!=[eid] or edge['system']!=system
            or {edge['start_node_id'],edge['end_node_id']}!={start,end}):raise ValueError('refined DN link identity differs')
        oc=origin['paired_topology_contract'];tc=target['paired_topology_contract']
        if (eid not in oc['branch_frontier_edges'] or start not in oc['verified_taps']
            or end not in tc['verified_taps'] or start in tc['verified_taps']
            or eid in tc['branch_frontier_edges']):raise ValueError('link through/branch direction cannot be established')
        if any(nodes[n].get('floor')!=mapping['floor'] or nodes[n].get('review_required') is True for n in (start,end)):
            raise ValueError('link endpoint is on another floor or remains unresolved')
        branch=[b for b in tc['branches'] if b['equipment_id']==match['target_equipment_id'] and b['system']==system]
        if len(branch)!=1 or branch[0]['tee']!=end:raise ValueError('link target equipment T differs')
        handle=tc['native_through_corridors'][system]['source_line_handle']
        rays=tc['junctions'][end].get('junctions',[])
        if len(rays)!=1 or eid not in {r['edge_id'] for r in rays[0]['source_rays'] if r.get('source_line_handle')==handle}:
            raise ValueError('link does not share the target native through LINE')
        if view['native_corridor']['source_line_handle']!=handle:raise ValueError('link corridor changed')
        coverage=view['coverage']['edges']
        if len(coverage)!=1 or coverage[0]['edge_id']!=eid or any(s['status']!='single_source_line_covers' for s in coverage[0]['segments']):
            raise ValueError('link has incomplete native source coverage')
        frontiers=[f for f in target['frontier_fragments'] if f['edge_id']==eid and f['selected_T']==end]
        paths=edge['attribute_paths']
        if (len(frontiers)!=1 or len(paths)!=1 or frontiers[0].get('whole_original_edge_value_assigned') is not False
            or frontiers[0]['annotation_point'] is not None
            or frontiers[0]['projected_source_path'] not in (paths[0],list(reversed(paths[0])))):
            raise ValueError('a partial annotation frontier cannot be promoted to a whole link')
        if eid in claimed or any(eid==r['edge_id'] for r in base_DN['records']):raise ValueError('refined DN link has another writer')
        claimed.add(eid);contract=contracts.setdefault(target['group_id'],copy.deepcopy(tc));contract['main_edges'].append(eid)
        contract.setdefault('propagation_stops_at_matched_parent_junctions',[]).append(start)
        promotions.append(dict(edge_id=eid,system=system,parent_pair_id=origin['group_id'],target_pair_id=target['group_id'],
            source_junction=start,target_through_junction=end,junction_correspondence_id=key,
            target_native_through_LINE=handle,parent_non_through_frontier_retained=True,
            whole_link_source_coverage_rechecked=True,physical_length_assigned=False))
    if not promotions:raise ValueError('refined mapping supplies no supported new link DN scope')
    for contract in contracts.values():
        if set(contract['propagation_stops_at_matched_parent_junctions'])&set(contract['verified_taps']):
            raise ValueError('parent DN boundary would be traversed')
    return contracts,promotions


def recompute_groups(doc,graph,base_DN,mapping,settings,texts,F_handles,direct_collector,component_strokes=()):
    contracts,promotions=extension_contracts(graph,base_DN,mapping);groups=[]
    sh=base_DN['source_sha256'];gh=base_DN['graph_sha256']
    for old in base_DN['groups']:
        pid=old['group_id']
        if pid not in contracts:groups.append(copy.deepcopy(old));continue
        contract=contracts[pid];configuration=settings[pid]
        group=dict(group_id=pid,floor=mapping['floor'],main_edges=contract['main_edges'],branches=contract['branches'],
            seeds=configuration['seeds'],line_F_frames=configuration.get('line_F_frames',[]))
        result=attribute_checked_scope(doc,graph,group,texts,sh,gh,F_handles,junctions=contract['junctions'],
            verified_taps=contract['verified_taps'],branch_frontier_edges=contract['branch_frontier_edges'],
            direct_collector=direct_collector,path_auditor=audit_paths,verified_nonpipe_annotation_strokes=component_strokes)
        result['paired_topology_contract']=contract;by={r['edge_id']:r for r in result['records']}
        if any(by.get(r['edge_id'])!=r for r in old['records']):raise ValueError('refined DN changed a previously checked pipe value or inheritance chain')
        groups.append(result)
    records=[r for g in groups for r in g['records']]
    if len({r['edge_id'] for r in records})!=len(records):raise ValueError('refined DN scopes overlap')
    return groups,promotions


def replay_refinement(paths,base_DN,base_receipt):
    """Reuse a fresh base DN replay's exact mapping, not an old success flag."""
    folder=Path(paths['mapping']).resolve().parent;receipt=load(paths['mapping_receipt'])
    if Path(paths['mapping']).resolve()!=folder/'mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':raise ValueError('noncanonical refined mapping')
    if receipt.get('mode')!=MAPPING_MODE or receipt['implementation_sha256']!=mapping_hashes():raise ValueError('refined correspondence implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('refined correspondence dependency changed')
    for dst,src in [('base_mapping','mapping'),('base_receipt','mapping_receipt')]:
        if receipt['inputs'][dst]!=base_receipt['inputs'][src]:raise ValueError('refinement and freshly replayed base DN use different correspondence inputs')
    if base_DN['mapping_sha256']!=receipt['inputs']['base_mapping']['sha256']:raise ValueError('refined DN base mapping differs')
    base=load(receipt['inputs']['base_mapping']['path']);mr=load(receipt['inputs']['base_receipt']['path'])
    graphs={v:load(mr['inputs'][v+'_graph']['path']) for v in ('plan','iso')}
    docs={v:read_source(mr['inputs'][v+'_source']['path'])[0] for v in graphs}
    hashes={v:dict(source_sha256=base['source_sha256'][v],graph_sha256=base[v+'_graph_sha256']) for v in graphs}
    proof=collect_junctions(docs,graphs,base,hashes);policy=load(receipt['inputs']['policy']['path'])
    for key in ('base_mapping','base_receipt'):
        if receipt['inputs'][key]['sha256']!=policy.get(key+'_sha256'):raise ValueError('refinement policy changed')
    result=refine(base,proof,graphs,policy['required_groups']);result['previous_mapping_sha256']=receipt['inputs']['base_mapping']['sha256']
    for view in graphs:
        ids=[eid for r in result['records'] if r['kind']!='equipment_branch' for eid in r[view+'_edges']]
        coverage=audit_native_paths(docs[view],graphs[view],dict(hashes[view],edges=ids),hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):raise ValueError('refined main native coverage changed')
        result['evidence'].setdefault('refined_main_coverage',{})[view]=coverage
    if encode(result)!=Path(paths['mapping']).read_bytes() or receipt['output_sha256']!=sha(paths['mapping']):raise ValueError('refined correspondence native replay differs')
    return result,docs,graphs


def compute(paths,policy):
    for key in ('base_DN','base_DN_receipt','mapping','mapping_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('refined DN input changed '+key)
    directory=Path(paths['base_DN']).resolve().parent
    if Path(paths['base_DN']).resolve()!=directory/'plan-DN-scopes.json' or Path(paths['base_DN_receipt']).resolve()!=directory/'plan-DN-scope-receipt.json':raise ValueError('noncanonical base DN evidence')
    base=verify_base_DN(directory);receipt=load(paths['base_DN_receipt'])
    mapping,docs,graphs=replay_refinement(paths,base,receipt);doc=docs['plan'];graph=graphs['plan']
    if mapping['source_sha256']['plan']!=base['source_sha256'] or mapping['plan_graph_sha256']!=base['graph_sha256']:raise ValueError('refined DN plan source or topology differs')
    contracts,_=extension_contracts(graph,base,mapping);oldpolicy=load(receipt['inputs']['policy']['path']);settings={g['pair_id']:g for g in oldpolicy['groups']}
    ids=sorted({r['edge_id'] for r in base['records']}|{eid for c in contracts.values() for eid in c['main_edges']})
    texts,inventory=catalog(doc,graph,ids,base['source_sha256'],base['graph_sha256'])
    calibration=load(receipt['inputs']['calibration_policy']['path']);allowed={s['text_handle']:s for s in calibration['selections']}
    def direct(doc,current,selection,sh,gh):
        selected=selection['selections']
        if selected and all(s['text_handle'] in allowed for s in selected):
            if any(s!=allowed[s['text_handle']] for s in selected):raise ValueError('refined calibrated DN seed differs')
            return calibrated_collect(doc,current,dict(calibration,selections=selected),sh,gh)
        if any(s['text_handle'] in allowed for s in selected):
            return dict(observations=[r for spec in selected for r in direct(doc,current,dict(selection,selections=[spec]),sh,gh)['observations']])
        return strict_collect(doc,current,selection,sh,gh)
    strokes=()
    if oldpolicy.get('qualified_component_DN'):
        from qualified_inline_DN_evidence import collect
        component=collect(doc,graph,oldpolicy['qualified_component_DN'],base['source_sha256'],base['graph_sha256'])
        texts=[t for t in texts if t['handle'] not in set(component['consumed_DN_text_handles'])];strokes=component['consumed_leader_handles'];inventory['qualified_component_DN']=component
    groups,promotions=recompute_groups(doc,graph,base,mapping,settings,texts,set(inventory['F_text_handles']),direct,strokes)
    result=copy.deepcopy(base);result.update(mode=MODE,status='source_checked_junction_refined_plan_DN_scopes_human_pending',
        mapping_sha256=sha(paths['mapping']),previous_DN_scope_sha256=sha(paths['base_DN']),groups=groups,records=[r for g in groups for r in g['records']],
        source_annotation_inventory=inventory,native_link_scope_extensions=promotions,
        previous_checked_records_preserved=True,local_graph_mutated=False,physical_values_fused=False,human_accepted=False)
    return result


def implementation_hashes():
    hashes=base_DN_hashes();hashes.update(mapping_hashes());hashes['refined_paired_plan_DN_scopes.py']=sha(__file__)
    return hashes


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'plan-DN-scope-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('refined DN implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('refined DN dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'plan-DN-scopes.json').read_bytes() or receipt['output_sha256']!=sha(directory/'plan-DN-scopes.json'):raise ValueError('refined DN native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('base-DN-run','mapping-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(base_DN=a.base_DN_run/'plan-DN-scopes.json',base_DN_receipt=a.base_DN_run/'plan-DN-scope-receipt.json',
        mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'plan-DN-scopes.json').write_bytes(encode(result))
    (a.output/'plan-DN-scope-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'plan-DN-scopes.json'),human_accepted=False)))
    print(dict(records=len(result['records']),known_DN=sum(r['nominal_mm'] is not None for r in result['records']),new_source_links=len(result['native_link_scope_extensions']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
