"""Source-check direct mains between independently matched, same-service Ts.

This extends a replayed partial mapping. It does not match unknown nodes, select
a shortest route, repair local topology, assign physical values or accept HIL.
"""
import argparse
import collections
import copy
import csv
import re
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory import index_graph, native_tee
from match_junction_rebased_paired_paths import MODE as PAIRED_MODE, verify_output as verify_parent
from match_junction_rebased_corridors import MODE as CORRIDOR_MODE
from match_source_checked_crossview_paths import selected_snapshot
from native_inline_joint_path_coverage import collect as inline_coverage
from native_path_coverage_audit import audit as line_coverage
from source_readability import read_source

MODE = 'source_checked_known_junction_direct_mains_v1'


def known_nodes(graphs, records, floor):
    if type(floor) is not int or floor < 1 or set(graphs) != {'plan','iso'} or not records:
        raise ValueError('Explicit two-view floor and parent paths required')
    indexes = {v: index_graph(g) for v,g in graphs.items()}
    maps = {v:{} for v in graphs}; used = {v:set() for v in graphs}; ids = set()
    owners = collections.defaultdict(list)
    for row in records:
        system = row.get('system'); rid = row.get('mapping_id')
        if system not in ('supply','return') or row.get('floor') != floor or not rid or rid in ids:
            raise ValueError('Parent service, floor or unique mapping identity differs')
        ids.add(rid)
        for view in graphs:
            nodes,edges,_ = indexes[view]; path = row[view+'_edges']
            if not path or len(path)!=len(set(path)) or used[view].intersection(path):
                raise ValueError('Parent path writer repeated')
            if selected_snapshot(graphs[view],path) != row[view+'_snapshot']:
                raise ValueError('Parent path snapshot changed')
            current=row[view+'_start']; visited={current}
            for eid in path:
                e=edges[eid]
                if e['system']!=system or current not in (e['start_node_id'],e['end_node_id']):
                    raise ValueError('Parent path order or service differs')
                current=e['end_node_id'] if current==e['start_node_id'] else e['start_node_id']
                if current in visited or nodes[current].get('floor')!=floor:
                    raise ValueError('Parent path has a cycle or leaves the floor')
                visited.add(current)
            if current!=row[view+'_end'] or nodes[row[view+'_start']].get('floor')!=floor:
                raise ValueError('Parent path endpoints differ')
            used[view].update(path)
        for side in ('start','end'):
            a=(system,row['plan_'+side]); b=(system,row['iso_'+side])
            if (a in maps['plan'] and maps['plan'][a]!=b) or (b in maps['iso'] and maps['iso'][b]!=a):
                raise ValueError('Parent junction identity is inconsistent or collapsed')
            maps['plan'][a]=b; maps['iso'][b]=a; owners[a].append(rid)
    return indexes,maps,used,owners


def discover(graphs, parent_records, floor):
    indexes,maps,used,owners=known_nodes(graphs,parent_records,floor)
    groups={v:collections.defaultdict(list) for v in graphs}
    for view in graphs:
        nodes,edges,adj=indexes[view]
        for eid,e in sorted(edges.items()):
            system=e['system']; a=e['start_node_id']; b=e['end_node_id']
            if eid in used[view] or (system,a) not in maps[view] or (system,b) not in maps[view]:continue
            if any(nodes[n]['node_type'] not in ('tee','physical_junction') for n in (a,b)):continue
            if a==b or any(nodes[n].get('floor')!=floor or nodes[n].get('review_required') is True
                or len(adj[n])!=3 or {x['system'] for x in adj[n]}!={system} for n in (a,b)):
                raise ValueError('Known-junction candidate is not a qualified same-floor same-service T')
            groups[view][(system,frozenset((a,b)))].append(e)
    candidates=[]; pending=[]; used_axis=set()
    for (system,ends),plan in groups['plan'].items():
        mapped=frozenset(maps['plan'][(system,n)][1] for n in ends)
        axis=groups['iso'].get((system,mapped),[])
        if len(plan)!=1 or len(axis)!=1:
            pending.append(dict(system=system,plan_edges=[e['edge_id'] for e in plan],
                                iso_edges=[e['edge_id'] for e in axis],reason='missing_or_parallel_direct_main'))
            continue
        p,a=plan[0],axis[0]; used_axis.add(a['edge_id'])
        row=dict(kind='main_between_independently_matched_junctions',floor=floor,system=system,
            plan_edges=[p['edge_id']],iso_edges=[a['edge_id']],plan_start=p['start_node_id'],plan_end=p['end_node_id'],
            iso_start=maps['plan'][(system,p['start_node_id'])][1],iso_end=maps['plan'][(system,p['end_node_id'])][1],
            endpoint_parent_mapping_ids={side:owners[(system,p[side+'_node_id'])] for side in ('start','end')},
            shortest_path_or_nearest_geometry_used=False,physical_ports_verified=False,human_accepted=False)
        for view in graphs:row[view+'_snapshot']=selected_snapshot(graphs[view],row[view+'_edges'])
        candidates.append(row)
    for group in groups['iso'].values():
        if any(e['edge_id'] not in used_axis for e in group):
            pending.append(dict(iso_edges=[e['edge_id'] for e in group],reason='unpaired_axis_direct_main'))
    return candidates,pending


