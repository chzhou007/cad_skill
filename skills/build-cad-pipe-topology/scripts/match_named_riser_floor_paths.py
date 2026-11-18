"""Match a named floor-riser approach to an independently checked device T.

Two source anchors per service are required: a native named riser interface
and the same equipment's independently checked local service branch. The
output is logical interface/path correspondence, not a physical port or metric.
"""
import argparse,dataclasses,math,runpy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,native_tee,service_route
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory
from native_axis_riser_DN_scopes import verify_output as verify_riser,implementation_hashes as riser_hashes
from native_named_riser_evidence import collect as collect_names
from native_line_path_evidence import _on,LAYERS
from native_path_coverage_audit import audit as coverage

MODE='source_checked_named_riser_floor_paths_v1'


def vent_normalization(doc):
    ns=runpy.run_path(str(Path(__file__).parent/'legacy_v17/analyze_graph.py'))
    ns['collect_pipe_segments'].__globals__['get_system_layers']=lambda current:{v:k for k,v in LAYERS.items()}
    segments=ns['collect_pipe_segments'](doc);segments,_=ns['trim_short_dangling_overshoots'](segments)
    segments,_=ns['remove_turn_display_valve_stubs'](segments,ns['collect_turn_display_valve_regions'](doc))
    layout=ns['infer_drawing_layout'](ns['equipment_labels'](doc))
    _,removed=ns['remove_auto_air_vent_display_legs'](segments,ns['collect_auto_air_vent_ports'](doc),layout)
    return removed


def correspond(docs,graphs,inventory,named,riser,removed,policy,hashes):
    equipment=policy['equipment_id'];floor=policy['floor'];ids=policy['identifiers']
    if (set(docs)!={'plan','iso'} or set(graphs)!=set(docs) or set(named)!=set(docs)
        or not isinstance(floor,int) or isinstance(floor,bool) or len(ids)!=2 or len(set(ids))!=2):raise ValueError('exact two-service named floor scope required')
    owners=[r for r in inventory['records'] if r['equipment_id']==equipment]
    if len(owners)!=1 or owners[0].get('ready_for_mapping_comparison') is not True or owners[0]['floor']!=floor:raise ValueError('equipment not independently source-ready in both views')
    owner=owners[0];indices={v:index_graph(g) for v,g in graphs.items()};records=[];systems=set()
    for identifier in ids:
        names={v:[r for r in named[v]['records'] if r['identifier']==identifier] for v in graphs}
        if any(len(rows)!=1 for rows in names.values()):raise ValueError('named riser is missing or repeated in selected source scope')
        names={v:rows[0] for v,rows in names.items()};system=names['plan']['system']
        if system not in LAYERS or system in systems or names['iso']['system']!=system:raise ValueError('named riser service ambiguity')
        systems.add(system);tip=names['iso']['leader']['target_point']
        candidates=[r for r in removed if r.system==system and _on(tip[:2],list(r.vent_port),list(r.junction),.05)]
        if len(candidates)!=1:raise ValueError('axis name has no unique inherited air-vent display-leg context')
        removal=candidates[0];contracts=[]
        for contract in riser['through_contracts']:
            if contract['system']!=system:continue
            upper=[s for s in contract['segments'] if s['side']=='upper']
            if len(upper)!=1:raise ValueError('riser scope upper segment is not unique')
            edge=indices['iso'][1][upper[0]['edge_id']]
            at=[p for path in edge['attribute_paths'] for p in path[1:-1] if math.dist(p,removal.junction)<=.05]
            if len(at)==1:contracts.append(contract)
        if len(contracts)!=1:raise ValueError('named axis core does not identify one checked through-riser column')
        contract=contracts[0];middle=contract['middle_T'];axisnode=indices['iso'][0][middle]
        if axisnode['floor']!=floor or axisnode.get('review_required') is True:raise ValueError('named axis interface is unresolved or on another floor')
        traces={v:service_route(graphs[v],equipment,system) for v in graphs}
        if any(traces[v]!=owner['views'][v]['services'][system]['trace'] or traces[v]['status']!='unique_graph_service_to_T' for v in graphs):raise ValueError('independent source service T differs')
        planname=names['plan']
        if planname['target_kind']!='plan_riser_circle' or planname['target']['floor']!=floor:raise ValueError('plan riser is not a source circle on selected floor')
        rif=planname['target']['node_id'];incident=indices['plan'][2][rif]
        if len(incident)!=1 or incident[0]['system']!=system or {incident[0]['start_node_id'],incident[0]['end_node_id']}!={rif,traces['plan']['tee']}:raise ValueError('plan interface does not directly reach independently checked equipment main T')
        matching=[e for e in indices['iso'][2][middle] if e['system']==system and {e['start_node_id'],e['end_node_id']}=={middle,traces['iso']['tee']}]
        if len(matching)!=1 or matching[0]['edge_id']!=contract['non_through_branch']:raise ValueError('axis interface approach differs from actual non-through branch')
        chosen={'plan':incident[0],'iso':matching[0]};proofs={}
        for view in graphs:
            graph=graphs[view];edge=chosen[view];h=hashes[view]
            result=coverage(docs[view],graph,dict(h,edges=[edge['edge_id']]),h['source_sha256'],h['graph_sha256'])
            if any(s['status']!='single_source_line_covers' for r in result['edges'] for s in r['segments']):raise ValueError('named floor approach lacks native source path coverage')
            tees=[traces[view]['tee']]+([middle] if view=='iso' else [])
            proofs[view]=dict(edge_id=edge['edge_id'],attribute_paths=edge['attribute_paths'],native_coverage=result,
                independent_equipment_service=owner['views'][view]['services'][system],junctions=[native_tee(docs[view],graph,t,h['source_sha256'],h['graph_sha256']) for t in tees])
        records.append(dict(mapping_id=f'RIF-{floor}-{identifier}-{equipment}',kind='named_riser_floor_approach',floor=floor,system=system,identifier=identifier,equipment_id=equipment,
            plan_edges=[incident[0]['edge_id']],iso_edges=[matching[0]['edge_id']],plan_riser_interface=rif,iso_riser_junction=middle,
            plan_equipment_main_T=traces['plan']['tee'],iso_equipment_main_T=traces['iso']['tee'],native_names=names,paths=proofs,
            inherited_display_leg_normalization=dataclasses.asdict(removal),
            matching_basis='native_named_riser_and_independently_checked_equipment_service_anchors',
            local_graphs_mutated=False,physical_port_verified=False,plan_glyph_radius_added_to_length=False,physical_length_mm=None,human_accepted=False))
    if systems!={'supply','return'}:raise ValueError('both independent services required')
    return records


