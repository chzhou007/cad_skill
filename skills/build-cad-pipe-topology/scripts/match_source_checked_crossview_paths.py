"""Match source-checked branches with independent main-order corroboration.

This is technical correspondence, not an expert reply, installed length,
diameter assignment, whole-drawing acceptance or a local topology repair.
"""
import argparse,collections,copy,itertools,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from crossview_equipment_branch_inventory import verify_output as verify_inventory,index_graph
from native_path_coverage_audit import audit as audit_paths
from source_readability import read_source
from native_line_path_evidence import _on,LAYERS


def native_main_corridor(doc,graph,taps,system,floor):
    """Scope this correspondence to an explicit native LINE, allowing rings
    elsewhere in the network without selecting an arbitrary shortest route.
    """
    nodes,_,_=index_graph(graph);points=[[nodes[nid]['x'],nodes[nid]['y']] for nid in taps.values()]
    lines=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer!=LAYERS[system]:continue
        a=[line.dxf.start.x,line.dxf.start.y];b=[line.dxf.end.x,line.dxf.end.y]
        if all(_on(point,a,b,.05) for point in points):lines.append((line,a,b))
    if len(lines)!=1:raise ValueError('selected main anchors lack one unique native LINE corridor')
    line,a,b=lines[0];edges=[]
    for e in graph['edges']:
        paths=e.get('attribute_paths',[])
        if (e.get('system')==system and len(paths)==1 and len(paths[0])>=2
            and all(_on(point,a,b,.05) for point in paths[0])):edges.append(e)
    return dict(nodes=graph['nodes'],edges=edges),dict(source_line_handle=line.dxf.handle,source_layer=line.dxf.layer,
        source_start=list(line.dxf.start),source_end=list(line.dxf.end),selected_anchor_points=points,
        scope='native LINE corridor only; alternate network routes outside it are not asserted unique')


def bridge_main_path(graph,start,end,system,floor):
    """Parallel edges and cycles cannot masquerade as a unique main route."""
    nodes,edges,_=index_graph(graph);adj=collections.defaultdict(list)
    allowed={nid for nid,n in nodes.items() if n.get('node_type') in ('tee','physical_junction') and n.get('floor')==floor and n.get('review_required') is not True}
    if start==end or not {start,end}<=allowed:raise ValueError('main anchors missing, shared or unresolved')
    for eid,e in edges.items():
        a,b=e['start_node_id'],e['end_node_id']
        if e.get('system')==system and {a,b}<=allowed:adj[a].append((b,eid));adj[b].append((a,eid))
    depth={};low={};bridges=set()
    def visit(n,parent_edge=None):
        depth[n]=low[n]=len(depth)
        for peer,eid in adj[n]:
            if eid==parent_edge:continue
            if peer not in depth:
                visit(peer,eid);low[n]=min(low[n],low[peer])
                if low[peer]>depth[n]:bridges.add(eid)
            else:low[n]=min(low[n],depth[peer])
    visit(start);queue=collections.deque([(start,[],[start])]);seen={start}
    while queue:
        n,path,visited=queue.popleft()
        if n==end:return dict(edges=path,nodes=visited)
        for peer,eid in adj[n]:
            if eid in bridges and peer not in seen:seen.add(peer);queue.append((peer,path+[eid],visited+[peer]))
    raise ValueError('main route is disconnected, cyclic, parallel or outside the proved floor')


def mutual_main_paths(graphs,taps,system,floor):
    equipment=sorted(taps['plan'])
    if len(equipment)<3 or set(equipment)!=set(taps['iso']):raise ValueError('at least three common equipment anchors required')
    if any(len(set(taps[v].values()))!=len(equipment) for v in graphs):raise ValueError('equipment anchors collapse onto one T')
    by_view={v:{nid:did for did,nid in taps[v].items()} for v in graphs};pairs=[]
    for a,b in itertools.combinations(equipment,2):
        routes={v:bridge_main_path(graphs[v],taps[v][a],taps[v][b],system,floor) for v in graphs}
        order={v:[by_view[v][nid] for nid in routes[v]['nodes'] if nid in by_view[v]] for v in graphs}
        if order['plan']!=order['iso']:raise ValueError('same equipment names have different native main branch order')
        pairs.append(dict(equipment_order=order['plan'],routes=routes))
    adjacent=[r for r in pairs if len(r['equipment_order'])==2]
    if len(adjacent)!=len(equipment)-1 or max(len(r['equipment_order']) for r in pairs)!=len(equipment):raise ValueError('selected anchors do not form one mutually corroborated chain')
    for v in graphs:
        ids=[eid for pair in adjacent for eid in pair['routes'][v]['edges']]
        if len(ids)!=len(set(ids)):raise ValueError('adjacent main paths overlap')
    return dict(system=system,floor=floor,pairwise_order_checks=pairs,adjacent=adjacent)


def selected_snapshot(graph,eids):
    nodes,edges,_=index_graph(graph);nids={nid for eid in eids for nid in (edges[eid]['start_node_id'],edges[eid]['end_node_id'])}
    return dict(edges=[copy.deepcopy(edges[eid]) for eid in eids],nodes=[copy.deepcopy(nodes[nid]) for nid in sorted(nids)])


