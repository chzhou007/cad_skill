"""Expand independently proved main Ts into unique native drawing branches.

Both local views stay immutable. Boundary/port correspondence is drawing
context, not a remote equipment identity, connection or installed whole length.
"""
import argparse,copy,hashlib,importlib,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from crossview_equipment_branch_inventory import index_graph
from ordered_group_plan_lengths import verify_output as verify_ordered
from source_readability import read_source
from native_drawing_marker_ports import collect as marker_ports
from native_capped_branch_annotations import native
from native_line_path_evidence import LAYERS
from batch_native_path_coverage import collect as coverage
from native_plan_projection_lengths import unit_evidence,lengths
from match_source_checked_crossview_paths import selected_snapshot
MODE='native_ordered_anchor_drawing_branch_paths_v1'

def branch_snapshot(graph,ids):
    nodes,edges,_=index_graph(graph);selected=[edges[eid]for eid in ids]
    if all(e.get(k)is not None for e in selected for k in('start_node_id','end_node_id')):return selected_snapshot(graph,ids)
    nids={e[k]for e in selected for k in('start_node_id','end_node_id')if e.get(k)is not None};bids={e[k]for e in selected for k in('start_boundary_id','end_boundary_id')if e.get(k)is not None};boundaries={b['boundary_id']:b for b in graph.get('boundary_anchors',[])}
    if not bids<=set(boundaries):raise ValueError('typed branch boundary missing')
    return dict(snapshot_mode='source_nodes_and_non_node_boundaries_v1',edges=copy.deepcopy(selected),nodes=[copy.deepcopy(nodes[nid])for nid in sorted(nids)],boundaries=[copy.deepcopy(boundaries[bid])for bid in sorted(bids)])

def retained_boundary_geometry(doc,boundary,edge):
    """Re-read the existing expert boundary using its inherited geometry gate.

    The original converter allows .6 drawing units of glyph placement rounding.
    This does not reinterpret a non-node boundary as an explicitly capped port;
    the separate capped-caption reader intentionally has a different gate.
    """
    if boundary.get('kind')!='expert_non_node_source_boundary'or boundary.get('source_marker_kind')!='two_bar'or not boundary.get('expert_issue'):raise ValueError('independently replayed expert non-node boundary required')
    pipe=native(doc,boundary['source_pipe_handle'],'LINE');bars=[native(doc,h,'LINE')for h in boundary['source_marker_handles']];point=[boundary['x'],boundary['y']]
    if len(bars)!=2 or len(set(boundary['source_marker_handles']))!=2 or pipe.dxf.layer!=LAYERS[edge['system']]or pipe.dxf.handle not in edge['source_handles']or any(bar.dxf.layer!=boundary['source_marker_layer']for bar in bars):raise ValueError('retained boundary typed source differs')
    tip=min((pipe.dxf.start,pipe.dxf.end),key=lambda p:math.dist(point,list(p)[:2]));a,b=bars;aa,ab=a.dxf.start,a.dxf.end;ba,bb=b.dxf.start,b.dxf.end
    if (math.dist(point,list(tip)[:2])>.01 or abs(aa.y-ab.y)>.01 or abs(ba.y-bb.y)>.01
        or abs(abs(aa.x-ab.x)-boundary['source_marker_lengths'][0])>.2 or abs(abs(ba.x-bb.x)-boundary['source_marker_lengths'][1])>.2
        or abs((aa.x+ab.x-ba.x-bb.x)/2)>.1 or abs(abs(aa.y-ba.y)-boundary['source_marker_spacing'])>.2
        or math.hypot((aa.x+ab.x)/2-point[0],aa.y-point[1])>.6
        or [aa.z,ba.z]!=boundary['source_marker_z']or tip.z!=boundary['source_pipe_endpoint_z']):raise ValueError('retained expert boundary native geometry changed')
    return dict(source_pipe_handle=pipe.dxf.handle,source_pipe_XYZ=[list(pipe.dxf.start),list(pipe.dxf.end)],source_marker_handles=boundary['source_marker_handles'],source_marker_XYZ=[[list(bar.dxf.start),list(bar.dxf.end)]for bar in bars],
        previous_boundary_role_preserved=True,native_Z_used_as_physical_elevation=False,new_capped_or_remote_role_assigned=False,physical_length_mm=None)