def read_paths(docs,graphs,rows,local,origin):
    proofs={}; junctions={}
    if origin.get('confirmation_basis')!='source_geometry_calibrated' or not origin.get('expert_evidence'):
        raise ValueError('Calibrated native inline template origin required')
    for view,graph in graphs.items():
        h={key+'_sha256':local[view+'_'+key]['sha256'] for key in ('source','graph')}
        _,edges,_=index_graph(graph); ids=[r[view+'_edges'][0] for r in rows]
        nids={r[view+'_'+side] for r in rows for side in ('start','end')}
        junctions[view]={nid:native_tee(docs[view],graph,nid,h['source_sha256'],h['graph_sha256']) for nid in sorted(nids)}
        simple=[eid for eid in ids if len(edges[eid].get('attribute_paths',[]))==1]
        multi=[eid for eid in ids if eid not in simple];proofs[view]={}
        if simple:
            evidence=line_coverage(docs[view],graph,dict(h,edges=simple),h['source_sha256'],h['graph_sha256'])
            if any(s['status']!='single_source_line_covers' for e in evidence['edges'] for s in e['segments']):
                raise ValueError('Selected direct main lacks unique native pipe coverage')
            proofs[view]['native_LINE_paths']=evidence
        if multi:
            item=local[view+'_devices']
            if sha(item['path'])!=item['sha256']:raise ValueError('Inline component inventory changed')
            with Path(item['path']).open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
            ih=dict(h,inventory_sha256=item['sha256'])
            proofs[view]['native_inline_paths']=inline_coverage(docs[view],graph,inventory,dict(ih,edges=multi,
                block_name=origin['block_name'],block_fingerprint_sha256=origin['block_fingerprint_sha256']),ih)
    return proofs,junctions


