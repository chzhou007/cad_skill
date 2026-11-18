"""Source-replayed floor main correspondence from independently owned services.

Joint colour refinement is deliberately conservative: unresolved symmetries,
parallel edges, missing Ts or source gaps cannot become a definite mapping.
Local graphs and historical correspondence receipts are never rewritten.
"""
import argparse,collections,copy,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,service_route,native_tee
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory,MODE as INVENTORY_MODE
from native_inline_joint_path_coverage import verify_output as verify_inline,implementation_hashes as inline_hashes
from native_path_coverage_audit import audit as audit_paths
from match_source_checked_crossview_paths import selected_snapshot

MODE='source_checked_anchored_floor_main_network_v1'


def match_structure(graphs,inventory,floor,equipment):
    if (set(graphs)!={'plan','iso'} or isinstance(floor,bool) or not isinstance(floor,int)
        or len(equipment)<3 or len(equipment)!=len(set(equipment))):raise ValueError('explicit independent multi-equipment floor scope required')
    by={r['equipment_id']:r for r in inventory['records']}
    if len(by)!=len(inventory['records']) or any(d not in by or by[d].get('floor')!=floor or by[d].get('ready_for_mapping_comparison') is not True for d in equipment):
        raise ValueError('selected equipment lacks complete native services')
    seeds={v:{} for v in graphs};anchors=[];networks={};main_edges={}
    for did in equipment:
        for system in ('supply','return'):
            anchor=dict(equipment_id=did,system=system)
            for view,graph in graphs.items():
                trace=service_route(graph,did,system);prior=by[did]['views'][view]['services'][system]
                if (trace!=prior['trace'] or trace.get('status')!='unique_graph_service_to_T' or len(trace['edges'])!=1
                    or prior.get('ready_for_mapping_comparison') is not True):raise ValueError('fresh native branch owner or route differs')
                nid=trace['tee']
                if nid in seeds[view]:raise ValueError('equipment service anchors collapse onto one T')
                seeds[view][nid]=did+'/'+system;anchor[view+'_T']=nid;anchor[view+'_branch_edges']=trace['edges']
            anchors.append(anchor)
    for view,graph in graphs.items():
        nodes,edges,adj=index_graph(graph)
        selected={nid:n for nid,n in nodes.items() if n.get('floor')==floor and n['node_type'] in ('tee','physical_junction')}
        if not selected or not set(seeds[view])<=set(selected):raise ValueError('native service T outside selected floor')
        net={};mains={}
        for nid in selected:
            systems={edge['system'] for edge in adj[nid]}
            if len(adj[nid])!=3 or len(systems)!=1 or not systems<={'supply','return'}:raise ValueError('floor network has an unqualified T or system conflict')
            net[nid]=dict(anchor=seeds[view].get(nid,''),system=next(iter(systems)),neighbours=[])
        for eid,edge in edges.items():
            a,b=edge['start_node_id'],edge['end_node_id']
            if a in selected and b in selected:
                if a==b:raise ValueError('self-loop in floor main network')
                net[a]['neighbours'].append((b,edge['system']));net[b]['neighbours'].append((a,edge['system']));mains[eid]=edge
        seen=set()
        for start in net:
            if start in seen:continue
            todo=[start];component=set()
            while todo:
                current=todo.pop()
                if current in component:continue
                component.add(current);todo.extend(peer for peer,_ in net[current]['neighbours'] if peer not in component)
            seen.update(component)
            anchored={net[nid]['anchor'].rsplit('/',1)[0] for nid in component if net[nid]['anchor']}
            if len(anchored)<3:raise ValueError('each independent floor main component needs three distinct equipment anchors')
        networks[view]=net;main_edges[view]=mains
    if len(networks['plan'])!=len(networks['iso']) or len(main_edges['plan'])!=len(main_edges['iso']):raise ValueError('unmatched full-floor T or main-edge counts')
    colours={v:{nid:(n['anchor'],n['system'],len(n['neighbours'])) for nid,n in net.items()} for v,net in networks.items()};count=0
    for iteration in range(2*len(networks['plan'])+1):
        signatures={v:{nid:(colours[v][nid],tuple(sorted((colours[v][peer],s) for peer,s in n['neighbours']))) for nid,n in net.items()} for v,net in networks.items()}
        ids={signature:i for i,signature in enumerate(sorted({s for d in signatures.values() for s in d.values()},key=repr))}
        colours={v:{nid:ids[s] for nid,s in d.items()} for v,d in signatures.items()}
        if len(ids)==count:break
        count=len(ids)
    else:raise ValueError('floor network refinement failed to stabilize')
    classes={v:collections.defaultdict(list) for v in graphs}
    for view,d in colours.items():
        for nid,colour in d.items():classes[view][colour].append(nid)
    if set(classes['plan'])!=set(classes['iso']) or any(len(nodes)!=1 for d in classes.values() for nodes in d.values()):
        raise ValueError('floor network is inconsistent or not uniquely resolved by independent anchors')
    node_map={nodes[0]:classes['iso'][colour][0] for colour,nodes in classes['plan'].items()};pairs=[];used=set()
    for eid,edge in sorted(main_edges['plan'].items()):
        a,b=node_map[edge['start_node_id']],node_map[edge['end_node_id']]
        matches=[e for e in main_edges['iso'].values() if {e['start_node_id'],e['end_node_id']}=={a,b} and e['system']==edge['system']]
        if len(matches)!=1 or matches[0]['edge_id'] in used:raise ValueError('parallel or missing native main-edge correspondence')
        used.add(matches[0]['edge_id']);pairs.append(dict(plan_edge=eid,iso_edge=matches[0]['edge_id'],system=edge['system'],
            plan_start=edge['start_node_id'],plan_end=edge['end_node_id'],iso_start=a,iso_end=b))
    if used!=set(main_edges['iso']):raise ValueError('unmatched axis main edge')
    return dict(floor=floor,node_mapping=node_map,anchors=anchors,pairs=pairs,refinement_iterations=iteration+1,
        unique_full_floor_T_network=True,physical_direction_inferred=False)


