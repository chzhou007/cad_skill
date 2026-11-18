"""Compose complete source-owned batch scopes over the preserved axis parent."""
import copy,math
from native_exploded_caption_identity import apply_aliases
from match_source_checked_crossview_paths import selected_snapshot
from attach_anchored_floor_main_attributes import horizontal_domain

FIELD='batch_plan_attribute_scopes'
ROOT='sourceFullPlanBatchAttributes'
MODE='complete_plan_batch_axis_attribute_composition_v1'
OLD_FIELDS={'cross_view_attributes','anchored_floor_main_attributes','external_feed_plan_attributes','network_named_lower_plan_attributes',
    'plan_segment_attributes','axis_riser_attributes','current_floor_plan_scope_evidence','current_named_prefix_source_evidence'}
NODE_FIELDS={'source_external_destination_context'}


def rebase(parent,before,after,aliases):
    old={e['edge_id']:e for e in before['edges']};current={e['edge_id']:e for e in after['edges']}
    if len(old)!=len(before['edges'])or set(old)!=set(current)or set(old)!={e['edge_id']for e in parent['edges']}:raise ValueError('complete source and parent pipe identities required')
    for edge in parent['edges']:
        if {k:v for k,v in edge.items()if k not in OLD_FIELDS}!=old[edge['edge_id']]:raise ValueError('parent geometry or components differ from native identity source')
        if any(edge.get(k)in aliases for k in ('start_node_id','end_node_id'))and OLD_FIELDS.intersection(edge):
            raise ValueError('identity-affected old attributes require semantic invalidation before composition')
    nodes={n['node_id']:n for n in before['nodes']}
    if any({k:v for k,v in n.items()if k not in NODE_FIELDS}!=nodes[n['node_id']]for n in parent['nodes']):raise ValueError('parent physical node differs')
    result=apply_aliases(parent,aliases);new_nodes={n['node_id']:n for n in after['nodes']}
    if any({k:v for k,v in n.items()if k not in NODE_FIELDS}!=new_nodes[n['node_id']]for n in result['nodes']):raise ValueError('native identity node migration differs')
    if any({k:v for k,v in e.items()if k not in OLD_FIELDS}!=current[e['edge_id']]for e in result['edges']):raise ValueError('native identity pipe reference migration differs')
    if any(k in parent for k in (ROOT,'sourceExplodedCaptionIdentity')):raise ValueError('batch identity already composed')
    result['sourceExplodedCaptionIdentity']=copy.deepcopy(after['sourceExplodedCaptionIdentity'])
    result['derivedEvidenceInvalidation']=copy.deepcopy(after['derivedEvidenceInvalidation'])
    return result


