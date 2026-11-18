"""Batch the existing native two-arm circle owner on current plan inputs.

Candidate geometry only bounds work. Original LINE/colour/XYZ/glyph/boundary
and unique unresolved-endpoint guards decide continuity, never a nearest snap.
"""
import collections,copy,math,types
from confirm_crossview_paths import encode
from legacy_named_provider_inventory import require
from native_line_path_evidence import LAYERS
from normalize_two_arm_circle_continuity import collect,normalize,reassign_components

MODE='current_native_two_arm_circle_routes_v1'

def candidates(doc,graph):
    degree=collections.Counter(n for e in graph['edges']for n in(e.get('start_node_id'),e.get('end_node_id')))
    terminals=[n for n in graph['nodes']if degree[n['node_id']]==1 and n.get('subtype')=='unresolved_source_terminal']
    selected=[];excluded=[]
    for circle in sorted(doc.modelspace().query('CIRCLE'),key=lambda e:e.dxf.handle):
        if circle.dxf.layer not in LAYERS.values():continue
        p=list(circle.ocs().to_wcs(circle.dxf.center))[:2];radius=circle.dxf.radius
        nearby=[n for n in terminals if math.dist(p,[n['x'],n['y']])<=radius+.05]
        kinds=['center'if math.dist(p,[n['x'],n['y']])<=.05 else'rim'if abs(math.dist(p,[n['x'],n['y']])-radius)<=.05 else'other'for n in nearby]
        item=dict(circle_handle=circle.dxf.handle,position=p,radius=radius,terminal_ids=sorted(n['node_id']for n in nearby))
        if sorted(kinds)==['center','rim']:selected.append(item)
        else:excluded.append(dict(item,reason='not_exactly_two_current_unresolved_center_and_rim_endpoints'))
    return selected,excluded

def rebuild(doc,graph,rows):
    selected,excluded=candidates(doc,graph);accepted=[];held=[]
    for item in selected:
        try:accepted.extend(collect(doc,graph,[item['circle_handle']]))
        except ValueError as exc:held.append(dict(item,reason=str(exc)))
    # A terminal belongs to exactly one accepted constraint. The original
    # normalizer checks chains, source identity, floors and component conservation.
    if accepted:
        out,aliases=normalize(graph,accepted)
        if graph.get('sourceTwoArmCircleContinuity'):
            out['sourceTwoArmCircleContinuity']['previous_repair']=copy.deepcopy(graph['sourceTwoArmCircleContinuity'])
        assigned=reassign_components(rows,aliases,out['edges'])
    else:out,aliases,assigned=copy.deepcopy(graph),{},copy.deepcopy(rows)
    equipment=lambda g:{n['node_id']:n for n in g['nodes']if n.get('node_type')in('equipment','physical_equipment')}
    require(equipment(graph)==equipment(out),'two-arm reconstruction changed equipment instances')
    require(collections.Counter(r['device_name']for r in assigned)==collections.Counter(r['device_name']for r in rows),'two-arm reconstruction lost source components')
    original={e['edge_id']:e for e in graph['edges']};current={e['edge_id']:e for e in out['edges']}
    require(all(current[eid]==e for eid,e in original.items()if eid not in aliases),'two-arm reconstruction changed an unrelated edge')
    return out,assigned,dict(mode=MODE,records=accepted,held=held,excluded=excluded,edge_aliases=aliases,counts=dict(pipe_circles=len(selected)+len(excluded),candidates=len(selected),qualified=len(accepted),held=len(held),excluded=len(excluded),retired_nonphysical_endpoints=len(graph['nodes'])-len(out['nodes']),edges_before=len(graph['edges']),edges_after=len(out['edges'])),physical_Ts_added=0,physical_lengths_assigned=0,human_accepted=False)

def circle_omissions(graph,edge,gaps,system):
    from member_external_anchored_routes import omission_evidence
    result=[]
    for gap in gaps:
        try:result.extend(omission_evidence(edge,[gap],system));continue
        except ValueError:pass
        matches=[]
        handles=edge.get('source_circle_continuity',{}).get('circle_handles',[])
        for row in graph.get('sourceTwoArmCircleContinuity',{}).get('records',[]):
            if row['circle_handle']not in handles or row['system']!=system or row['blockers']or row['physical_T_proven']is not False or row['physical_connector_length_mm']is not None:continue
            points=[c['endpoint'][:2]for c in row['contacts']]
            if any(all(math.dist(a,b)<=.05 for a,b in zip(gap,p))for p in(points,list(reversed(points)))):matches.append(row)
        require(len(matches)==1,'external gap lacks its exact replayed native two-arm circle')
        result.append(dict(kind='replayed_native_two_arm_circle_unknown_connector_length',points=copy.deepcopy(gap),evidence=copy.deepcopy(matches[0]),physical_connector_length_mm=None))
    return result

def discover_external(plan,axis,parent,interfaces,provider,floor):
    import member_external_anchored_routes as original
    namespace=dict(original.outward_candidates.__globals__)
    namespace['omission_evidence']=lambda e,g,s:circle_omissions(plan,e,g,s)
    outward=types.FunctionType(original.outward_candidates.__code__,namespace,original.outward_candidates.__name__)
    namespace=dict(original.discover.__globals__);namespace['outward_candidates']=outward
    discover=types.FunctionType(original.discover.__code__,namespace,original.discover.__name__)
    known={r['edge_id']for r in provider['records']if r['has_existing_correspondence']}
    reading=copy.deepcopy(parent);reading['original_external_ports']=[p for p in parent['original_external_ports']if p['axis_edge_id']not in known]
    records,held=discover(plan,axis,reading,interfaces,provider,floor)
    return records,held,dict(original_external_ports=len(parent['original_external_ports']),already_mapped_axis_edges=sorted({p['axis_edge_id']for p in parent['original_external_ports']if p['axis_edge_id']in known}),pending_external_ports=len(reading['original_external_ports']))

def inherit(original,records,member_local,plan,reading_bindings):
    from rebuild_member_external_routes import inherit as original_inherit
    extended,local=original_inherit(original,records,dict(member_local_graph=member_local),plan)
    result=copy.deepcopy(original)
    for key in('records','remaining_horizontal_attributes','member_domain_observations','ordinary_junction_mappings','counts','current_horizontal_frontier'):result[key]=extended[key]
    result.update(mode=MODE,native_two_arm_external_records=copy.deepcopy(records),current_native_plan_reading_graphs=copy.deepcopy(reading_bindings),old_provider_observations_preserved=True,source_canonical_graphs_changed=False,physical_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    before={r['edge_id']:r for r in original['records']};new={r['axis_edge_id']for r in records}
    require(all(r==before[r['edge_id']]for r in result['records']if r['edge_id']not in new),'two-arm route overwrote an old correspondence')
    require(result['remaining_horizontal_attributes']==original['remaining_horizontal_attributes']and result['current_component_inventory']==original['current_component_inventory'],'two-arm topology changed attributes or component rendering')
    return result,local