def historical_lineage(graphs,inventory,structure,policy,hashes,records):
    by={r['equipment_id']:r for r in inventory['records']};current={r['plan_edges'][0]:r for r in records};lineage=[];used={v:set() for v in graphs};groups=set()
    for spec in policy.get('previous_mappings',[]):
        mp=Path(spec['path']);group=spec['group_id']
        if group in groups or sha(mp)!=spec['sha256']:raise ValueError('historical mapping group repeated or changed')
        groups.add(group);prior=load(mp)
        if (prior.get('plan_graph_sha256')!=hashes['plan']['graph_sha256'] or prior.get('iso_graph_sha256')!=hashes['iso']['graph_sha256']
            or prior.get('source_sha256')!={v:h['source_sha256'] for v,h in hashes.items()} or prior.get('floor')!=structure['floor']):raise ValueError('historical mapping belongs to another local/source version')
        for row in prior['records']:
            for view in graphs:
                if selected_snapshot(graphs[view],row[view+'_edges'])!=row[view+'_snapshot']:raise ValueError('historical mapped path changed')
                if used[view].intersection(row[view+'_edges']):raise ValueError('historical scopes overlap')
                used[view].update(row[view+'_edges'])
            if row['kind']=='equipment_branch':
                did=row['equipment_id'];system=row['system']
                if did not in by or did not in policy['equipment_ids']:raise ValueError('historical branch outside current equipment scope')
                for view in graphs:
                    service=by[did]['views'][view]['services'][system]
                    if row[view+'_edges']!=service['trace']['edges'] or row[view+'_start']!=service['trace']['tee'] or row[view+'_end']!=did:
                        raise ValueError('historical equipment branch owner changed')
                current_id=None
            elif row['kind']=='main_between_equipment_branches':
                if len(row['plan_edges'])!=1:raise ValueError('historical multi-edge main needs separate reconciliation')
                new=current.get(row['plan_edges'][0])
                if (not new or new['system']!=row['system'] or new['iso_edges']!=row['iso_edges']
                    or structure['node_mapping'].get(row['plan_start'])!=row['iso_start'] or structure['node_mapping'].get(row['plan_end'])!=row['iso_end']):
                    raise ValueError('historical main correspondence differs from new full-network proof')
                current_id=new['mapping_id']
            else:raise ValueError('unsupported historical scope kind')
            lineage.append(dict(group_id=group,previous_mapping_id=row['mapping_id'],previous_mapping_sha256=spec['sha256'],
                kind=row['kind'],current_main_mapping_id=current_id,local_path_semantics_preserved=True,human_confirmation_transferred=False))
    return lineage


