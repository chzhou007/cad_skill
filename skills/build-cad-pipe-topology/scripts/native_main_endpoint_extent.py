"""Qualify undirected native main extent without changing source path order.

This geometry predicate does not prove source connectivity. Callers must replay
the native corridor and both Ts before consuming it. Diameter and metric status
are separate; a missing metric does not erase independently proved uniform DN.
"""
import copy,math
from attach_anchored_floor_main_attributes import horizontal_domain

def endpoint_relation(graph,eid,floor,system,tolerance=.05):
    if not math.isfinite(tolerance)or tolerance<=0:raise ValueError('invalid endpoint tolerance')
    edges=[e for e in graph['edges']if e['edge_id']==eid]
    if len(edges)!=1:raise ValueError('unique main edge required')
    edge=edges[0];nodes={n['node_id']:n for n in graph['nodes']}
    if edge['system']!=system:raise ValueError('main service differs')
    if edge.get('source_view_context'):raise ValueError('detail-view spans need their separate metric owner')
    paths=edge.get('attribute_paths',[])
    if len(paths)!=1 or len(paths[0])<2:raise ValueError('one continuous drawn main path required')
    path=paths[0]
    if any(len(p)!=2 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in p)for p in path):raise ValueError('finite native XY path required')
    ends=[nodes[edge[k]]for k in('start_node_id','end_node_id')]
    if any(n.get('node_type')not in('tee','physical_junction')or n.get('floor')!=floor or n.get('review_required')is True or n.get('system',system)!=system for n in ends):raise ValueError('same-floor same-system physical Ts required')
    for names in(('floor_start','start_floor'),('floor_end','end_floor')):
        values=[edge[k]for k in names if k in edge]
        if not values or any(v!=floor for v in values):raise ValueError('main floor differs')
    points=[[n['x'],n['y']]for n in ends]
    if math.dist(*points)<=2*tolerance:raise ValueError('coincident main endpoints require separate evidence')
    forward=all(math.dist(a,b)<=tolerance for a,b in zip((path[0],path[-1]),points))
    reverse=all(math.dist(a,b)<=tolerance for a,b in zip((path[-1],path[0]),points))
    if forward==reverse:raise ValueError('drawn path does not cover both distinct T endpoints')
    return dict(edge_id=eid,path_orientation='start_to_end'if forward else'end_to_start',endpoint_path_indexes=[0,-1]if forward else[-1,0],source_path_unchanged=True,flow_direction_inferred=False)

def qualify(plan,axis,row,nominal_mm,projection,angles):
    if row['kind']!='same_floor_T_to_T_main'or len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('single independently mapped T-to-T main required')
    if isinstance(nominal_mm,bool)or not isinstance(nominal_mm,(int,float))or not math.isfinite(nominal_mm)or nominal_mm<=0:raise ValueError('uniform known native plan DN required')
    relations={view:endpoint_relation(g,row[view+'_edges'][0],row['floor'],row['system'])for view,g in(('plan',plan),('iso',axis))}
    # The old horizontal-domain reader requires display direction to match node
    # order. Normalize only its read-only projection, never the source graph.
    by={e['edge_id']:e for e in axis['edges']};edge=by[row['iso_edges'][0]];projected=dict(edge)
    if relations['iso']['path_orientation']=='end_to_start':projected['attribute_paths']=[list(reversed(edge['attribute_paths'][0]))]
    readonly=dict(axis,edges=[projected]);horizontal_domain(readonly,row,angles)
    complete=None
    if projection is not None:
        pieces=projection.get('pieces',[]);value=projection.get('value_mm')
        if (isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0 or not pieces
            or abs(sum(p['length_mm']for p in pieces)-value)>.0001 or projection.get('installed_whole_edge_length_mm')is not None):raise ValueError('invalid source plan projection')
        source_edge=next(e for e in plan['edges']if e['edge_id']==row['plan_edges'][0])
        if projection['status']=='native_plan_horizontal_projection_partial_length'and not source_edge.get('source_flexible_joints'):complete=value
    return dict(mapping_id=row['mapping_id'],axis_edge_id=edge['edge_id'],plan_edge_id=row['plan_edges'][0],floor=row['floor'],system=row['system'],nominal_mm=nominal_mm,endpoint_relations=relations,
        axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),plan_nodes=[row['plan_start'],row['plan_end']],axis_nodes=[row['iso_start'],row['iso_end']],
        complete_horizontal_centerline_route_mm=complete,source_projection=copy.deepcopy(projection),whole_installed_length_mm=None,net_pipe_cut_length_mm=None,source_paths_mutated=False,DN_depends_on_metric_completeness=False,human_accepted=False)
