"""Reuse native inline and crossover readers after complete batch matching."""
import copy
from native_inline_joint_path_coverage import collect as inline
from anchored_floor_main_plan_attributes import inline_projection
from inherited_circle_branch_inventory import path_evidence
from native_plan_projection_lengths import lengths


def extend(doc,graph,inventory,rows,previous,units,hashes,template_origin):
    by={e['edge_id']:e for e in graph['edges']};old={r['mapping_id']:r for r in previous};records=[]
    if len(old)!=len(previous)or set(old)!={r['mapping_id']for r in rows}:raise ValueError('complete mapping and prior metric population required')
    if (template_origin.get('confirmation_basis')!='source_geometry_calibrated'or not template_origin.get('expert_evidence')
        or not template_origin.get('block_name')or not template_origin.get('block_fingerprint_sha256')):
        raise ValueError('inherited native inline template origin required')
    for mapping in rows:
        mid=mapping['mapping_id'];prior=old[mid]
        if any(prior[k]!=mapping[k]for k in ('plan_edges','iso_edges')):raise ValueError('metric mapping scope differs')
        record=dict(mapping_id=mid,plan_edges=copy.deepcopy(mapping['plan_edges']),iso_edges=copy.deepcopy(mapping['iso_edges']),
            projection=copy.deepcopy(prior['projection']),previous_reason=prior.get('reason'),reader='inherited_batch_native_projection'if prior['projection']is not None else None,attempts=[])
        if prior['projection']is not None:records.append(record);continue
        selected=[by[eid]for eid in mapping['plan_edges']]
        if any(e.get('source_view_context')is not None for e in selected):
            record['reason']='confirmed_detail_expression_has_no_separately_proved_physical_plan_length';records.append(record);continue
        if len(selected)==1:
            edge=selected[0];eid=edge['edge_id']
            if edge.get('source_flexible_joints'):
                try:
                    proof=inline(doc,graph,inventory,dict(hashes,edges=[eid],block_name=template_origin['block_name'],block_fingerprint_sha256=template_origin['block_fingerprint_sha256']),hashes)
                    record.update(projection=inline_projection(graph,proof['records'][0],mapping,units),source_evidence=proof,reader='inherited_inline_pipe_XY')
                except ValueError as exc:record['attempts'].append(dict(reader='native_inline',reason=str(exc)))
            if record['projection']is None and edge.get('source_normalized_crossovers'):
                try:
                    proof=path_evidence(doc,graph,edge,hashes['source_sha256'],hashes['graph_sha256'])['evidence']
                    segments=[dict(s,path_index=p['original_path_index'])for p in proof['paths']for s in p['coverage']['segments']]
                    coverage=dict(edges=[dict(edge_id=eid,system=edge['system'],segments=segments,coverage_mode='native_plan_paths_excluding_replayed_crossovers',source_path_evidence=proof)])
                    record.update(projection=lengths(graph,coverage,mapping,units),source_evidence=proof,reader='inherited_native_crossover_pipe_XY')
                except ValueError as exc:record['attempts'].append(dict(reader='native_crossover',reason=str(exc)))
        if record['projection']is None:record['reason']=prior['reason']
        records.append(record)
    return dict(records=records,prior_metric_scopes_retained=sum(r['projection']is not None for r in previous),
        additional_metric_scopes=sum(r['reader']in ('inherited_inline_pipe_XY','inherited_native_crossover_pipe_XY')for r in records),
        local_graph_mutated=False,missing_physical_lengths_filled_with_zero=False,physical_gap_lengths_assigned=0,human_accepted=False)
