"""Replay current providers, batch cycle-gate matching, verify native Ts/paths."""
import argparse, collections, copy, csv, importlib, sys
from pathlib import Path
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from anchored_cycle_gate_matching import discover
from source_readability import read_source
from crossview_equipment_branch_inventory import native_tee
from batch_native_path_coverage import collect as coverage
from anchor_bounded_main_paths import component_profiles
from native_replay_session import verify_once
MODE='native_anchored_cycle_gate_crossview_batch_v1'

def csv_rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))

def compute(manifest,announce=lambda s:None):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('cycle gate input changed')
    checked()
    from bridge_aware_provider_inventory import verify_output
    announce('Replaying complete current correspondence providers and original topology owners')
    parent=verify_once(paths['inventory'].parent,verify_output)
    if encode(parent)!=paths['inventory'].read_bytes():raise ValueError('current provider replay differs')
    original=parent['original_provider_inventory_inputs']
    for key in ('axis_graph','plan_graph_1','plan_graph_2','plan_graph_3','routing'):
        if sha(paths[key])!=original[key]['sha256']or paths[key].resolve()!=Path(original[key]['path']).resolve():raise ValueError('cycle discovery uses another local graph or routing '+key)
    axis=load(paths['axis_graph']);axis_doc,axis_preflight=read_source(paths['axis_source'])
    if axis['metadata']['source_sha256']!=sha(paths['axis_source']):raise ValueError('axis source differs')
    ac=csv_rows(paths['axis_components']);routing=load(paths['routing'])
    routes={r['edge_id']:r for r in routing['edges']}
    old={r['edge_id']:r for r in parent['records']};new_records=[];floors={}
    for floor in (1,2,3):
        f=str(floor);plan=load(paths['plan_graph_'+f]);mapping=parent['ordinary_junction_mappings'][f]
        graphs=dict(plan=plan,iso=axis);result=discover(graphs,mapping,floor)
        if not result['new_junction_mapping']:
            floors[f]=dict(discovery=result,new_junction_mapping={},records=[],native_gate_evidence={});continue
        doc,preflight=read_source(paths['plan_source_'+f])
        if plan['metadata']['source_sha256']!=sha(paths['plan_source_'+f]):raise ValueError('plan source differs')
        docs=dict(plan=doc,iso=axis_doc);hashes={v:dict(source_sha256=sha(paths['plan_source_'+f]if v=='plan'else paths['axis_source']),graph_sha256=sha(paths['plan_graph_'+f]if v=='plan'else paths['axis_graph']))for v in graphs}
        gate_evidence={};pending=copy.deepcopy(result['pending']);accepted={}
        for pn,an in result['new_junction_mapping'].items():
            try:
                gate_evidence[pn]={v:native_tee(docs[v],graphs[v],n,hashes[v]['source_sha256'],hashes[v]['graph_sha256'])for v,n in [('plan',pn),('iso',an)]}
                accepted[pn]=an
            except ValueError as exc:
                pending.append(dict(plan_node=pn,axis_node=an,reason='native_cycle_gate_not_proved',detail=str(exc)))
        extended=dict(mapping,**accepted);components=dict(plan=csv_rows(paths['components_'+f]),iso=ac);records=[]
        for pe in plan['edges']:
            x,y=pe['start_node_id'],pe['end_node_id']
            if x not in extended or y not in extended or not({x,y}&accepted.keys()):continue
            options=[ae for ae in axis['edges']if ae['system']==pe['system']and {ae['start_node_id'],ae['end_node_id']}=={extended[x],extended[y]}]
            plan_options=[e for e in plan['edges']if e['system']==pe['system']and {e['start_node_id'],e['end_node_id']}=={x,y}]
            if len(options)!=1 or len(plan_options)!=1:
                pending.append(dict(plan_edge=pe['edge_id'],reason='missing_or_parallel_direct_interval'));continue
            ae=options[0];eid=ae['edge_id']
            if old[eid]['has_existing_correspondence']:continue
            profile={v:component_profiles(components[v],[e['edge_id']])[0]for v,e in [('plan',pe),('iso',ae)]}
            if profile['plan']!=profile['iso']:
                pending.append(dict(plan_edge=pe['edge_id'],axis_edge=eid,reason='interval_component_profiles_differ',profiles=profile));continue
            native={}
            try:
                for v,e in [('plan',pe),('iso',ae)]:
                    native[v]=coverage(docs[v],graphs[v],[e['edge_id']],hashes[v]['source_sha256'],hashes[v]['graph_sha256'])
                    if any(s['status']!='single_source_line_covers'for r in native[v]['edges']for s in r['segments']):raise ValueError('interval lacks unique native LINE coverage')
            except ValueError as exc:
                pending.append(dict(plan_edge=pe['edge_id'],axis_edge=eid,reason='native_interval_not_proved',detail=str(exc)));continue
            row=dict(mapping_id='CYCLE-F'+f+'-'+sha_bytes(encode([pe['edge_id'],eid]))[:16],kind='native_cycle_gate_direct_interval',floor=floor,system=pe['system'],
                     plan_edges=[pe['edge_id']],iso_edges=[eid],plan_start=x,plan_end=y,iso_start=extended[x],iso_end=extended[y],
                     classification=routes[eid]['classification'],component_profiles=profile,native_path_evidence=native,
                     original_known_endpoint_evidence='independently_replayed_complete_provider_inventory',
                     DN_used_for_matching=False,physical_values_assigned=0,human_accepted=False)
            records.append(row);new_records.append(row)
        floors[f]=dict(discovery=result,new_junction_mapping=accepted,native_gate_evidence=gate_evidence,records=records,pending=pending,source_preflight=preflight,source_hashes=hashes)
        announce(f'{floor}F: {len(accepted)} native cycle gates; {len(records)} native direct intervals; all cycle interiors retained')
    checked()
    if len({r['iso_edges'][0]for r in new_records})!=len(new_records):raise ValueError('cycle batch has competing axis writers')
    return dict(mode=MODE,floors=floors,inputs=manifest['inputs'],counts=dict(existing_correspondence_edges=parent['counts']['existing_correspondence_edges'],
                new_junction_pairs=sum(len(f['new_junction_mapping'])for f in floors.values()),new_axis_intervals=len(new_records),
                new_pure_horizontal_intervals=sum(r['classification']=='horizontal_only'for r in new_records)),
                current_provider_inventory_independently_replayed=True,source_preflight=axis_preflight,
                raw_graphs_unchanged=True,member_namespaces_preserved=True,DN_used_for_matching=False,
                coordinates_used_for_matching=False,shortest_path_used=False,interior_node_identities_assigned=False,
                physical_values_assigned=0,viewer_publication_pending=True,human_accepted=False,whole_goal_complete=False)

def sha_bytes(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()

def implementation_hashes():
    names=('anchored_cycle_gate_matching','bridge_aware_provider_inventory','batch_native_path_coverage','crossview_equipment_branch_inventory','anchor_bounded_main_paths','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();result=compute(load(manifest_path),lambda s:print(s,flush=True))
    if code!=implementation_hashes():raise ValueError('cycle code changed during reconstruction')
    output.mkdir(parents=True);target=output/'cycle-gate-correspondences.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=code,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'cycle-gate-correspondences.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('cycle gate receipt, code or input changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('cycle gate independent native replay differs')
    return result

def main():
    parser=argparse.ArgumentParser()
    for name in ('manifest','output','verify-output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output:r=verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output:parser.error('manifest and fresh output required')
            r=produce(args.manifest,args.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
