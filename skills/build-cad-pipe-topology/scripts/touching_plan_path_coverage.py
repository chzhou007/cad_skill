"""Add exact-touching plan chunks to the unchanged reviewed-path reader.

Native audit runs on a private joined scope. Its segments are mapped back to
the original path indices; unrelated single/crossover scopes keep their reader.
"""
import copy
from source_checked_plan_path_coverage import audit as inherited_audit
from native_touching_plan_path_chunks import evaluate


def audit(doc,graph,policy,source_hash,graph_hash,tol=.05):
    by={e['edge_id']:e for e in graph['edges']};selected=policy.get('edges',[])
    if (len(by)!=len(graph['edges']) or not selected or len(set(selected))!=len(selected) or any(eid not in by for eid in selected)
        or policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or tol!=.05):
        raise ValueError('touching-aware plan path scope differs')
    if any(not by[eid].get('attribute_paths') or any(len(path)<2 for path in by[eid]['attribute_paths']) for eid in selected):
        raise ValueError('empty plan path chunk')
    touching=[eid for eid in selected if len(by[eid].get('attribute_paths',[]))>1
              and all(a[-1]==b[0] for a,b in zip(by[eid]['attribute_paths'],by[eid]['attribute_paths'][1:]))]
    if not touching:return inherited_audit(doc,graph,policy,source_hash,graph_hash,tol)
    nodes={n['node_id']:n for n in graph['nodes']};rows=[];proofs=[]
    for eid in selected:
        if eid not in touching:
            rows.extend(inherited_audit(doc,graph,dict(policy,edges=[eid]),source_hash,graph_hash,tol)['edges']);continue
        edge=by[eid];floors={nodes.get(edge.get(k),{}).get('floor') for k in ('start_node_id','end_node_id')}
        if len(floors)!=1 or None in floors:raise ValueError('touching path has no single local floor')
        _,proof,locations=evaluate(doc,graph,dict(policy,edges=[eid],floor=next(iter(floors)),view_kind='floor_plan'),source_hash,graph_hash)
        row=copy.deepcopy(proof['coverage']['edges'][0])
        for segment in row['segments']:
            original=locations[(eid,segment['index'])]
            if original['points']!=[segment['start'],segment['end']]:raise ValueError('native coverage lost original chunk identity')
            segment.update(projection_segment_index=segment['index'],index=original['segment_index'],path_index=original['path_index'])
        row.update(coverage_mode='native_exact_touching_path_chunks_no_added_span',source_path_evidence=proof)
        rows.append(row);proofs.append(proof)
    return dict(status='partial_source_coverage_not_physical_length',source_sha256=source_hash,graph_sha256=graph_hash,
        edges=rows,graph_mutated=False,hil_ready=False,touching_path_chunk_evidence=proofs,
        limitations=['Exact-touching chunks are read privately and every piece retains its original index. No span or physical connection is added.',
                    'Other single and reviewed crossover paths keep the inherited source reader; unknown gaps remain unsupported.'])
