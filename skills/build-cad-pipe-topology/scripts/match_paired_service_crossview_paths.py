"""Correspond source-checked equipment pairs through both service corridors.

This is a separate proof from three-anchor main-order matching. Four equipment
service branches per view and both independent native main paths are required.
No source ownership, local connection, physical value or human answer is added.
"""
import argparse,copy,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from crossview_equipment_branch_inventory import index_graph,native_tee,service_route
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory
from match_source_checked_crossview_paths import native_main_corridor,bridge_main_path,selected_snapshot
from native_path_coverage_audit import audit as audit_paths
from source_readability import read_source

MODE='source_checked_paired_service_paths_v1'
INPUTS=('inventory','inventory_receipt','plan_source','iso_source','plan_graph','iso_graph')


def pair_paths(docs,graphs,by,equipment,floor,hashes):
    if len(equipment)!=2 or len(set(equipment))!=2 or set(docs)!= {'plan','iso'} or set(graphs)!=set(docs):
        raise ValueError('exactly two independent equipment in both views required')
    indices={v:index_graph(g) for v,g in graphs.items()};result={};claimed={v:set() for v in graphs};anchors={v:set() for v in graphs}
    for did in equipment:
        row=by.get(did)
        if not row or row.get('floor')!=floor or row.get('ready_for_mapping_comparison') is not True:
            raise ValueError('both complete equipment services must be independently source-ready')
    for system in ('supply','return'):
        taps={v:{} for v in graphs};branches={v:{} for v in graphs}
        for view in graphs:
            for did in equipment:
                service=by[did]['views'][view]['services'][system];trace=service['trace']
                if service.get('ready_for_mapping_comparison') is not True or trace.get('status')!='unique_graph_service_to_T':raise ValueError('unsupported local service')
                owner=indices[view][0].get(did)
                if not owner or owner.get('node_type') not in ('equipment','physical_equipment') or owner.get('floor')!=floor or trace!=service_route(graphs[view],did,system):raise ValueError('service no longer belongs to the source-checked equipment')
                nid=trace['tee'];node=indices[view][0][nid]
                if node.get('floor')!=floor or node.get('review_required') is True or nid in anchors[view]:raise ValueError('shared, wrong-floor or unresolved service anchor')
                anchors[view].add(nid);taps[view][did]=nid;branches[view][did]=trace['edges']
                for eid in trace['edges']:
                    edge=indices[view][1][eid]
                    if edge['system']!=system or eid in claimed[view]:raise ValueError('overlapping or mixed service branches')
                    claimed[view].add(eid)
                # Recheck even fixture-provided local evidence at this entry.
                native_tee(docs[view],graphs[view],nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        corridors={v:native_main_corridor(docs[v],graphs[v],taps[v],system,floor) for v in graphs}
        routes={v:bridge_main_path(corridors[v][0],taps[v][equipment[0]],taps[v][equipment[1]],system,floor) for v in graphs}
        internal={}
        for view,route in routes.items():
            junctions=[]
            for nid in route['nodes'][1:-1]:
                incident=indices[view][2][nid]
                if len(incident)==2:continue  # Source-covered subdivisions are not branch correspondence.
                if len(incident)!=3 or {e['system'] for e in incident}!={system}:raise ValueError('unresolved interior main junction')
                junctions.append(dict(node_id=nid,evidence=native_tee(docs[view],graphs[view],nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])))
            internal[view]=junctions
            if claimed[view].intersection(route['edges']):raise ValueError('main and service paths overlap')
            claimed[view].update(route['edges'])
        if len(internal['plan'])!=len(internal['iso']):raise ValueError('internal main branch counts disagree; return to local topology')
        result[system]=dict(taps=taps,branches=branches,routes=routes,native_corridors={v:corridors[v][1] for v in graphs},
            internal_native_junctions=internal,offcorridor_branch_correspondence='not_asserted')
    return result


