"""Project checked plan DN ranges; close only proven horizontal T-to-T mains."""
import copy,math,re
from confirmed_detail_projection import is_unmeasured_detail

def main_route_complete(record,axis,plan,angles):
    if record['kind']!='main_between_equipment_branches' or len(record['iso_edges'])!=1 or len(record['plan_edges'])!=1 or not angles:return False
    nodes={n['node_id']:n for n in axis['nodes']};pnodes={n['node_id']:n for n in plan['nodes']};ae={e['edge_id']:e for e in axis['edges']}[record['iso_edges'][0]];pe={e['edge_id']:e for e in plan['edges']}[record['plan_edges'][0]]
    for graph_nodes,edge in ((nodes,ae),(pnodes,pe)):
        if edge.get('system')!=record['system']:return False
        for names in (('floor_start','start_floor'),('floor_end','end_floor')):
            declared=[edge[k] for k in names if k in edge]
            if not declared or any(v!=record['floor'] for v in declared):return False
        if any(graph_nodes.get(edge[k],{}).get('node_type') not in ('tee','physical_junction') or graph_nodes[edge[k]].get('floor')!=record['floor'] or graph_nodes[edge[k]].get('review_required') is True for k in ('start_node_id','end_node_id')):return False
        paths=edge.get('attribute_paths',[])
        if len(paths)!=1 or len(paths[0])!=2 or any(len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in paths[0]) or math.dist(*paths[0])<=.05:return False
    a,b=ae['attribute_paths'][0];bearing=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%180
    return any(min(abs(bearing-(v%180)),180-abs(bearing-(v%180)))<=.1 for v in angles)

def apply(axis,mapping,plan,evidence,evidence_hash,angles=()):
    if not isinstance(evidence_hash,str) or not re.fullmatch('[0-9a-f]{64}',evidence_hash):raise ValueError('invalid plan DN evidence hash')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v%180-90)<.5 for v in angles):raise ValueError('invalid horizontal axes; plumb cannot be declared horizontal')
    rows={r['edge_id']:r for r in evidence['records']};plan_edges={e['edge_id']:e for e in plan['edges']}
    if len(rows)!=len(evidence['records']):raise ValueError('duplicate plan DN owners')
    out=copy.deepcopy(axis);axis_edges={e['edge_id']:e for e in out['edges']};proof=[]
    for record in mapping['records']:
        values=[]
        for eid in record['plan_edges']:
            row=rows.get(eid)
            if not row or row['system']!=record['system'] or row['scope_paths']!=plan_edges[eid]['attribute_paths'] or row['scope']!='native_plan_drawn_pipe_paths_only' or row['human_accepted'] is not False:raise ValueError('plan DN scope does not match current mapped source')
            values.append(row)
        known=[r['nominal_mm'] for r in values];nominal=known[0] if None not in known and len(set(known))==1 else None
        if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0) for v in known):raise ValueError('invalid source nominal DN')
        if nominal is not None and (isinstance(nominal,bool) or not isinstance(nominal,(int,float)) or not math.isfinite(nominal) or nominal<=0):raise ValueError('invalid source nominal DN')
        whole=nominal is not None and main_route_complete(record,out,plan,angles)
        for eid in record['iso_edges']:
            attributes=axis_edges[eid]['cross_view_attributes'];diameter=attributes['diameter']
            if attributes['mapping_id']!=record['mapping_id'] or attributes['plan_edges']!=record['plan_edges'] or attributes['iso_edges']!=record['iso_edges'] or attributes['system']!=record['system'] or attributes['human_accepted'] is not False:raise ValueError('axis attribute correspondence differs')
            detail=any(plan_edges[pid].get('source_view_context') is not None for pid in record['plan_edges'])
            if detail and not is_unmeasured_detail(attributes['horizontal_projection'],record,evidence):raise ValueError('detail DN scope lacks explicit unmeasured source projection')
            measured_whole=whole and not detail
            diameter.update(plan_drawn_nominal_mm=nominal,plan_drawn_values=copy.deepcopy(values),plan_scope_evidence_sha256=evidence_hash,
                plan_drawn_status='source_checked_plan_DN_scope_human_pending',nominal_mm=nominal if whole else None,
                status=('source_checked_whole_horizontal_main_DN_length_unknown' if detail else 'source_checked_whole_horizontal_main_DN') if whole else ('source_checked_plan_DN_axis_extent_partial' if nominal is not None else 'source_checked_plan_DN_unresolved'),selected_physical_diameter=bool(whole))
            attributes.update(plan_DN_scope_evidence_sha256=evidence_hash,whole_axis_main_scope='source_checked_plan_native_T_to_T_horizontal_main' if whole else None)
            if measured_whole:
                length=attributes['horizontal_projection'].get('edge_value_mm')
                if not isinstance(length,(int,float)) or isinstance(length,bool) or not math.isfinite(length) or length<=0:raise ValueError('complete main route lacks allocated plan length')
                attributes.update(whole_edge_physical_length_mm=length,whole_edge_length_kind='floor_plan_horizontal_main_centerline_route',
                    whole_edge_length_scope='complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length',pipe_net_cut_length_mm=None)
                attributes['horizontal_projection']['route_scope_status']='complete_mapped_horizontal_main_centerline'
            elif detail:
                if attributes.get('whole_edge_physical_length_mm') is not None:raise ValueError('detail drawing was promoted to physical length')
                attributes['horizontal_projection']['route_scope_status']='confirmed_detail_T_to_T_topology_length_unknown' if whole else 'confirmed_detail_branch_topology_length_unknown'
            row=dict(mapping_id=record['mapping_id'],iso_edge=eid,plan_edges=record['plan_edges'],plan_drawn_nominal_mm=nominal,whole_main_DN_and_centerline_route=bool(measured_whole),human_accepted=False)
            if whole and detail:row['whole_main_DN_length_unknown']=True
            proof.append(row)
    out['sourceCheckedCrossViewAttributeFusion']['plan_DN_scope_evidence_sha256']=evidence_hash
    out['sourceCheckedCrossViewAttributeFusion']['whole_main_centerline_route_edges']=[r['iso_edge'] for r in proof if r['whole_main_DN_and_centerline_route']]
    unmeasured=[r['iso_edge'] for r in proof if r.get('whole_main_DN_length_unknown')]
    if unmeasured:out['sourceCheckedCrossViewAttributeFusion']['whole_main_DN_length_unknown_edges']=unmeasured
    return out,proof