def outward(graph,start,blocked,system,floor):
    nodes,edges,adj=index_graph(graph);node=nodes[start]
    if node['node_type']not in('tee','physical_junction')or node.get('floor')!=floor or node.get('review_required')is True or len(adj[start])!=3 or {e['system']for e in adj[start]}!={system}:raise ValueError('ordered main T is not an independently usable same-system junction')
    options=[e for e in adj[start]if e['edge_id']not in blocked]
    if len(options)!=1 or sum(e['edge_id']in blocked for e in adj[start])!=2:raise ValueError('ordered main T has no unique off-main branch')
    edge=options[0];route=[];at=start;visited={start}
    for _ in range(len(edges)+1):
        if edge['system']!=system or edge['edge_id']in blocked or edge['edge_id']in route:raise ValueError('branch leaves its source system or repeats the main')
        route.append(edge['edge_id']);side='end'if edge['start_node_id']==at else'start';at=edge.get(side+'_node_id')
        if at is None:
            boundary=edge.get(side+'_boundary_id')
            if not boundary:raise ValueError('drawing boundary identity missing')
            return dict(edges=route,terminal_kind='source_boundary',terminal_id=boundary,terminal_edge=edge['edge_id'],terminal_side=side)
        if at in visited:raise ValueError('branch has a cycle')
        visited.add(at);node=nodes[at]
        if node.get('floor')!=floor:raise ValueError('off-main source branch changes floors')
        if node['node_type']=='virtual_equipment'and node.get('subtype')=='external_system_interface':
            return dict(edges=route,terminal_kind='drawing_marker_interface',terminal_id=at,terminal_edge=edge['edge_id'],terminal_side=side)
        if node['node_type']in('tee','physical_junction','equipment','physical_equipment','virtual_equipment')or node.get('review_required')is True or len(adj[at])!=2:raise ValueError('branch reaches an unresolved junction or actual equipment')
        candidates=[e for e in adj[at]if e['edge_id']not in route]
        if len(candidates)!=1:raise ValueError('branch route is ambiguous')
        edge=candidates[0]
    raise ValueError('branch route did not terminate')

def discover(graphs,proof,parent_records):
    used={v:{eid for row in parent_records for eid in row[v+'_edges']}for v in graphs};pairs=[];pending=[];seen={v:set()for v in graphs}
    for group in proof['groups']:
        blocked={v:{row['plan_edge_id'if v=='plan'else'axis_edge_id']for row in group['records']}for v in graphs}
        for anchor in group['internal_main_junction_correspondence']:
            try:
                routes={v:outward(graphs[v],anchor['plan_node'if v=='plan'else'axis_node'],blocked[v],group['system'],group['floor'])for v in graphs}
                if routes['plan']['terminal_kind']!='source_boundary'or routes['iso']['terminal_kind']!='drawing_marker_interface':raise ValueError('different boundary roles need their own correspondence rule')
                for view in graphs:
                    if used[view].intersection(routes[view]['edges'])or seen[view].intersection(routes[view]['edges']):raise ValueError('branch overlaps an existing path writer')
                row=dict(mapping_id='OB-F'+str(group['floor'])+'-'+hashlib.sha256(encode(dict(system=group['system'],routes=routes))).hexdigest()[:12],floor=group['floor'],system=group['system'],parent_mapping_id=group['mapping_id'],main_anchor=copy.deepcopy(anchor),routes=routes,
                    source_scope='matched_drawn_branch_context_not_remote_endpoint_identity',physical_port_verified=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,human_accepted=False)
                for view in graphs:row[view+'_snapshot']=branch_snapshot(graphs[view],routes[view]['edges']);seen[view].update(routes[view]['edges'])
                pairs.append(row)
            except ValueError as exc:pending.append(dict(parent_mapping_id=group['mapping_id'],main_anchor=copy.deepcopy(anchor),reason=str(exc)))
    return pairs,pending

