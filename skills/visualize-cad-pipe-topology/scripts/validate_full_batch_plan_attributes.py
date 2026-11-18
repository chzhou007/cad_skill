"""Validate the derived viewer carrier against its native composition proof."""
import math,re

FIELD='batch_plan_attribute_scopes';ROOT='sourceFullPlanBatchAttributes'


def validate(graph,native_doc=None,native_source_sha256=None):
    stage=graph.get(ROOT);owners=[e for e in graph['edges']if FIELD in e]
    if not stage and not owners:return None
    proof=graph.get('sourceCheckedCrossViewAttributeEvidence',{}).get('full_batch_plan_attribute_fusion_audit')
    if (not stage or not proof or stage!=proof.get('stage')or stage.get('mode')!='complete_plan_batch_axis_attribute_composition_v1'
        or stage.get('source_verification_pending')is not False or proof.get('human_accepted')is not False or proof.get('hil_ready')is not False):
        raise ValueError('complete batch source composition proof missing or differs')
    source=stage['source_hashes'];digest=re.compile('[0-9a-f]{64}').fullmatch
    if not all(isinstance(source[k],str)and digest(source[k])for k in ('identity_graph','axis_source','mapping_receipt','DN_receipt','parent_graph')):
        raise ValueError('complete batch source identities invalid')
    if native_doc is not None and native_source_sha256!=source['axis_source']:raise ValueError('complete batch native axis source differs')
    indexed={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']};claimed=set()
    for record in stage['records']:
        floor=str(record['floor']);ids=record['iso_edges'];plan=record['plan_edges'];DN=record['plan_DN_records'];nominal=record['plan_drawn_nominal_mm']
        if (not ids or len(set(ids))!=len(ids)or not plan or len(set(plan))!=len(plan)or len(DN)!=len(plan)
            or {r['edge_id']for r in DN}!=set(plan)or record.get('human_accepted')is not False or record.get('related_HIL_confirmation_inherited')is not False
            or record.get('whole_installed_length_mm')is not None or record['graph_sha256']!=dict(plan=source['plan_graphs'][floor],iso=source['identity_graph'])
            or record['source_sha256']!=dict(plan=source['plan_sources'][floor],iso=source['axis_source'])):raise ValueError('complete batch record scope differs')
        for row in DN:
            value=row['nominal_mm']
            if row['system']!=record['system']or row['human_accepted']is not False:raise ValueError('current plan service or review state differs')
            if value is not None and (isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0):raise ValueError('invalid current plan DN')
        values={r['nominal_mm']for r in DN};expected=next(iter(values))if len(values)==1 and None not in values else None
        if nominal!=expected:raise ValueError('current group DN cannot choose a missing or conflicting plan value')
        metric=record['horizontal_projection']
        if metric:
            pieces=metric['pieces'];keys=[(p['plan_edge'],p['path_index'],p['segment_index'])for p in pieces]
            if (not pieces or len(keys)!=len(set(keys))or not all(p['plan_edge']in plan and p['length_mm']>0 for p in pieces)
                or abs(sum(p['length_mm']for p in pieces)-metric['value_mm'])>.0001):raise ValueError('current native plan metric pieces differ')
        if len(ids)>1 and (record['group_scope_not_allocated_to_child_edges']is not True or record['whole_axis_nominal_mm']is not None
            or record['complete_horizontal_centerline_route_mm']is not None):raise ValueError('group route cannot become child edge values')
        for eid in ids:
            edge=indexed.get(eid)
            if eid in claimed or edge is None or edge.get(FIELD)!=record or edge['system']!=record['system']:raise ValueError('current batch edge carrier missing, duplicated or differs')
            claimed.add(eid)
            if record.get('axis_horizontal_scope_paths'):
                if (len(ids)!=1 or record['kind']!='same_floor_T_to_T_main'or record['axis_horizontal_scope_paths']!=edge['attribute_paths']
                    or any(nodes[edge[k]]['node_type']not in ('tee','physical_junction')or nodes[edge[k]]['floor']!=record['floor']for k in ('start_node_id','end_node_id'))):
                    raise ValueError('current whole-main axis extent differs')
            elif record['whole_axis_nominal_mm']is not None or record['complete_horizontal_centerline_route_mm']is not None:raise ValueError('whole-main values have no source axis extent')
    if claimed!={e['edge_id']for e in owners}or len(claimed)!=stage['current_axis_edge_scopes']:raise ValueError('current complete batch edge inventory differs')
    return dict(current_edges=len(claimed),source_accepted=False,human_accepted=False)
