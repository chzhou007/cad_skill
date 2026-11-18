"""Source-replay unique cycle risers; keep unequal terminal arcs as differences."""
import argparse,copy,importlib,math,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from typed_cycle_riser_matching import discover
from source_readability import read_source
from crossview_equipment_branch_inventory import native_tee,index_graph
from native_line_path_evidence import LAYERS
from batch_native_path_coverage import collect as coverage
from anchor_bounded_main_paths import component_profiles
from rebuild_anchored_cycle_gate_batch import csv_rows,sha_bytes
from native_replay_session import verify_once
MODE='native_typed_cycle_riser_crossview_batch_v1'

def native_riser_circle(doc,graph,node_id,system):
    nodes,_,adj=index_graph(graph);n=nodes[node_id];circle=doc.entitydb.get(n.get('source_handle'))
    if n.get('subtype')!='out_of_plane_riser'or n.get('system')!=system or len(adj[node_id])!=1 or not circle or circle not in doc.modelspace()or circle.dxftype()!='CIRCLE'or circle.dxf.layer!=LAYERS[system]or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('native riser circle role differs')
    if not all(math.isfinite(v)for v in (*circle.dxf.center,circle.dxf.radius,n['x'],n['y']))or circle.dxf.radius<=0 or math.dist([n['x'],n['y']],list(circle.dxf.center)[:2])>.05:raise ValueError('native riser circle geometry differs')
    return dict(node_id=node_id,circle_handle=circle.dxf.handle,center=list(circle.dxf.center),radius=circle.dxf.radius,system=system,incident_edge=adj[node_id][0]['edge_id'])