def qualified_local_DN(raw,DN,receipt_path,result_path,graphs,source_hashes,graph_hashes):
    """Retain the exact previously qualified local DN; no fresh DN claim."""
    from rebuild_inherited_full_plan_DN import implementation_hashes as dn_hashes,MODE as DN_MODE
    receipt=load(receipt_path);roots=raw['sourceFullPlanBatchAttributes']['source_hashes']
    if receipt['mode']!=DN_MODE or sha(receipt_path)!=roots['DN_receipt']or sha(result_path)!=receipt['output_sha256']or receipt['implementation_sha256']!=dn_hashes():raise ValueError('qualified local DN owner or result changed')
    manifest=receipt['manifest']
    if sha(manifest['path'])!=manifest['sha256']:raise ValueError('qualified local DN manifest changed')
    rows={}
    for floor,graph in graphs.items():
        local=DN['floors'][floor]
        if local['graph_sha256']!=graph_hashes[floor]or local['source_sha256']!=source_hashes[floor]or roots['plan_graphs'][floor]!=graph_hashes[floor]or roots['plan_sources'][floor]!=source_hashes[floor]:raise ValueError('qualified local DN source scope differs')
        rows[floor]={r['edge_id']:r for r in local['records']}
    return rows

def measure_branch(graph,path_coverage,row,units):
    return lengths(graph,path_coverage,dict(plan_edges=row['routes']['plan']['edges'],system=row['system']),units)

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def unchanged():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('ordered branch input changed')
    unchanged();ordered=verify_ordered(paths['ordered_proof'].parent);raw=load(paths['parent_graph']);axis=load(paths['axis_graph']);batch=load(paths['batch_result']);parent=load(paths['parent_manifest'])
    if ordered['native_axis_graph_sha256']!=sha(paths['axis_graph'])or ordered['axis_source_graph_sha256']!=sha(paths['parent_graph'])or parent['sourceHashes']['graph']!=sha(paths['parent_graph']):raise ValueError('ordered branch parent source identity differs')
    if parent['attributeValueContext']['ordered_group_plan_runs']['source_bindings']['length_proof']!=sha(paths['ordered_proof']):raise ValueError('qualified parent has no same ordered source proof')
    floors=sorted({str(g['floor'])for g in ordered['groups']});plans={f:load(paths['plan_graph_'+f])for f in floors}
    local_DN=qualified_local_DN(raw,load(paths['DN_result']),paths['DN_receipt'],paths['DN_result'],plans,{f:sha(paths['plan_source_'+f])for f in floors},{f:sha(paths['plan_graph_'+f])for f in floors})
    docs_axis,axis_preflight=read_source(paths['axis_source']);records=[];pending=[];preflight=dict(iso=axis_preflight);port_cache={};native_roots={}
    for floor,plan in plans.items():
        pdoc,preflight[floor]=read_source(paths['plan_source_'+floor]);graphs=dict(plan=plan,iso=axis);selected=dict(groups=[g for g in ordered['groups']if str(g['floor'])==floor]);parent_records=batch['floors'][floor]['records']
        candidates,unresolved=discover(graphs,selected,parent_records);pending.extend(unresolved);units=unit_evidence(pdoc,load(paths['unit_policy_'+floor]));boundaries={b['boundary_id']:b for b in plan.get('boundary_anchors',[])}
        for row in candidates:
            try:
                terminal=row['routes']['plan'];boundary=boundaries[terminal['terminal_id']];last=next(e for e in plan['edges']if e['edge_id']==terminal['terminal_edge'])
                if boundary['kind']!='expert_non_node_source_boundary'or boundary['source_pipe_handle']not in last['source_handles']or boundary['system']!=row['system']:raise ValueError('retained plan boundary role differs')
                cap=retained_boundary_geometry(pdoc,boundary,last)
                pc=coverage(pdoc,plan,terminal['edges'],sha(paths['plan_source_'+floor]),sha(paths['plan_graph_'+floor]))
                if any(s['status']!='single_source_line_covers'for edge in pc['edges']for s in edge['segments']):raise ValueError('plan branch lacks unique native pipe coverage')
                iso=row['routes']['iso'];nid=iso['terminal_id']
                if nid not in port_cache:port_cache[nid]=marker_ports(docs_axis,axis,nid,sha(paths['axis_source']),sha(paths['axis_graph']))
                ports=[p for p in port_cache[nid]['records']if p['edge_id']==iso['terminal_edge']and p['system']==row['system']]
                if len(ports)!=1:raise ValueError('axis drawing branch has no unique same-system existing port')
                axis_coverage=coverage(docs_axis,axis,iso['edges'],sha(paths['axis_source']),sha(paths['axis_graph']))
                for item in axis_coverage['edges']:
                    for segment in item['segments']:
                        if item['edge_id']==iso['terminal_edge']and segment['index']==ports[0]['display_segment_index']:continue
                        if segment['status']!='single_source_line_covers':raise ValueError('axis branch physical source segment is unverified')
                projection=measure_branch(plan,pc,row,units);DNrows=[copy.deepcopy(local_DN[floor][eid])for eid in terminal['edges']]
                if any(r['system']!=row['system']or r['scope_paths']!=next(e for e in plan['edges']if e['edge_id']==r['edge_id'])['attribute_paths']for r in DNrows):raise ValueError('retained local DN source paths differ')
                values={r['nominal_mm']for r in DNrows};value=next(iter(values))if len(values)==1 and None not in values else None
                group=next(g for g in ordered['groups']if g['mapping_id']==row['parent_mapping_id'])
                record=copy.deepcopy(row);record.update(plan_boundary=copy.deepcopy(boundary),plan_native_boundary_geometry=cap,plan_native_path_coverage=pc,
                    axis_drawing_port=copy.deepcopy(ports[0]),axis_native_path_coverage=axis_coverage,plan_horizontal_projection=projection,plan_drawn_nominal_mm=value,plan_DN_records=DNrows,
                    local_DN_evidence_status='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild',mapping_verified_independently_of_DN=True,
                    original_native_main_T_evidence={v:group['native_source_check'][v]['junctions'][row['main_anchor']['plan_node'if v=='plan'else'axis_node']]for v in graphs},
                    whole_horizontal_plan_route_mm=None,circle_radius_added_to_metric=False,axis_marker_centre_span_added_to_metric=False,remote_equipment_identity_inferred=False)
                records.append(record)
            except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],main_anchor=row['main_anchor'],reason=str(exc)))
    unchanged()
    return dict(mode=MODE,records=records,pending=pending,source_preflight=preflight,source_hashes={k:sha(v)for k,v in paths.items()},
        native_marker_context=port_cache,counts=dict(derived_main_anchors=sum(len(g['internal_main_junction_correspondence'])for g in ordered['groups']),branch_contexts=len(records),pending=len(pending)),
        original_local_graphs_mutated=False,original_axis_graph_mutated=False,physical_ports_created=0,remote_connections_added=0,whole_axis_DN_assigned=0,physical_whole_edge_lengths_assigned=0,
        old_local_DN_qualified_retention=True,fresh_global_DN_rebuild_performed=False,anchor_feedback_into_its_own_parent=False,human_accepted=False)

def implementation_hashes():
    names=('ordered_group_plan_lengths','native_drawing_marker_ports','native_capped_branch_annotations','batch_native_path_coverage','native_plan_projection_lengths','native_path_coverage_audit','source_readability')
    return dict({name:sha(importlib.import_module(name).__file__)for name in names},entry=sha(__file__))
def produce(manifest_path,output):
    if Path(output).exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest_path))
    if implementation_hashes()!=before:raise RuntimeError('ordered branch implementation changed during native job')
    Path(output).mkdir(parents=True);target=Path(output)/'ordered-branch-paths.json';target.write_bytes(encode(result))
    (Path(output)/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=before,output_sha256=sha(target))))
    return result
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');target=output/'ordered-branch-paths.json';m=receipt['manifest']
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('ordered branch receipt or implementation changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('ordered branch native independent replay differs')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification cannot override inputs')
            result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
