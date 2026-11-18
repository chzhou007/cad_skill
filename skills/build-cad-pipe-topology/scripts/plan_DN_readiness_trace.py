"""Explain unresolved local DN in batches without assigning pipe attributes.

Incidence groups locate common source barriers; they are not DN propagation
paths, correspondence, source replay or human acceptance.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path

MODE='complete_plan_DN_readiness_trace_v1'
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))

def collect(graph,result,floor,source_hash,graph_hash):
    if type(floor)is not int or result['source_sha256']!=source_hash or result['graph_sha256']!=graph_hash:raise ValueError('DN trace source or graph binding differs')
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']};rows={r['edge_id']:r for r in result['records']}
    if len(nodes)!=len(graph['nodes'])or len(edges)!=len(graph['edges'])or len(rows)!=len(result['records'])or set(rows)!=set(edges):raise ValueError('complete unique local DN/graph inventory required')
    adj=collections.defaultdict(set)
    for eid,e in edges.items():
        if e['system']not in ('supply','return')or rows[eid]['system']!=e['system']:raise ValueError('DN trace service differs')
        for side in ('start','end'):
            nid=e[side+'_node_id']
            if nid is None:
                boundary=e.get('endpoint_semantics',{}).get(side,{})
                if boundary.get('kind')!='source_boundary' or not boundary.get('id')or boundary['id']!=e.get(side+'_boundary_id'):raise ValueError('untyped missing pipe endpoint')
                continue
            if nid not in nodes or nodes[nid]['floor']!=floor:raise ValueError('DN trace endpoint floor differs')
            adj[nid].add(eid)
    unknown={eid for eid,r in rows.items()if r['status']=='unresolved'};net=collections.defaultdict(set);roles=result['roles']
    for nid,role in roles.items():
        ids=role['through']+[role['branch']];node=nodes.get(nid);proof=role['source_T_proof']
        if (len(role['through'])!=2 or len(set(ids))!=3 or set(ids)!=adj[nid]or not node or node['node_type']not in ('tee','physical_junction')or node.get('review_required')is True
            or len({edges[e]['system']for e in ids})!=1 or proof['source_sha256']!=source_hash or proof['graph_sha256']!=graph_hash):raise ValueError('native T incidence or source binding differs')
        selected=set(ids)&unknown
        for eid in selected:net[eid].update(selected-{eid})
    if any(rows[e]['nominal_mm']is not None or rows[e]['lineage']or rows[e]['scope_paths']!=edges[e]['attribute_paths']for e in unknown):raise ValueError('unresolved DN has contradictory value, source lineage or scope')
    unseen=set(unknown);groups=[];edge_groups={}
    while unseen:
        todo=[min(unseen)];members=set()
        while todo:
            eid=todo.pop()
            if eid in members:continue
            members.add(eid);todo.extend(net[eid]-members)
        unseen-=members;frontier={};missing=[];transitions=[];contacts=[]
        for nid in sorted({n for e in members for n in (edges[e]['start_node_id'],edges[e]['end_node_id'])if n is not None}):
            role=roles.get(nid);node=nodes[nid]
            if role:
                contacts.append(nid)
                for eid in sorted(adj[nid]-members):
                    r=rows[eid];frontier[eid]=dict(edge_id=eid,status=r['status'],nominal_mm=r['nominal_mm'],
                        annotation_barriers=result.get('annotation_barriers',{}).get(eid,[]),source_lineage=r.get('lineage',[]))
                values=[rows[e]['nominal_mm']for e in role['through']]
                if role['branch']in members and all(isinstance(v,(float,int))and not isinstance(v,bool)and math.isfinite(v)and v>0 for v in values)and values[0]!=values[1]:
                    transitions.append(dict(node_id=nid,through_edges=role['through'],through_nominal_mm=values,branch_edge=role['branch']))
            elif node['node_type']in ('tee','physical_junction'):
                missing.append(dict(node_id=nid,source_issue=result.get('source_T_exceptions',{}).get(nid,'native T transfer not supplied')))
        barriers=[r['edge_id']for r in frontier.values()if r['status']=='annotation_blocked'];source_gaps=[r['edge_id']for r in frontier.values()if r['status']=='source_scope_unverified']
        scope_boundaries=[r['edge_id']for r in frontier.values()if r['status']=='reviewed_plan_DN_scope']
        primary=('source_annotation_scope_barrier'if barriers else 'source_T_evidence_missing'if missing else 'source_path_scope_barrier'if source_gaps
            else 'DN_transition_branch_scope_unassigned'if transitions else 'no_source_DN_seed_reaches_checked_group')
        group_id=f'DN-READINESS-F{floor}-'+hashlib.sha256(encoded(sorted(members))).hexdigest()[:12]
        group=dict(group_id=group_id,floor=floor,system=edges[min(members)]['system'],edges=sorted(members),primary_reason=primary,
            source_checked_T_contacts=contacts,frontier=list(frontier.values()),annotation_barrier_edges=barriers,source_path_barrier_edges=source_gaps,
            missing_T_evidence=missing,distinct_through_DN_at_unassigned_branch=transitions,reviewed_scope_boundaries=scope_boundaries,
            branch_defaults_with_unverified_frontiers=sorted(members&set(result.get('branch_default_regions_with_unverified_frontiers',[]))),
            grouping_basis='same_service_unknown_edges_incident_at_current_source_checked_Ts_not_DN_transfer_or_mapping',
            nominal_mm_assigned=None,physical_length_assigned=None,human_accepted=False)
        groups.append(group)
        for eid in members:edge_groups[eid]=group_id
    return dict(mode=MODE,floor=floor,source_sha256=source_hash,graph_sha256=graph_hash,groups=groups,
        edge_outcomes=[dict(edge_id=eid,local_status=rows[eid]['status'],trace_group_id=edge_groups.get(eid))for eid in sorted(edges)],
        counts=dict(all_edges=len(edges),unresolved_edges=len(unknown),trace_groups=len(groups),primary_reason_edges=dict(collections.Counter({reason:sum(len(g['edges'])for g in groups if g['primary_reason']==reason)for reason in sorted({g['primary_reason']for g in groups})}))),
        source_stage_reexecuted=False,values_assigned=0,graph_mutated=False,crossview_correspondences_added=0,human_accepted=False)

def produce(manifest_path,DN_run,output):
    output=Path(output).resolve();DN_run=Path(DN_run).resolve()
    if output.exists():raise FileExistsError(output)
    receipt_path=DN_run/'local-detail-plan-DN-receipt.json';result_path=DN_run/'local-detail-plan-DN-results.json';receipt=load(receipt_path);result=load(result_path);manifest=load(manifest_path)
    if sha(manifest_path)!=receipt['manifest']['sha256']or sha(result_path)!=receipt['output_sha256']or receipt['mode']!=result['mode']:raise ValueError('qualified local DN inputs changed')
    inputs={str(Path(p).resolve()):sha(p)for p in (manifest_path,receipt_path,result_path)};floors={}
    for item in manifest['plans']:
        floor=item['floor'];bound=item['inputs']
        for spec in bound.values():
            if sha(spec['path'])!=spec['sha256']:raise ValueError('native floor input changed')
            inputs[str(Path(spec['path']).resolve())]=spec['sha256']
        floors[str(floor)]=collect(load(bound['graph']['path']),result['floors'][str(floor)],floor,bound['source']['sha256'],bound['graph']['sha256'])
    report=dict(mode=MODE,floors=floors,inputs=inputs,implementation_sha256=sha(__file__),source_DN_stage=receipt['mode'],source_stage_reexecuted=False,
        aggregate_counts=dict(all_edges=sum(f['counts']['all_edges']for f in floors.values()),unresolved_edges=sum(f['counts']['unresolved_edges']for f in floors.values()),trace_groups=sum(f['counts']['trace_groups']for f in floors.values())),
        values_assigned=0,graph_mutated=False,human_accepted=False)
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('inputs changed while deriving readiness trace')
    output.mkdir(parents=True);(output/'readiness-trace.json').write_bytes(encoded(report));(output/'arguments.json').write_bytes(encoded(dict(manifest=str(Path(manifest_path).resolve()),DN_run=str(DN_run))))
    return report

def verify(output):
    import tempfile
    output=Path(output).resolve();saved=load(output/'readiness-trace.json');args=load(output/'arguments.json')
    if sha(__file__)!=saved['implementation_sha256']or any(sha(p)!=h for p,h in saved['inputs'].items()):raise ValueError('readiness trace inputs or implementation changed')
    with tempfile.TemporaryDirectory(prefix='.DN-readiness-replay-',dir=output.parent)as name:
        fresh=produce(args['manifest'],args['DN_run'],Path(name)/'trace')
        if encoded(fresh)!=(output/'readiness-trace.json').read_bytes():raise ValueError('readiness trace replay differs')
    return dict(status='pending',artifact_trace_replay='passed',source_stage_reexecuted=False,values_assigned=0,graph_mutated=False,human_accepted=False,
        counts=saved['aggregate_counts'],pending=['Resolve upstream evidence before DN assignment; trace groups are not extra HIL questions or pipe connections'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path);p.add_argument('--DN-run',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.DN_run or a.output:p.error('verification uses its original bound inputs')
        result=verify(a.verify_output)
    else:
        if not(a.manifest and a.DN_run and a.output):p.error('manifest, DN-run and new output required')
        result=produce(a.manifest,a.DN_run,a.output)
    print(json.dumps(result.get('aggregate_counts',result),ensure_ascii=False))
if __name__=='__main__':main()
