"""Versioned common-anchor mapping for independently replayed circle inventories.

Reuse main-order/bridge and source coverage kernels. Canonical source-family
views are explicit, retain all raw entities, and do not resolve physical pipe
multiplicity. Old unique-LINE mapping modes keep their original strict rules.
"""
import argparse,copy,hashlib,re,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,native_tee,service_route
from inherited_circle_branch_inventory import verify_output as verify_inventory,implementation_hashes as inventory_hashes
from native_inherited_duplicate_circle_evidence import collect as inherited_tee
from native_canonical_main_family_view import project
from match_source_checked_crossview_paths import mutual_main_paths,selected_snapshot
from native_path_coverage_audit import audit as audit_paths

MODE='source_checked_inherited_circle_main_order_paths_v1'


def correspond(docs,graphs,inventory,inventory_policy,policy,hashes):
    selected=policy.get('equipment_ids',[]);floor=policy.get('floor');prefix=policy.get('mapping_prefix','')
    if (not isinstance(selected,list) or len(selected)<3 or len(selected)!=len(set(selected)) or isinstance(floor,bool) or not isinstance(floor,int)
        or not re.fullmatch('[A-Z0-9-]+',prefix) or set(docs)!={'plan','iso'} or set(graphs)!=set(docs)):
        raise ValueError('explicit independent multi-equipment floor scope required')
    by={r['equipment_id']:r for r in inventory['records']};indices={v:index_graph(g) for v,g in graphs.items()}
    if len(by)!=len(inventory['records']) or any(d not in by or by[d].get('ready_for_mapping_comparison') is not True or by[d].get('floor')!=floor for d in selected):
        raise ValueError('selected complete equipment services have not passed native checks')
    records=[];checks={};coverage={};used={v:set() for v in graphs};source_family_views={}
    for system in ('supply','return'):
        taps={v:{} for v in graphs};anchors={v:{} for v in graphs};corridors={};views={};source_family_views[system]={}
        for view in graphs:
            h=hashes[view]
            for did in selected:
                node=indices[view][0].get(did);service=by[did]['views'][view]['services'][system];trace=service['trace']
                if (not node or node.get('node_type') not in ('equipment','physical_equipment') or node.get('floor')!=floor
                    or service.get('ready_for_mapping_comparison') is not True or trace!=service_route(graphs[view],did,system)
                    or trace.get('status')!='unique_graph_service_to_T' or len(trace['edges'])!=1):raise ValueError('current source service owner, route or floor differs')
                nid=trace['tee'];fresh=inherited_tee(docs[view],graphs[view],nid,h['source_sha256'],h['graph_sha256'],inventory_policy) if view=='plan' else native_tee(docs[view],graphs[view],nid,h['source_sha256'],h['graph_sha256'])
                if fresh!=service.get('junction_evidence'):raise ValueError('current native T evidence differs from independently replayed inventory')
                if nid in taps[view].values():raise ValueError('equipment anchors collapse onto one source T')
                taps[view][did]=nid;anchors[view][nid]=dict(evidence=fresh,branch_edges=trace['edges'])
            views[view],corridors[view],source_family_views[system][view]=project(docs[view],graphs[view],taps[view],system,floor,
                policy['source_main_families'][view][system],anchors[view],h['source_sha256'],h['graph_sha256'])
        check=mutual_main_paths(corridors,taps,system,floor);checks[system]=check
        for view in graphs:
            selected_taps=set(taps[view].values());route_nodes={nid for pair in check['adjacent'] for nid in pair['routes'][view]['nodes']}
            extra=[nid for nid in route_nodes-selected_taps if len(indices[view][2][nid])!=2]
            if extra:raise ValueError('unmatched interior main branches require separate source comparison before this mapping')
        for did in selected:
            branches={v:by[did]['views'][v]['services'][system]['trace']['edges'] for v in graphs}
            records.append(dict(kind='equipment_branch',equipment_id=did,system=system,floor=floor,
                plan_edges=branches['plan'],iso_edges=branches['iso'],plan_start=taps['plan'][did],iso_start=taps['iso'][did],plan_end=did,iso_end=did,
                local_evidence={v:copy.deepcopy(by[did]['views'][v]['services'][system]) for v in graphs}))
        for pair in check['adjacent']:
            a,b=pair['equipment_order'];routes=pair['routes']
            records.append(dict(kind='main_between_equipment_branches',endpoint_equipment_ids=[a,b],system=system,floor=floor,
                plan_edges=routes['plan']['edges'],iso_edges=routes['iso']['edges'],plan_start=taps['plan'][a],plan_end=taps['plan'][b],iso_start=taps['iso'][a],iso_end=taps['iso'][b]))
        coverage[system]={}
        for view in graphs:
            ids=[eid for r in records if r['system']==system for eid in r[view+'_edges']]
            if len(ids)!=len(set(ids)) or used[view].intersection(ids):raise ValueError('source correspondence repeats a branch or main edge')
            used[view].update(ids);mains=[eid for r in records if r['system']==system and r['kind']=='main_between_equipment_branches' for eid in r[view+'_edges']]
            h=hashes[view];audited=audit_paths(views[view],graphs[view],dict(h,edges=mains),h['source_sha256'],h['graph_sha256'])
            if any(s['status']!='single_source_line_covers' for e in audited['edges'] for s in e['segments']):raise ValueError('canonical main path lacks native source coverage')
            coverage[system][view]=dict(status='canonical_graph_LINE_source_coverage_physical_multiplicity_unresolved',
                canonical_source_projection=source_family_views[system][view]['canonical_source_projection'],evidence=audited)
    for i,row in enumerate(records,1):
        row.update(mapping_id=prefix+'-MAP-'+str(i).zfill(4),status='source_checked_inherited_circle_common_anchor_path_human_pending',
            decision_basis='replayed_local_branches_and_mutual_main_order_with_explicit_canonical_source_families',
            physical_source_identity_resolved=False,physical_ports_verified=False,human_accepted=False,
            plan_snapshot=selected_snapshot(graphs['plan'],row['plan_edges']),iso_snapshot=selected_snapshot(graphs['iso'],row['iso_edges']))
    return dict(mode=MODE,status='source_checked_path_correspondence_attributes_pending',floor=floor,equipment_scope=selected,records=records,
        source_sha256={v:h['source_sha256'] for v,h in hashes.items()},plan_graph_sha256=hashes['plan']['graph_sha256'],iso_graph_sha256=hashes['iso']['graph_sha256'],
        evidence=dict(main_topology=checks,main_coverage=coverage,native_source_families=source_family_views),
        local_graphs_mutated=False,expert_confirmation_claimed=False,physical_source_identity_resolved=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)