def compute(paths,policy):
    for key in INPUTS:
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('stale paired source input '+key)
    folder=Path(paths['inventory']).resolve().parent
    if Path(paths['inventory']).resolve()!=folder/'inventory.json' or Path(paths['inventory_receipt']).resolve()!=folder/'inventory-receipt.json':raise ValueError('noncanonical inventory paths')
    receipt=load(paths['inventory_receipt'])
    for key in ('plan_source','iso_source','plan_graph','iso_graph'):
        if receipt['inputs'][key]['sha256']!=sha(paths[key]):raise ValueError('inventory and paired mapping scope differ')
    inventory=verify_inventory(folder);by={r['equipment_id']:r for r in inventory['records']}
    pairs=policy.get('equipment_pairs');floor=policy.get('floor');reference=policy.get('context_only_equipment_ids',[])
    if (not isinstance(pairs,list) or not pairs or any(not isinstance(p,list) or len(p)!=2 for p in pairs)
        or isinstance(floor,bool) or not isinstance(floor,int) or not isinstance(reference,list) or len(reference)!=len(set(reference))):raise ValueError('explicit paired floor scope required')
    selected=[did for pair in pairs for did in pair]
    if len(selected)!=len(set(selected)) or not set(reference)<=set(selected) or any(set(p)<=set(reference) for p in pairs):raise ValueError('duplicate pairs or invalid context-only scope')
    graphs={v:load(paths[v+'_graph']) for v in ('plan','iso')};docs={v:read_source(paths[v+'_source'])[0] for v in graphs}
    hashes={v:dict(source_sha256=sha(paths[v+'_source']),graph_sha256=sha(paths[v+'_graph'])) for v in graphs};records=[];checks=[]
    for pi,pair in enumerate(pairs,1):
        checked=pair_paths(docs,graphs,by,pair,floor,hashes);checks.append(dict(pair_id=f'P{pi:02d}',equipment_ids=pair,services=checked))
        for system,state in checked.items():
            for did in pair:
                if did in reference:continue
                records.append(dict(kind='equipment_branch',equipment_id=did,system=system,floor=floor,
                    plan_edges=state['branches']['plan'][did],iso_edges=state['branches']['iso'][did],
                    plan_start=state['taps']['plan'][did],iso_start=state['taps']['iso'][did],plan_end=did,iso_end=did,
                    local_evidence={v:by[did]['views'][v]['services'][system] for v in graphs}))
            records.append(dict(kind='main_between_equipment_branches',endpoint_equipment_ids=pair,system=system,floor=floor,
                plan_edges=state['routes']['plan']['edges'],iso_edges=state['routes']['iso']['edges'],
                plan_start=state['taps']['plan'][pair[0]],plan_end=state['taps']['plan'][pair[1]],
                iso_start=state['taps']['iso'][pair[0]],iso_end=state['taps']['iso'][pair[1]]))
    coverage={}
    for view in graphs:
        eids=[eid for r in records for eid in r[view+'_edges']]
        if len(eids)!=len(set(eids)):raise ValueError('paired mapping double counts an edge')
        main=[eid for r in records if r['kind']=='main_between_equipment_branches' for eid in r[view+'_edges']]
        coverage[view]=audit_paths(docs[view],graphs[view],dict(hashes[view],edges=main),hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        if any(s['status']!='single_source_line_covers' for e in coverage[view]['edges'] for s in e['segments']):raise ValueError('paired main lacks unique native coverage')
    for index,record in enumerate(records,1):
        record.update(mapping_id=f'PS-{index:04d}',status='source_checked_paired_service_path_not_human_accepted',
            decision_basis='independent_two_equipment_four_service_branches_and_native_main_paths',physical_ports_verified=False,human_accepted=False,
            plan_snapshot=selected_snapshot(graphs['plan'],record['plan_edges']),iso_snapshot=selected_snapshot(graphs['iso'],record['iso_edges']))
    return dict(status='source_checked_paired_service_correspondence_attributes_pending',mode=MODE,
        plan_graph_sha256=hashes['plan']['graph_sha256'],iso_graph_sha256=hashes['iso']['graph_sha256'],source_sha256={v:hashes[v]['source_sha256'] for v in graphs},
        records=records,equipment_scope=selected,context_only_equipment_ids=reference,floor=floor,
        evidence=dict(paired_services=checks,main_coverage=coverage,inventory_sha256=sha(paths['inventory'])),
        local_graphs_mutated=False,expert_confirmation_claimed=False,human_accepted=False,hil_ready=False,
        limitations=['This is paired-service source proof, not three-anchor main-order proof or an expert cross-view answer.',
            'Off-corridor branches at intermediate native Ts are not automatically mapped.',
            'DN extents, lengths, physical equipment ports and whole-graph acceptance remain separate.'])


def implementation_hashes():
    names=('match_paired_service_crossview_paths.py','crossview_equipment_branch_inventory_v2.py','native_exploded_endpoint_evidence.py',
        'crossview_equipment_branch_inventory.py','match_source_checked_crossview_paths.py','native_path_coverage_audit.py','source_readability.py')
    return {name:sha(Path(__file__).with_name(name)) for name in names}


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('stale paired mapping entry')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('paired mapping input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('paired mapping native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in (*INPUTS,'policy','output'):parser.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    args=parser.parse_args();paths={key:getattr(args,key) for key in (*INPUTS,'policy')}
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(paths,load(args.policy));args.output.mkdir(parents=True);(args.output/'mapping.json').write_bytes(encode(result))
    (args.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(args.output/'mapping.json'),human_accepted=False)))
    print(dict(paths=len(result['records']),equipment=len(result['equipment_scope']),context_only=result['context_only_equipment_ids']),flush=True)


if __name__=='__main__':main()