def protected_floor_attributes(path,spec,graphs,structure,lineage,records,hashes):
    if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or sha(path)!=spec['sha256'] or Path(path).resolve()!=Path(spec['path']).resolve():
        raise ValueError('explicit preserved axis attribute snapshot required')
    dataset=load(path)
    if dataset.get('provenance',{}).get('sha256')!=hashes['iso']['source_sha256']:raise ValueError('preserved attributes use another axis source')
    floor=structure['floor'];old={r['group_id']+'-'+r['previous_mapping_id']:r for r in lineage};seen=set();segments=[];known_mains=set()
    axis_edges=index_graph(graphs['iso'])[1];by_plan={r['plan_edges'][0]:r for r in records}
    for edge in dataset['edges']:
        attr=edge.get('cross_view_attributes',{})
        if attr.get('floor')==floor:
            key=attr.get('source_scope_mapping_id')
            if key not in old or key in seen or attr['source_hashes']['plan_graph']!=hashes['plan']['graph_sha256'] or attr['source_hashes']['local_iso_graph']!=hashes['iso']['graph_sha256']:
                raise ValueError('preserved floor branch/main attribute scope is missing, duplicated or stale')
            seen.add(key)
        for attr in edge.get('plan_segment_attributes',[]):
            if attr.get('floor')!=floor:continue
            if (attr.get('edge_id')!=edge['edge_id'] or structure['node_mapping'].get(attr.get('plan_network_T'))!=attr.get('axis_network_T')
                or len(attr.get('plan_edges',[]))!=1 or attr.get('physical_port_verified',False) is not False):
                raise ValueError('preserved named floor segment conflicts with current network')
            source_edge=axis_edges.get(edge['edge_id']);indices=attr['segment_indices'];points=attr['scope_points']
            if (not source_edge or not indices or indices!=list(range(indices[0],indices[-1]+1))
                or source_edge['attribute_paths'][attr['path_index']][indices[0]:indices[-1]+2]!=points):raise ValueError('preserved axis attribute segment changed')
            if attr.get('whole_local_edge'):
                mapped=by_plan.get(attr['plan_edges'][0])
                if not mapped or mapped['iso_edges']!=[edge['edge_id']]:raise ValueError('preserved complete named main differs from current network mapping')
                known_mains.add(mapped['mapping_id'])
            segments.append(copy.deepcopy(attr))
    if seen!=set(old):raise ValueError('published floor attribute scopes were lost')
    return dict(source_snapshot=dict(path=str(Path(path).resolve()),sha256=sha(path)),history_only_not_a_mapping_seed=True,
        old_group_attributes_preserved=len(seen),named_segment_snapshots=segments,named_main_mapping_ids=sorted(known_mains),
        attributes_rewritten=False,values_assigned=0,human_confirmation_transferred=False)