def build(paths,policy):
    for key in ('inventory','inventory_receipt','plan_source','iso_source','plan_graph','iso_graph'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('stale source correspondence input '+key)
    folder=Path(paths['inventory']).resolve().parent
    if Path(paths['inventory_receipt']).resolve()!=folder/'inventory-receipt.json' or Path(paths['inventory']).resolve()!=folder/'inventory.json':raise ValueError('inventory paths not canonical')
    receipt=load(paths['inventory_receipt'])
    for key in ('plan_source','iso_source','plan_graph','iso_graph'):
        if receipt['inputs'][key]['sha256']!=sha(paths[key]):raise ValueError('mapping and inventory scope differ '+key)
    inventory=verify_inventory(folder);selected=policy.get('equipment_ids',[]);floor=policy.get('floor')
    if not isinstance(selected,list) or len(selected)<3 or len(selected)!=len(set(selected)) or isinstance(floor,bool) or not isinstance(floor,int):raise ValueError('explicit multi-equipment floor scope required')
    by={r['equipment_id']:r for r in inventory['records']}
    if any(did not in by or not by[did]['ready_for_mapping_comparison'] or by[did]['floor']!=floor for did in selected):raise ValueError('selected local branches have not passed independent native checks')
    graphs={v:load(paths[v+'_graph']) for v in ('plan','iso')};docs={v:read_source(paths[v+'_source'])[0] for v in graphs}
    records=[];main_checks={}
    for system in ('supply','return'):
        taps={v:{did:by[did]['views'][v]['services'][system]['trace']['tee'] for did in selected} for v in graphs}
        corridors={v:native_main_corridor(docs[v],graphs[v],taps[v],system,floor) for v in graphs}
        main_checks[system]=mutual_main_paths({v:corridors[v][0] for v in graphs},taps,system,floor)
        main_checks[system]['native_corridors']={v:corridors[v][1] for v in graphs}
        for did in selected:
            branches={v:by[did]['views'][v]['services'][system]['trace']['edges'] for v in graphs}
            records.append(dict(mapping_id=f'SC-{len(records)+1:04d}',kind='equipment_branch',equipment_id=did,system=system,floor=floor,
                plan_edges=branches['plan'],iso_edges=branches['iso'],plan_start=taps['plan'][did],iso_start=taps['iso'][did],
                plan_end=did,iso_end=did,local_evidence={v:by[did]['views'][v]['services'][system] for v in graphs}))
        for pair in main_checks[system]['adjacent']:
            a,b=pair['equipment_order'];routes=pair['routes']
            records.append(dict(mapping_id=f'SC-{len(records)+1:04d}',kind='main_between_equipment_branches',endpoint_equipment_ids=[a,b],system=system,floor=floor,
                plan_edges=routes['plan']['edges'],iso_edges=routes['iso']['edges'],plan_start=taps['plan'][a],plan_end=taps['plan'][b],iso_start=taps['iso'][a],iso_end=taps['iso'][b]))
    # Main geometry is checked independently, not inferred from branch labels.
    coverage={}
    for view in graphs:
        ids=[eid for record in records for eid in record[view+'_edges']]
        if len(ids)!=len(set(ids)):raise ValueError('source correspondence double counts a local edge')
        main_ids=[eid for record in records if record['kind']=='main_between_equipment_branches' for eid in record[view+'_edges']]
        audited=audit_paths(docs[view],graphs[view],dict(source_sha256=sha(paths[view+'_source']),graph_sha256=sha(paths[view+'_graph']),edges=main_ids),sha(paths[view+'_source']),sha(paths[view+'_graph']))
        if any(s['status']!='single_source_line_covers' for e in audited['edges'] for s in e['segments']):raise ValueError('main correspondence lacks unique native LINE coverage')
        coverage[view]=audited
    for record in records:
        record.update(status='source_checked_mutually_correlated_path_not_human_accepted',decision_basis='native_local_branches_and_same_system_main_order',physical_ports_verified=False,human_accepted=False,
            plan_snapshot=selected_snapshot(graphs['plan'],record['plan_edges']),iso_snapshot=selected_snapshot(graphs['iso'],record['iso_edges']))
    return dict(status='source_checked_path_correspondence_attributes_pending',plan_graph_sha256=sha(paths['plan_graph']),iso_graph_sha256=sha(paths['iso_graph']),
        source_sha256={v:sha(paths[v+'_source']) for v in graphs},records=records,equipment_scope=selected,floor=floor,
        evidence=dict(main_topology=main_checks,main_coverage=coverage,inventory_sha256=sha(paths['inventory'])),
        local_graphs_mutated=False,expert_confirmation_claimed=False,human_accepted=False,hil_ready=False,
        limitations=['Correspondence is scoped technical source proof, not an expert answer or whole-graph acceptance.','Physical ports, omitted connectors, DN scope and installed lengths remain independently unresolved.'])


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('native_confirmed_equipment_pair_circle_evidence.py','match_source_checked_crossview_paths.py','crossview_equipment_branch_inventory.py','native_path_coverage_audit.py','source_readability.py')}


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('stale source correspondence implementation')
    for spec in receipt['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('source correspondence input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=build(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('source correspondence replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory','inventory-receipt','plan-source','iso-source','plan-graph','iso-graph','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();paths={key:getattr(args,key) for key in ('inventory','inventory_receipt','plan_source','iso_source','plan_graph','iso_graph','policy')}
    if args.output.exists():raise FileExistsError(args.output)
    result=build(paths,load(args.policy));args.output.mkdir(parents=True);(args.output/'mapping.json').write_bytes(encode(result))
    receipt=dict(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},output_sha256=sha(args.output/'mapping.json'),implementation_sha256=implementation_hashes(),human_accepted=False)
    (args.output/'source-mapping-receipt.json').write_bytes(encode(receipt));print(json.dumps(dict(mapped_paths=len(result['records']),equipment=len(result['equipment_scope']),expert_confirmation_claimed=False,human_accepted=False)))

if __name__=='__main__':main()
