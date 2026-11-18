"""Evidence-only grouping of mixed-service three-ray junctions.

This helper never connects, splits, relabels or discards graph entities. A
geometric crossing and an overlaid main are indistinguishable without separate
source evidence. Candidates must remain algorithm-pending before HIL.
"""
import collections
import math


def identify(graph, *, point_tolerance, straight_angle_tolerance_degrees,
             branch_angle_tolerance_degrees, allowed_systems=('supply','return')):
    if point_tolerance <= 0 or not 0 < straight_angle_tolerance_degrees < 45 or not 0 < branch_angle_tolerance_degrees < 45:
        raise ValueError('Invalid source-calibrated mixed-tee tolerances')
    edges_by_node=collections.defaultdict(list)
    for edge in graph['edges']:
        for key in ('start_node_id','end_node_id'):
            edges_by_node[edge[key]].append(edge)
    candidates=[]; excluded=[]

    def ray(edge,node):
        points=edge.get('path_points') or edge.get('path') or []
        if len(points)<2:return None
        target=(float(node['x']),float(node['y']))
        if edge['start_node_id']==node['node_id']: oriented=points
        elif edge['end_node_id']==node['node_id']: oriented=list(reversed(points))
        else:return None
        if math.dist(target,oriented[0][:2])>point_tolerance:return None
        for p in oriented[1:]:
            dx=float(p[0])-target[0];dy=float(p[1])-target[1];length=math.hypot(dx,dy)
            if length>point_tolerance:return (dx/length,dy/length)
        return None

    for node in graph['nodes']:
        if node.get('node_type')!='tee' or not node.get('mixed_source_contact'):continue
        incident=edges_by_node[node['node_id']]
        count=collections.Counter(e.get('system') for e in incident)
        reason=None
        if len(incident)!=3 or len(count)!=2 or sorted(count.values())!=[1,2]:reason='not_two_plus_one_system_rays'
        if reason:
            excluded.append({'node_id':node['node_id'],'reason':reason});continue
        trunk=next(k for k,v in count.items() if v==2);branch=next(k for k,v in count.items() if v==1)
        te=[e for e in incident if e.get('system')==trunk];be=next(e for e in incident if e.get('system')==branch)
        rays=[ray(e,node) for e in te+[be]]
        if any(v is None for v in rays):
            excluded.append({'node_id':node['node_id'],'reason':'missing_unambiguous_local_edge_path'});continue
        def angle(a,b):return math.degrees(math.acos(max(-1,min(1,a[0]*b[0]+a[1]*b[1]))))
        straight=angle(rays[0],rays[1]);branch_angles=[angle(rays[2],rays[0]),angle(rays[2],rays[1])]
        if abs(180-straight)>straight_angle_tolerance_degrees or any(abs(90-a)>branch_angle_tolerance_degrees for a in branch_angles):
            excluded.append({'node_id':node['node_id'],'reason':'not_opposing_trunk_and_perpendicular_branch'});continue
        known=trunk in allowed_systems and branch in allowed_systems and trunk!=branch
        candidates.append({'node_id':node['node_id'],'xy':[node['x'],node['y']],
            'trunk_system':trunk,'branch_system':branch,'trunk_edges':sorted(e['edge_id'] for e in te),
            'branch_edge':be['edge_id'],'source_handles':sorted({h for e in incident for h in e.get('source_handles',[])}),
            'trunk_angle_degrees':straight,'branch_angles_degrees':branch_angles,
            'candidate_kind':'known_supply_return' if known else 'unknown_service',
            'status':'algorithm_pending','physical_connection_confirmed':False,
            'overlay_status':'not_established_requires_source_symbol_and_project_rule',
            'is_overlay_repair_candidate':False,
            'reason':'Mixed-system graph geometry only. Neither ordinary orthogonal contact nor proximity establishes an overlay or a topology error; inspect project-specific native symbols and user/source interpretation first.'})
    return {'status':'algorithm_pending' if candidates or excluded else 'no_candidates',
        'counts':{'candidates':len(candidates),'known_supply_return':sum(c['candidate_kind']=='known_supply_return' for c in candidates),
                  'unknown_service':sum(c['candidate_kind']=='unknown_service' for c in candidates),'excluded_for_shape_or_path':len(excluded)},
        'candidates':candidates,'excluded':excluded,'graph_mutated':False,
        'scope':'Graph geometry candidate inventory only; no source identity, hydraulic connection, or overlaid trunk is inferred.'}