def compute(paths,policy):
    for key in ('inventory','inventory_receipt','riser_scope','riser_receipt','plan_name_policy','iso_name_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('named floor-riser input changed '+key)
    folder=Path(paths['inventory']).resolve().parent
    if Path(paths['inventory']).resolve()!=folder/'inventory.json' or Path(paths['inventory_receipt']).resolve()!=folder/'inventory-receipt.json':raise ValueError('noncanonical service inventory')
    inventory=verify_inventory(folder);ir=load(paths['inventory_receipt']);inputs={k:v['path'] for k,v in ir['inputs'].items()}
    directory=Path(paths['riser_scope']).resolve().parent
    if Path(paths['riser_scope']).resolve()!=directory/'axis-riser-DN-scopes.json' or Path(paths['riser_receipt']).resolve()!=directory/'axis-riser-DN-scope-receipt.json':raise ValueError('noncanonical riser scope')
    riser=verify_riser(directory);graphs={v:load(inputs[v+'_graph']) for v in ('plan','iso')};docs={v:read_source(inputs[v+'_source'])[0] for v in graphs}
    hashes={v:dict(source_sha256=sha(inputs[v+'_source']),graph_sha256=sha(inputs[v+'_graph'])) for v in graphs}
    if riser['graph_sha256']!=hashes['iso']['graph_sha256'] or riser['source_sha256']!=hashes['iso']['source_sha256']:raise ValueError('named approach and riser use different local axis source')
    named={}
    for view in graphs:
        original=load(paths[view+'_name_policy']);selected=policy['native_label_handles'][view]
        if len(selected)!=2 or len(set(selected))!=2:raise ValueError('exact main-view label source scope required')
        scoped=dict(original,selections=[s for s in original['selections'] if s['text_handle'] in selected])
        if len(scoped['selections'])!=2:raise ValueError('selected native labels missing from named source policy')
        named[view]=collect_names(docs[view],graphs[view],scoped,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
    records=correspond(docs,graphs,inventory,named,riser,vent_normalization(docs['iso']),policy,hashes)
    return dict(mode=MODE,status='source_checked_named_floor_riser_paths_attributes_pending',source_sha256={v:h['source_sha256'] for v,h in hashes.items()},
        graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()},records=records,local_graphs_mutated=False,
        physical_values_fused=False,physical_ports_verified=False,DN_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)


def implementation_hashes():
    hashes=riser_hashes()
    for name in ('match_named_riser_floor_paths.py','native_named_riser_evidence.py','crossview_equipment_branch_inventory_v2.py','crossview_equipment_branch_inventory.py','native_path_coverage_audit.py'):
        hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'named-riser-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('named riser mapping implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('named riser mapping dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('named riser mapping native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','riser-run','plan-name-policy','iso-name-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',
        riser_scope=a.riser_run/'axis-riser-DN-scopes.json',riser_receipt=a.riser_run/'axis-riser-DN-scope-receipt.json',plan_name_policy=a.plan_name_policy,iso_name_policy=a.iso_name_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'mapping.json').write_bytes(encode(result))
    (a.output/'named-riser-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'mapping.json'),human_accepted=False)))
    print(dict(named_floor_approaches=len(result['records']),physical_values_fused=False,human_accepted=False),flush=True)


if __name__=='__main__':main()