def check_result(data):
    if data.get('mode')!=MODE or data.get('status')!='native_direct_known_junction_mains_attributes_pending':
        raise ValueError('Unsupported direct-main result')
    if any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','whole_floor_connectivity_confirmed','human_accepted','hil_ready')):
        raise ValueError('Direct-main correspondence cannot promote topology, values or acceptance')
    rows=data['records'];used={v:set() for v in ('plan','iso')}
    if not rows or len({r['mapping_id'] for r in rows})!=len(rows):raise ValueError('Distinct direct-main records required')
    for row in rows:
        if row.get('human_accepted') is not False or row.get('physical_ports_verified') is not False:
            raise ValueError('Native correspondence is not physical or human acceptance')
        for view in used:
            path=row[view+'_edges']
            if len(path)!=1 or used[view].intersection(path):raise ValueError('Direct-main writer repeated or path not direct')
            used[view].update(path)
    return dict(status='pending',source_replay='passed',additional_main_paths=len(rows),
        whole_floor_connectivity_confirmed=False,physical_values_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Recompute plan DN/XY, compose the complete axis parent, source comparison, viewer and HIL'])


def compute(paths,policy):
    for key in ('paired','paired_receipt','template_origin'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('Direct-main dependency changed: '+key)
    parent_dir=Path(paths['paired']).resolve().parent
    if Path(paths['paired_receipt']).resolve()!=parent_dir/'source-mapping-receipt.json' or Path(paths['paired']).resolve()!=parent_dir/'mapping.json':
        raise ValueError('Canonical replayable paired mapping required')
    parent=verify_parent(parent_dir)
    if parent['mode']!=PAIRED_MODE:raise ValueError('Current paired parent required')
    receipt=load(paths['paired_receipt']);local=receipt['local_inputs'];corridor=receipt['inputs']['corridors']
    if sha(corridor['path'])!=corridor['sha256'] or parent['corridor_parent_sha256']!=corridor['sha256']:
        raise ValueError('Replayed corridor ancestor changed')
    base=load(corridor['path'])
    if base['mode']!=CORRIDOR_MODE:raise ValueError('Current native corridor ancestor required')
    graphs={};docs={}
    for view in ('plan','iso'):
        for kind in ('graph','source','devices'):
            item=local[view+'_'+kind]
            if sha(item['path'])!=item['sha256']:raise ValueError('Replayed local input changed')
        graphs[view]=load(local[view+'_graph']['path']);docs[view]=read_source(local[view+'_source']['path'])[0]
        if base[view+'_graph_sha256']!=parent[view+'_graph_sha256'] or parent[view+'_graph_sha256']!=local[view+'_graph']['sha256']:
            raise ValueError('Parent views belong to different graph versions')
    floor=policy['floor'];prefix=policy.get('mapping_prefix','')
    if not re.fullmatch('[A-Z0-9-]+',prefix):raise ValueError('Explicit direct-main mapping prefix required')
    rows,pending=discover(graphs,base['records']+parent['records'],floor)
    expected=policy.get('selected_pairs',[])
    keys=lambda rs:{(r['plan_edges'][0],r['iso_edges'][0]) for r in rs}
    if not expected or len(keys(expected))!=len(expected) or keys(expected)!=keys(rows):
        raise ValueError('Explicit complete known-junction direct-main scope changed')
    for i,row in enumerate(rows,1):row['mapping_id']=prefix+'-'+str(i).zfill(4)
    source,junctions=read_paths(docs,graphs,rows,local,load(paths['template_origin']))
    data=dict(mode=MODE,status='native_direct_known_junction_mains_attributes_pending',floor=floor,records=rows,
        source_sha256={v:local[v+'_source']['sha256'] for v in graphs},
        plan_graph_sha256=local['plan_graph']['sha256'],iso_graph_sha256=local['iso_graph']['sha256'],
        parent_paired_sha256=sha(paths['paired']),parent_corridor_sha256=corridor['sha256'],
        native_path_evidence=source,native_T_evidence=junctions,unresolved_known_junction_frontiers=pending,
        parent_path_records_preserved=len(base['records'])+len(parent['records']),
        local_graphs_mutated=False,physical_values_fused=False,whole_floor_connectivity_confirmed=False,human_accepted=False,hil_ready=False)
    check_result(data)
    for item in list(receipt['inputs'].values())+list(local.values()):
        if sha(item['path'])!=item['sha256']:raise ValueError('Input changed during direct-main source replay')
    for key in ('paired','paired_receipt','template_origin'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('Dependency changed during direct-main replay')
    return data,copy.deepcopy(local)


def implementation_hashes():
    from match_junction_rebased_paired_paths import implementation_hashes as parent_hashes
    from native_inline_joint_path_coverage import implementation_hashes as inline_hashes
    result=parent_hashes();result.update(inline_hashes());result[Path(__file__).name]=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('Direct-main implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Direct-main input changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};data,local=compute(paths,load(paths['policy']))
    if encode(data)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256'] or local!=receipt['local_inputs']:
        raise ValueError('Direct-main independent native replay differs')
    return data


def main():
    parser=argparse.ArgumentParser()
    for key in ('paired-run','template-origin','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(paired=a.paired_run/'mapping.json',paired_receipt=a.paired_run/'source-mapping-receipt.json',template_origin=a.template_origin,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    data,local=compute(paths,load(a.policy));a.output.mkdir(parents=True);out=a.output/'mapping.json';out.write_bytes(encode(data))
    (a.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={key:dict(path=str(value.resolve()),sha256=sha(value)) for key,value in paths.items()},local_inputs=local,
        implementation_sha256=implementation_hashes(),output_sha256=sha(out),human_accepted=False,hil_ready=False)))
    print(check_result(data),flush=True)


if __name__=='__main__':main()