def append(parent,before,axis,aliases,batch,plans,diameters,metric_extensions,angles,hashes):
    if batch['identity_graph_sha256']!=hashes['identity_graph']:raise ValueError('current source identity batch differs')
    result=rebase(parent,before,axis,aliases);targets={e['edge_id']:e for e in result['edges']};rows=[];claimed=set()
    for floor,data in batch['floors'].items():
        values={r['edge_id']:r for r in diameters['floors'][floor]['records']};metrics={r['mapping_id']:r for r in batch['metrics'][floor]}
        plan=plans[floor]
        if diameters['floors'][floor]['graph_sha256']!=hashes['plan_graphs'][floor]:raise ValueError('current plan DN belongs to another topology')
        for mapping in data['records']:
            if (selected_snapshot(plan,mapping['plan_edges'])!=mapping['plan_snapshot']or selected_snapshot(axis,mapping['iso_edges'])!=mapping['iso_snapshot']
                or any(eid in claimed for eid in mapping['iso_edges'])):raise ValueError('changed mapping snapshots or repeated axis attribute writer')
            claimed.update(mapping['iso_edges']);DN=[copy.deepcopy(values[eid])for eid in mapping['plan_edges']]
            known={v['nominal_mm']for v in DN};nominal=next(iter(known))if None not in known and len(known)==1 else None
            if any(v['system']!=mapping['system']or v.get('human_accepted')is not False or
                (v['nominal_mm']is not None and (isinstance(v['nominal_mm'],bool)or not isinstance(v['nominal_mm'],(int,float))or not math.isfinite(v['nominal_mm'])or v['nominal_mm']<=0))for v in DN):
                raise ValueError('invalid source-owned plan DN or service')
            metric=metric_extensions.get(mapping['mapping_id'],{}).get('projection')or metrics[mapping['mapping_id']]['projection']
            if metric:
                pieces=metric['pieces'];keys=[(p['plan_edge'],p['path_index'],p['segment_index'])for p in pieces]
                if len(keys)!=len(set(keys))or abs(sum(p['length_mm']for p in pieces)-metric['value_mm'])>.0001:raise ValueError('native source metric pieces differ or repeat')
            scope=dict(mapping_id=mapping['mapping_id'],kind=mapping['kind'],floor=int(floor),system=mapping['system'],
                plan_edges=copy.deepcopy(mapping['plan_edges']),iso_edges=copy.deepcopy(mapping['iso_edges']),
                plan_drawn_nominal_mm=nominal,plan_DN_records=DN,horizontal_projection=copy.deepcopy(metric),
                complete_horizontal_centerline_route_mm=None,whole_axis_nominal_mm=None,whole_installed_length_mm=None,
                group_scope_not_allocated_to_child_edges=len(mapping['iso_edges'])>1,source_sha256=dict(plan=hashes['plan_sources'][floor],iso=hashes['axis_source']),
                graph_sha256=dict(plan=hashes['plan_graphs'][floor],iso=hashes['identity_graph']),
                mapping_receipt_sha256=hashes['mapping_receipt'],plan_DN_receipt_sha256=hashes['DN_receipt'],
                source_extent='drawn_plan_scope_only_not_unshown_axis_drop_or_equipment_connector',human_accepted=False,related_HIL_confirmation_inherited=False)
            if mapping['kind']=='same_floor_T_to_T_main'and len(mapping['iso_edges'])==1 and len(mapping['plan_edges'])==1:
                try:
                    paths=horizontal_domain(axis,mapping,angles)
                    edge=next(e for e in plan['edges']if e['edge_id']==mapping['plan_edges'][0]);nodes={n['node_id']:n for n in plan['nodes']}
                    if len(edge['attribute_paths'])!=1:raise ValueError('multiple drawn paths retain unknown omitted lengths')
                    for nid,point in zip(('start_node_id','end_node_id'),(edge['attribute_paths'][0][0],edge['attribute_paths'][0][-1])):
                        n=nodes[edge[nid]]
                        if n['node_type']not in ('tee','physical_junction')or math.dist(point,[n['x'],n['y']])>.05:raise ValueError('plan source paths do not cover both T endpoints')
                    scope['axis_horizontal_scope_paths']=[copy.deepcopy(paths)]
                    scope['whole_axis_nominal_mm']=nominal
                    if metric and metric['status']=='native_plan_horizontal_projection_partial_length':scope['complete_horizontal_centerline_route_mm']=metric['value_mm']
                except ValueError as exc:scope['whole_horizontal_scope_pending_reason']=str(exc)
            for eid in mapping['iso_edges']:targets[eid][FIELD]=copy.deepcopy(scope)
            rows.append(scope)
    result[ROOT]=dict(mode=MODE,records=rows,
        current_axis_edge_scopes=len(claimed),previous_attributes_preserved=True,identity_aliases=copy.deepcopy(aliases),
        previous_metadata=copy.deepcopy(parent.get('metadata',{})),previous_invalidation=copy.deepcopy(parent.get('derivedEvidenceInvalidation')),
        source_hashes=copy.deepcopy(hashes),source_verification_pending=False,human_accepted=False,related_HIL_confirmation_inherited=False)
    result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_complete_plan_batch_attributes')
    restore(result,parent)
    return result


def restore(graph,parent):
    restored=copy.deepcopy(graph);stage=restored.pop(ROOT)
    if (stage.get('mode')!=MODE or stage.get('source_verification_pending')is not False or stage.get('previous_attributes_preserved')is not True
        or stage.get('human_accepted')is not False or stage.get('related_HIL_confirmation_inherited')is not False
        or graph.get('metadata',{}).get('hil_ready')is not False):raise ValueError('complete batch composition state differs')
    owned={}
    for record in stage['records']:
        for eid in record['iso_edges']:
            if eid in owned:raise ValueError('batch root repeats a physical edge writer')
            owned[eid]=record
    if len(owned)!=stage['current_axis_edge_scopes']:raise ValueError('batch root scope count differs')
    found=set()
    for edge in graph['edges']:
        if edge['edge_id']in owned:
            if edge.get(FIELD)!=owned[edge['edge_id']]:raise ValueError('root and edge current source scopes differ')
            found.add(edge['edge_id'])
        elif FIELD in edge:raise ValueError('unowned current batch edge scope')
    if found!=set(owned):raise ValueError('batch root references a missing edge')
    restored.pop('sourceExplodedCaptionIdentity');restored['derivedEvidenceInvalidation']=stage['previous_invalidation'];restored['metadata']=stage['previous_metadata']
    for edge in restored['edges']:edge.pop(FIELD,None)
    restored=apply_aliases(restored,{v:k for k,v in stage['identity_aliases'].items()})
    if restored!=parent:raise ValueError('original complete parent is not exactly restorable')
    return restored