def compute(manifest,announce=lambda s:None):
    from graph_first_provider_inventory import verify_output as verify_inventory
    from rebuild_anchored_cycle_gate_batch import verify_output as verify_cycles
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('typed cycle riser input changed')
    checked();announce('Replaying current complete graph-first providers and original cycle gate evidence')
    parent=verify_once(paths['inventory'].parent,verify_inventory);cycles=verify_once(paths['cycle_proof'].parent,verify_cycles)
    if encode(parent)!=paths['inventory'].read_bytes()or encode(cycles)!=paths['cycle_proof'].read_bytes():raise ValueError('current native provider or cycle replay differs')
    if parent['inputs']['cycle_proof']['sha256']!=sha(paths['cycle_proof']):raise ValueError('current inventory uses another cycle proof')
    for k in cycles['inputs']:
        if k=='inventory':continue
        if k not in paths or sha(paths[k])!=cycles['inputs'][k]['sha256']:raise ValueError('typed riser source ancestry differs '+k)
    axis=load(paths['axis_graph']);axis_doc,axis_readable=read_source(paths['axis_source']);axis_components=csv_rows(paths['axis_components']);routing=load(paths['routing']);routes={r['edge_id']:r for r in routing['edges']}
    if axis['metadata']['source_sha256']!=sha(paths['axis_source']):raise ValueError('axis source differs')
    old={r['edge_id']:r for r in parent['records']};floors={};all_records=[];all_maps={}
    for floor in(1,2,3):
        f=str(floor);plan=load(paths['plan_graph_'+f]);graphs=dict(plan=plan,iso=axis)
        discovery=discover(graphs,parent['ordinary_junction_mappings'][f],floor,cycles['floors'][f]['discovery']['groups'],routes)
        if not discovery['new_junction_mapping']:
            floors[f]=dict(discovery=discovery,new_junction_mapping={},records=[],pending=discovery['pending']);continue
        doc,readable=read_source(paths['plan_source_'+f]);docs=dict(plan=doc,iso=axis_doc)
        hashes={v:dict(source_sha256=sha(paths['plan_source_'+f]if v=='plan'else paths['axis_source']),graph_sha256=sha(paths['plan_graph_'+f]if v=='plan'else paths['axis_graph']))for v in graphs}
        if plan['metadata']['source_sha256']!=hashes['plan']['source_sha256']:raise ValueError('plan source differs')
        accepted={};ports=[];native_roles=[];pending=copy.deepcopy(discovery['pending']);records=[]
        for role in discovery['riser_role_evidence']:
            p,a=role['plan'],role['iso'];pn,an=p['main_node'],a['main_node']
            try:
                evidence=dict(plan_main=native_tee(doc,plan,pn,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256']),axis_main=native_tee(axis_doc,axis,an,hashes['iso']['source_sha256'],hashes['iso']['graph_sha256']),
                    plan_riser=native_riser_circle(doc,plan,p['interface_node'],role['system']),axis_riser_junction=native_tee(axis_doc,axis,a['interface_node'],hashes['iso']['source_sha256'],hashes['iso']['graph_sha256']))
            except ValueError as exc:
                pending.append(dict(plan_node=pn,axis_node=an,reason='native_riser_role_not_proved',detail=str(exc)));continue
            accepted[pn]=an;native_roles.append(dict(role=role,native=evidence));ports.extend(x for x in discovery['riser_port_correspondences']if x['plan_node']==p['interface_node']and x['axis_node']==a['interface_node'])
        mapping=dict(parent['ordinary_junction_mappings'][f],**accepted);scoped=dict(mapping)
        for p in ports:
            if p['plan_node']in scoped or p['axis_node']in scoped.values():raise ValueError('typed port competes with ordinary anchor')
            scoped[p['plan_node']]=p['axis_node']
        components=dict(plan=csv_rows(paths['components_'+f]),iso=axis_components)
        for pe in plan['edges']:
            x,y=pe['start_node_id'],pe['end_node_id']
            if not {x,y}<=scoped.keys()or not {x,y}&accepted.keys():continue
            options=[e for e in axis['edges']if e['system']==pe['system']and {e['start_node_id'],e['end_node_id']}=={scoped[x],scoped[y]}]
            if len(options)!=1 or sum(e['system']==pe['system']and {e['start_node_id'],e['end_node_id']}=={x,y}for e in plan['edges'])!=1:continue
            ae=options[0];eid=ae['edge_id']
            if old[eid]['has_existing_correspondence']:continue
            profile={v:component_profiles(components[v],[e['edge_id']])[0]for v,e in [('plan',pe),('iso',ae)]}
            if profile['plan']!=profile['iso']:
                pending.append(dict(plan_edge=pe['edge_id'],axis_edge=eid,reason='interval_component_profiles_differ'));continue
            try:
                native={v:coverage(docs[v],graphs[v],[e['edge_id']],hashes[v]['source_sha256'],hashes[v]['graph_sha256'])for v,e in [('plan',pe),('iso',ae)]}
                if any(s['status']!='single_source_line_covers'for v in native.values()for e in v['edges']for s in e['segments']):raise ValueError('unique native source coverage missing')
            except ValueError as exc:
                pending.append(dict(plan_edge=pe['edge_id'],axis_edge=eid,reason='native_direct_interval_not_proved',detail=str(exc)));continue
            records.append(dict(mapping_id='RISER-CYCLE-F'+f+'-'+sha_bytes(encode([pe['edge_id'],eid]))[:16],kind='native_typed_riser_cycle_direct_interval',floor=floor,system=pe['system'],plan_edges=[pe['edge_id']],iso_edges=[eid],
                plan_start=x,plan_end=y,iso_start=scoped[x],iso_end=scoped[y],classification=routes[eid]['classification'],component_profiles=profile,native_path_evidence=native,
                scoped_riser_port=next((p for p in ports if p['plan_node']in(x,y)),None),DN_used_for_matching=False,physical_values_assigned=0,human_accepted=False))
        bounded=[]
        for route in discovery['bounded_routes']:
            if not {route['plan']['nodes'][0],route['plan']['nodes'][-1]}<=mapping.keys():continue
            try:native={v:coverage(docs[v],graphs[v],route[v]['edges'],hashes[v]['source_sha256'],hashes[v]['graph_sha256'])for v in('plan','iso')}
            except ValueError as exc:
                pending.append(dict(system=route['system'],reason='bounded_route_native_source_pending',route=route,detail=str(exc)));continue
            statuses={v:dict(__import__('collections').Counter(s['status']for e in proof['edges']for s in e['segments']))for v,proof in native.items()}
            bounded.append(dict(route,native_path_evidence=native,native_segment_statuses=statuses,individual_mapping_pending=True,attributes_assigned=False))
        floors[f]=dict(discovery=discovery,new_junction_mapping=accepted,riser_port_correspondences=ports,native_role_evidence=native_roles,records=records,bounded_route_differences=bounded,pending=pending,source_preflight=readable,source_hashes=hashes)
        all_records.extend(records);all_maps[f]=accepted;announce(f'{floor}F: {len(accepted)} native riser attachment Ts, {len(records)} direct intervals; {len(bounded)} bounded route differences retained')
    checked()
    if len({r['iso_edges'][0]for r in all_records})!=len(all_records):raise ValueError('competing direct interval writers')
    return dict(mode=MODE,inputs=manifest['inputs'],floors=floors,counts=dict(new_junction_pairs=sum(len(f['new_junction_mapping'])for f in floors.values()),new_riser_port_correspondences=sum(len(f.get('riser_port_correspondences',[]))for f in floors.values()),new_axis_intervals=len(all_records),new_pure_horizontal_intervals=sum(r['classification']=='horizontal_only'for r in all_records),bounded_route_differences=sum(len(f.get('bounded_route_differences',[]))for f in floors.values())),
        current_complete_provider_inventory_independently_replayed=True,source_preflight=axis_readable,raw_graphs_unchanged=True,ordinary_and_riser_port_domains_separate=True,DN_used_for_matching=False,coordinates_used_for_matching=False,ordinal_identities_assigned=False,physical_values_assigned=0,viewer_publication_pending=True,human_accepted=False,whole_goal_complete=False)

def implementation_hashes():
    names=('typed_cycle_riser_matching','graph_first_provider_inventory','rebuild_anchored_cycle_gate_batch','batch_native_path_coverage','crossview_equipment_branch_inventory','anchor_bounded_main_paths','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})
def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();result=compute(load(manifest_path),lambda s:print(s,flush=True))
    if code!=implementation_hashes():raise ValueError('typed riser implementation changed during reconstruction')
    output.mkdir(parents=True);p=output/'typed-cycle-riser-correspondences.json';p.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=code,output_sha256=sha(p))))
    return result
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'typed-cycle-riser-correspondences.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('typed riser receipt changed')
    result=compute(load(m['path']))
    if encode(result)!=p.read_bytes():raise ValueError('typed riser independent replay differs')
    return result
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