def compute(paths,policy):
    for key in ('inventory','inventory_receipt','plan_inline','plan_inline_receipt','iso_inline','iso_inline_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('floor main mapping dependency changed '+key)
    owner_hashes=implementation_hashes()
    folder=Path(paths['inventory']).resolve().parent;receipt=load(paths['inventory_receipt'])
    if (Path(paths['inventory']).resolve()!=folder/'inventory.json' or Path(paths['inventory_receipt']).resolve()!=folder/'inventory-receipt.json'
        or receipt.get('mode')!=INVENTORY_MODE):raise ValueError('complete replayable v2 native branch inventory required')
    prefix=policy.get('mapping_prefix','')
    if not re.fullmatch('[A-Z0-9-]+',prefix):raise ValueError('explicit unique mapping prefix required')
    inventory=verify_inventory(folder);local=copy.deepcopy(receipt['inputs']);graphs={};docs={};hashes={};inline={};T_proofs={};coverage={}
    for key,item in local.items():
        if sha(item['path'])!=item['sha256']:raise ValueError('local inventory dependency changed '+key)
    for view in ('plan','iso'):
        gp=Path(local[view+'_graph']['path']);sp=Path(local[view+'_source']['path'])
        graphs[view]=load(gp);docs[view],_=read_source(sp);hashes[view]=dict(source_sha256=sha(sp),graph_sha256=sha(gp))
        ip=Path(paths[view+'_inline']).resolve();ir=Path(paths[view+'_inline_receipt']).resolve()
        if ip.name!='inline-joint-coverage.json' or ir!=ip.with_name('inline-joint-coverage-receipt.json'):raise ValueError('noncanonical inline source evidence')
        proof=verify_inline(ip.parent)
        if proof['source_sha256']!=hashes[view]['source_sha256'] or proof['graph_sha256']!=hashes[view]['graph_sha256']:raise ValueError('inline path evidence belongs to another local/source version')
        inline[view]={r['edge_id']:r for r in proof['records']}
    structure=match_structure(graphs,inventory,policy.get('floor'),policy.get('equipment_ids',[]));records=[]
    for view in graphs:
        node_ids=sorted(structure['node_mapping'] if view=='plan' else structure['node_mapping'].values());T_proofs[view]={}
        for nid in node_ids:T_proofs[view][nid]=native_tee(docs[view],graphs[view],nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        coverage[view]={}
        for pair in structure['pairs']:
            eid=pair[view+'_edge']
            if eid in inline[view]:coverage[view][eid]=dict(mode='independently_replayed_native_inline_joint_paths',evidence_sha256=sha(paths[view+'_inline']),edge_id=eid)
            else:
                proof=audit_paths(docs[view],graphs[view],dict(hashes[view],edges=[eid]),hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
                if any(s['status']!='single_source_line_covers' for e in proof['edges'] for s in e['segments']):raise ValueError('floor main lacks native pipe or qualified inline source evidence '+view+'/'+eid)
                coverage[view][eid]=dict(mode='native_LINE_path_source_coverage',evidence=proof)
    for index,pair in enumerate(structure['pairs'],1):
        row=dict(mapping_id=prefix+'-MAIN-'+str(index).zfill(4),kind='anchored_same_floor_T_to_T_main',floor=structure['floor'],system=pair['system'],
            plan_edges=[pair['plan_edge']],iso_edges=[pair['iso_edge']],plan_start=pair['plan_start'],plan_end=pair['plan_end'],iso_start=pair['iso_start'],iso_end=pair['iso_end'],
            status='source_checked_anchored_floor_main_path_human_pending',physical_ports_verified=False,physical_length_mm=None,human_accepted=False)
        for view in graphs:row[view+'_snapshot']=selected_snapshot(graphs[view],row[view+'_edges'])
        records.append(row)
    lineage=historical_lineage(graphs,inventory,structure,policy,hashes,records)
    protected_spec=policy.get('preserved_axis_attributes');protected=None
    if protected_spec:
        protected=protected_floor_attributes(protected_spec['path'],protected_spec,graphs,structure,lineage,records,hashes)
    known={r['current_main_mapping_id'] for r in lineage if r['current_main_mapping_id'] is not None}
    if protected:known.update(protected['named_main_mapping_ids'])
    result=dict(mode=MODE,status='source_checked_full_floor_main_correspondence_attributes_pending',floor=structure['floor'],equipment_scope=policy['equipment_ids'],records=records,
        plan_graph_sha256=hashes['plan']['graph_sha256'],iso_graph_sha256=hashes['iso']['graph_sha256'],source_sha256={v:h['source_sha256'] for v,h in hashes.items()},
        evidence=dict(structure=structure,native_T_proofs=T_proofs,main_path_coverage=coverage,inventory_sha256=sha(paths['inventory']),
            inventory_receipt_sha256=sha(paths['inventory_receipt']),historical_scope_lineage=lineage,preserved_floor_attributes=protected),
        historical_main_paths=len(known),additional_main_paths=len(records)-len(known),
        local_graphs_mutated=False,expert_confirmation_claimed=False,physical_source_identity_resolved=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)
    for key in ('inventory','inventory_receipt','plan_inline','plan_inline_receipt','iso_inline','iso_inline_receipt'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('mapping input changed during source replay '+key)
    for key,item in local.items():
        if sha(item['path'])!=item['sha256']:raise ValueError('local input changed during floor mapping '+key)
    for spec in policy.get('previous_mappings',[]):
        if sha(spec['path'])!=spec['sha256']:raise ValueError('historical mapping changed during source replay')
    if protected_spec and sha(protected_spec['path'])!=protected_spec['sha256']:raise ValueError('preserved attributes changed during source replay')
    if implementation_hashes()!=owner_hashes:raise ValueError('mapping source implementation changed during replay')
    return result,local


def implementation_hashes():
    result=inline_hashes()
    for name in ('match_anchored_floor_main_network.py','crossview_equipment_branch_inventory_v2.py','crossview_equipment_branch_inventory.py','match_source_checked_crossview_paths.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('anchored floor main implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('anchored floor main input changed')
    paths={k:item['path'] for k,item in receipt['inputs'].items()};result,local=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256'] or local!=receipt['local_inputs']:raise ValueError('anchored floor main native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','plan-inline-run','iso-inline-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',
        plan_inline=a.plan_inline_run/'inline-joint-coverage.json',plan_inline_receipt=a.plan_inline_run/'inline-joint-coverage-receipt.json',
        iso_inline=a.iso_inline_run/'inline-joint-coverage.json',iso_inline_receipt=a.iso_inline_run/'inline-joint-coverage-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result,local=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        local_inputs=local,implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(equipment=len(result['equipment_scope']),native_Ts=len(result['evidence']['structure']['node_mapping']),main_paths=len(result['records'])),flush=True)
if __name__=='__main__':main()