def compute(paths,policy):
    for key in ('inventory','inventory_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('inherited mapping input changed '+key)
    directory=Path(paths['inventory']).resolve().parent
    if Path(paths['inventory']).resolve()!=directory/'inventory.json' or Path(paths['inventory_receipt']).resolve()!=directory/'inventory-receipt.json':raise ValueError('noncanonical inherited inventory')
    receipt=load(paths['inventory_receipt']);inventory=verify_inventory(directory);inventory_policy=load(receipt['inputs']['policy']['path'])
    local=load(receipt['inputs']['parent_receipt']['path'])['inputs'];graphs={};docs={};hashes={}
    for view in ('plan','iso'):
        graphs[view]=load(local[view+'_graph']['path']);docs[view],_=read_source(local[view+'_source']['path'])
        hashes[view]=dict(source_sha256=sha(local[view+'_source']['path']),graph_sha256=sha(local[view+'_graph']['path']))
    result=correspond(docs,graphs,inventory,inventory_policy,policy,hashes)
    result['evidence']['inventory_sha256']=sha(paths['inventory'])
    return result,{k:copy.deepcopy(local[k]) for k in ('plan_source','iso_source','plan_graph','iso_graph')}


def implementation_hashes():
    result=inventory_hashes()
    for name in (Path(__file__).name,'native_canonical_main_family_view.py','match_source_checked_crossview_paths.py','native_path_coverage_audit.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inherited mapping implementation changed')
    for spec in receipt['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('inherited mapping dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result,local=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256'] or local!=receipt['local_inputs']:
        raise ValueError('inherited mapping native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result,local=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    receipt=dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},local_inputs=local,
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)
    (a.output/'source-mapping-receipt.json').write_bytes(encode(receipt));print(dict(paths=len(result['records']),equipment=len(result['equipment_scope']),physical_values=0),flush=True)


if __name__=='__main__':main()
