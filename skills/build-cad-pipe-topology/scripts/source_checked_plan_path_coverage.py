"""Add explicitly replayed plan crossover paths to the old LINE audit.

The single-path contract and result stay unchanged. Separate paths require
the historical source-reviewed circle and each real opposite-service crossing.
"""
from native_path_coverage_audit import audit as single_audit
from source_reviewed_circle_branch_evidence import collect,branch_coverage


def audit(doc,graph,policy,source_hash,graph_hash,tol=.05):
    by={e['edge_id']:e for e in graph['edges']};selected=policy.get('edges',[])
    if len(by)!=len(graph['edges']) or not selected or len(set(selected))!=len(selected) or any(eid not in by for eid in selected):raise ValueError('invalid plan source path scope')
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or tol!=.05:raise ValueError('plan path source/hash/tolerance differs')
    if all(len(by[eid].get('attribute_paths',[]))==1 for eid in selected):return single_audit(doc,graph,policy,source_hash,graph_hash,tol)
    rows=[];nodes={n['node_id']:n for n in graph['nodes']}
    for eid in selected:
        edge=by[eid]
        if len(edge.get('attribute_paths',[]))==1:
            rows.extend(single_audit(doc,graph,dict(policy,edges=[eid]),source_hash,graph_hash,tol)['edges']);continue
        taps=[nodes[nid] for nid in (edge.get('start_node_id'),edge.get('end_node_id')) if nid in nodes and nodes[nid].get('source_reviewed_circle')]
        if len(taps)!=1:raise ValueError('separate plan paths lack one reviewed circle branch')
        junction=collect(doc,graph,taps[0]['node_id'],source_hash,graph_hash)
        if [r['edge_id'] for r in junction['junctions'][0]['source_rays'] if r.get('scope')=='historical_source_reviewed_circle_rim']!=[eid]:raise ValueError('separate plan path is not the reviewed branch')
        proof=branch_coverage(doc,graph,edge,source_hash,graph_hash)
        segments=[dict(segment,path_index=p['original_path_index']) for p in proof['paths'] for segment in p['coverage']['segments']]
        rows.append(dict(edge_id=eid,system=edge['system'],segments=segments,coverage_mode='native_plan_paths_excluding_replayed_crossovers',
            source_covered_drawing_length=sum(s['drawing_length'] for s in segments),unverified_drawing_length=0,
            source_path_evidence=proof,junction_evidence=junction,physical_length='unknown',status='source_geometry_audit_unreviewed'))
    return dict(status='partial_source_coverage_not_physical_length',source_sha256=source_hash,graph_sha256=graph_hash,edges=rows,graph_mutated=False,hil_ready=False,
        limitations=['Every separate plan path and opposite-service crossover is rechecked against the source.','The excluded crossover and unshown equipment connection are not measured lengths.'])
