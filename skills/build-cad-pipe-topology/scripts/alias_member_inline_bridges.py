"""Reapply native inline bridges to confirmed-alias member interfaces.

The original local edge may be a long, bent drawing carrier and omit the newer
source_flexible_joints metadata. Project a private, endpoint-bounded reading
domain using the existing native joint reader; never edit the local graph.
The unchanged bridge owner still proves continuity, Ts, DN and component order.
"""
import collections,copy,hashlib,math
from confirm_crossview_paths import encode
from native_line_path_evidence import _on
from native_inline_joint_path_coverage import native_joint
from compound_member_bridges import collect as native_bridges
from alias_member_circle_interfaces import MODE as PARENT_MODE

MODE='native_confirmed_alias_member_inline_bridges_v1'

def bounded_paths(paths,start,end,tol=.05):
    if tol!=.05:raise ValueError('original native contact tolerance required')
    if any(len(p)!=2 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in p)for p in(start,end)):
        raise ValueError('finite member boundaries required')
    size=math.dist(start,end)
    if size<=tol:raise ValueError('distinct member boundaries required')
    u=[(end[i]-start[i])/size for i in(0,1)];result=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            if any(abs((p[0]-start[0])*u[1]-(p[1]-start[1])*u[0])>tol for p in(a,b)):continue
            low,high=sorted(sum((p[i]-start[i])*u[i]for i in(0,1))for p in(a,b));low,high=max(0,low),min(size,high)
            if high-low>tol:result.append([[start[i]+t*u[i]for i in(0,1)]for t in(low,high)])
    if not result:raise ValueError('no original pipe fragments within member domain')
    return result

def reading_projection(doc,plan,parent,inventory,template):
    if parent.get('mode')!=PARENT_MODE or parent.get('original_local_graphs_mutated')is not False:
        raise ValueError('qualified alias member interface parent required')
    original=encode(plan);private=copy.deepcopy(plan);nodes={n['node_id']:n for n in parent['member_local_graph']['nodes']}
    if len(nodes)!=len(parent['member_local_graph']['nodes']):raise ValueError('duplicate member node identity')
    by=collections.defaultdict(list)
    for p in parent['member_local_graph']['external_ports']:by[p['axis_edge_id']].append(p)
    evidence=[];pending=[];used=set()
    for eid,ports in sorted(by.items()):
        if len(ports)!=2:continue  # Retained and explicitly rejected by the original bridge owner.
        try:
            ports=sorted(ports,key=lambda p:(nodes[p['member_node_id']]['x'],nodes[p['member_node_id']]['y']))
            if len({p['system']for p in ports})!=1:raise ValueError('member boundary systems differ')
            xy=[[nodes[p['member_node_id']][k]for k in('x','y')]for p in ports]
            candidates=[e for e in plan['edges']if e['system']==ports[0]['system']and all(any(_on(p,a,b,.05)for path in e.get('attribute_paths',[])for a,b in zip(path,path[1:]))for p in xy)]
            if len(candidates)!=1:raise ValueError('unique original drawing carrier required')
            source=candidates[0]
            if source['edge_id']in used:raise ValueError('overlapping reading domains need independent carrier scopes')
            paths=bounded_paths(source['attribute_paths'],*xy)
            joint_rows=[r for r in inventory if r.get('edge_id')==source['edge_id']and r.get('equipment_type')in('flexible_joint','金属软接')]
            if not joint_rows:raise ValueError('carrier has no independently assigned inline joint')
            if len({r.get('source_top_handle')or r.get('source_handle')for r in joint_rows})!=len(joint_rows):raise ValueError('duplicate assigned native joint')
            joints=[native_joint(doc,plan,source,r,template['block_name'],template['block_fingerprint_sha256'],.05)for r in joint_rows]
            if any(not all(_on(p[:2],*xy,.05)for p in j['contact_points_wcs'])for j in joints):
                raise ValueError('carrier contains inline joints outside bounded member scope')
            record=dict(axis_edge_id=eid,original_source_edge_id=source['edge_id'],original_source_paths=copy.deepcopy(source['attribute_paths']),
                member_boundaries=copy.deepcopy(ports),bounded_paths=copy.deepcopy(paths),native_joint_evidence=joints,
                drawing_tails_excluded_from_this_reading_domain=True,physical_joint_length_mm=None,human_accepted=False)
            present={n['node_id']for n in private['nodes']}
            if any(p['member_node_id']in present for p in ports):raise ValueError('member namespace already occupies local drawing graph')
            target=next(e for e in private['edges']if e['edge_id']==source['edge_id'])
            target.update(attribute_paths=paths,start_node_id=ports[0]['member_node_id'],end_node_id=ports[1]['member_node_id'],
                source_flexible_joints=[dict(source_handle=j['source_handle'],source_block=j['source_block'],
                    source_contact_points=[p[:2]for p in j['contact_points_wcs']],physical_length='unknown',parameter_status='unknown_not_zero')for j in joints])
            private['nodes'].extend(copy.deepcopy(nodes[p['member_node_id']])for p in ports)
            used.add(source['edge_id']);evidence.append(record)
        except (ValueError,KeyError)as exc:pending.append(dict(axis_edge_id=eid,reason=str(exc)))
    if encode(plan)!=original:raise ValueError('original local plan mutated')
    return private,evidence,pending

def collect(pd,ad,plan,axis,parent,pi,ai,template,hashes,units,angles):
    before=encode(plan),encode(axis),encode(parent),encode(pi),encode(ai)
    private,projection,pending=reading_projection(pd,plan,parent,pi,template)
    digest=hashlib.sha256(encode(private)).hexdigest();reading_hashes=dict(hashes,original_plan_graph=hashes['plan_graph'],plan_graph=digest)
    result=native_bridges(pd,ad,private,axis,parent,pi,ai,template,reading_hashes,units,angles)
    failed={p['axis_edge_id']for p in pending}
    if any(r['axis_edge_id']in failed for r in result['records']):raise ValueError('failed reading projection escaped native bridge rejection')
    if before!=(encode(plan),encode(axis),encode(parent),encode(pi),encode(ai)):raise ValueError('original graph, interfaces or component assignments mutated')
    result.update(mode=MODE,source_hashes=copy.deepcopy(hashes),original_native_bridge_mode='native_compound_member_inline_bridges_v1',
        reading_projection_sha256=digest,reading_projection=private,reading_projection_evidence=projection,reading_projection_pending=pending,
        old_interface_records_retained=True,all_vertical_attributes_from11=True,physical_inline_lengths_assigned=0,
        whole_centerline_lengths_assigned=0,original_component_assignments_mutated=False,geometry_bridge_algorithm_reimplemented=False)
    return result
