"""Join already qualified member interfaces through original inline corridors.

The endpoint identity is independent of DN and component counts. The inherited
inline reader proves actual source LINE/joint continuity; ordered native instance
identities cross-check both views. Only drawn pipe projections are measured.
"""
import collections,copy,hashlib,math
from confirm_crossview_paths import encode
from native_line_path_evidence import _on,LAYERS
from native_inline_joint_path_coverage import collect as inline_chain
from native_inline_anchors import block_signature
from repair_native_flexible_joints import fingerprint
from batch_native_path_coverage import collect as coverage
from compound_member_interfaces import unique_path,native_label_guard
from native_paired_caption_geometry import collect as captions
from crossview_equipment_branch_inventory import native_tee,index_graph
from native_main_endpoint_extent import endpoint_relation
from attach_anchored_floor_main_attributes import horizontal_domain
from native_dn_text_position import supported as supported_text

MODE='native_compound_member_inline_bridges_v1'

def clip_chain(source,start,end,tol=.05):
    length=math.dist(start,end)
    if not math.isfinite(length) or length<=tol:raise ValueError('distinct bridge boundaries required')
    u=[(end[i]-start[i])/length for i in (0,1)];pieces=[]
    for p in source['private_ordered_pieces']:
        points=p['points']
        if len(points)!=2 or any(abs((q[0]-start[0])*u[1]-(q[1]-start[1])*u[0])>tol for q in points):raise ValueError('bridge corridor is not collinear')
        a,b=sorted(sum((q[i]-start[i])*u[i]for i in(0,1))for q in points);low,high=max(0,a),min(length,b)
        if high-low<=tol:continue
        if p['kind']=='native_inline_joint' and (abs(low-a)>tol or abs(high-b)>tol):raise ValueError('member boundary cuts an inline symbol')
        if p['kind'] not in ('native_inline_joint','native_pipe'):raise ValueError('unknown bridge source piece')
        pieces.append(dict(kind=p['kind'],source_handle=p.get('source_handle')or p.get('source_line_handle'),station_interval=[low,high],
            points=[[start[i]+t*u[i]for i in(0,1)]for t in(low,high)],measured_plan_pipe_projection_mm=high-low if p['kind']=='native_pipe' else None,physical_inline_length_mm=None))
    pieces.sort(key=lambda p:p['station_interval'])
    if (not pieces or abs(pieces[0]['station_interval'][0])>tol or abs(pieces[-1]['station_interval'][1]-length)>tol
        or any(abs(a['station_interval'][1]-b['station_interval'][0])>tol for a,b in zip(pieces,pieces[1:]))):raise ValueError('clipped pipe/joint chain has a gap or overlap')
    if not any(p['kind']=='native_inline_joint'for p in pieces):raise ValueError('bridge requires the inline-corridor owner')
    return pieces

def component_order(doc,inventory,edge,start,end):
    size=math.dist(start,end);u=[(end[i]-start[i])/size for i in(0,1)];rows=[]
    names=edge.get('equipment_names',[])+[n for item in edge.get('equipment_inventory',[])for n in item.get('device_names',[])]
    for row in inventory:
        if row.get('edge_id')!=edge['edge_id']:continue
        h=row.get('source_top_handle')or row.get('source_handle');ins=doc.entitydb.get(h)
        if not ins or ins.dxftype()!='INSERT' or ins not in doc.modelspace() or ins.dxf.name!=row.get('source_block_name'):raise ValueError('component source identity differs')
        p=list(ins.ocs().to_wcs(ins.dxf.insert));t=sum((p[i]-start[i])*u[i]for i in(0,1));d=abs((p[0]-start[0])*u[1]-(p[1]-start[1])*u[0])
        if t<-.05 or t>size+.05:continue
        if min(abs(t),abs(t-size))<=.05:raise ValueError('component at member boundary requires a port-specific owner')
        kind={'ball_valve':'ball_valve','球阀':'ball_valve','flexible_joint':'flexible_joint','金属软接':'flexible_joint'}.get(row.get('equipment_type'))
        if not kind or d>=3 or row.get('assignment_status')!='assigned' or names.count(row.get('device_name'))!=1:raise ValueError('unsupported or unowned member component')
        if sum((r.get('source_top_handle')or r.get('source_handle'))==h for r in inventory)!=1 or sum(r.get('device_name')==row.get('device_name')for r in inventory)!=1:raise ValueError('duplicate native component instance')
        rows.append(dict(device_name=row['device_name'],source_handle=h,source_block=ins.dxf.name,kind=kind,station=t,position_wcs=p,
            block_profile_sha256=fingerprint(doc.blocks[ins.dxf.name]) if kind=='flexible_joint' else block_signature(doc,ins.dxf.name),
            original_owner_edge=edge['edge_id'],rotation=ins.dxf.rotation,scales=[ins.dxf.get(k,1)for k in('xscale','yscale','zscale')],extrusion=list(ins.dxf.extrusion)))
    rows.sort(key=lambda x:x['station'])
    if not rows or any(b['station']-a['station']<=.05 for a,b in zip(rows,rows[1:])):raise ValueError('ambiguous component order')
    return rows

def match_components(plan_rows,axis_rows,joint_handles):
    if len(plan_rows)!=len(axis_rows) or {p['source_handle']for p in plan_rows if p['kind']=='flexible_joint'}!=set(joint_handles):raise ValueError('native inline component population differs')
    pairs=[]
    for p,a in zip(plan_rows,axis_rows):
        if p['kind']!=a['kind'] or p['source_block']!=a['source_block'] or p['block_profile_sha256']!=a['block_profile_sha256']:raise ValueError('ordered native component identity/profile differs')
        pairs.append(dict(plan=copy.deepcopy(p),axis=copy.deepcopy(a),basis='independent_member_endpoints_unique_native_chain_and_ordered_source_instances',physical_port_identity_verified=False))
    return pairs

def annotation_barrier(doc,start,end):
    """Any unresolved nearby DN stops inheritance; never use it to pick a member."""
    size=math.dist(start,end);u=[(end[i]-start[i])/size for i in(0,1)]
    def relevant(e):
        if e.dxftype() not in ('TEXT','MTEXT')or 'DN' not in e.plain_text().upper():return False
        h=e.dxf.height if e.dxftype()=='TEXT'else e.dxf.char_height;p=list(e.ocs().to_wcs(e.dxf.insert) if e.dxftype()=='TEXT'else e.dxf.insert)
        # A supported left-baseline TEXT advances in its native text direction.
        # Unsupported alignment/OCS keeps a conservative envelope and blocks.
        t=sum((p[i]-start[i])*u[i]for i in(0,1));n=(p[0]-start[0])*u[1]-(p[1]-start[1])*u[0];span=max(1,len(e.plain_text()))*h*max(1,abs(e.dxf.get('width',1)))
        if supported_text(e):
            angle=math.radians(e.dxf.rotation);v=[math.cos(angle),math.sin(angle)];t1=t+span*sum(v[i]*u[i]for i in(0,1));n1=n+span*(v[0]*u[1]-v[1]*u[0])
            return min(n,n1)<=2*h and max(n,n1)>=-2*h and max(t,t1)>0 and min(t,t1)<size
        return abs(n)<=2*h and t+span>0 and t-span<size
    if any(relevant(e)for e in doc.modelspace().query('TEXT MTEXT')):raise ValueError('unresolved native plan DN within bridge scope; use its dedicated reader')
    from ezdxf.disassemble import recursive_decompose
    def has_dn(name,trail=frozenset()):
        if name in trail:return False
        return any((e.dxftype()in('TEXT','MTEXT')and 'DN'in e.plain_text().upper())or(e.dxftype()=='INSERT'and has_dn(e.dxf.name,trail|{name}))for e in doc.blocks[name])
    for ins in doc.modelspace().query('INSERT'):
        if has_dn(ins.dxf.name)and any(relevant(e)for e in recursive_decompose([ins])):raise ValueError('nested native plan DN within bridge scope requires its dedicated reader')

def endpoint(port,parent):
    matches=[(g,i)for g in parent['groups']for i in g['interfaces']if i['member_primary_node_id']==port['member_node_id']and i['axis_primary_T']==port['axis_node_id']]
    if len(matches)!=1:raise ValueError('member interface is not unique in the native parent')
    group,interface=matches[0];records=[r for r in group['records']if r['kind']=='primary_member_main']
    if len(records)!=1:raise ValueError('member endpoint lacks its independent plan declaration')
    return group,interface,records[0]

def bridge(pd,ad,plan,axis,parent,ports,pi,ai,template,hashes,units,angles,axis_captions):
    if len(ports)!=2:raise ValueError('two independently mapped member boundaries required')
    pn={n['node_id']:n for n in parent['member_local_graph']['nodes']};ports=sorted(ports,key=lambda p:(pn[p['member_node_id']]['x'],pn[p['member_node_id']]['y']))
    ends=[endpoint(p,parent)for p in ports];groups=[x[0]for x in ends];members=[x[2]for x in ends]
    eid=ports[0]['axis_edge_id'];an,ae,_=index_graph(axis);edge=ae[eid];system=edge['system'];floor=members[0]['floor'];level=members[0]['literal_level_key']
    if any(p['axis_edge_id']!=eid or p['system']!=system for p in ports)or {p['axis_node_id']for p in ports}!={edge['start_node_id'],edge['end_node_id']}or any(p['other_axis_node']not in {q['axis_node_id']for q in ports if q is not p}for p in ports):raise ValueError('member ports are not reciprocal source edge boundaries')
    if len({g['member_scope_id']for g in groups})!=2 or any(m['system']!=system or m['floor']!=floor or m['literal_level_key']!=level for m in members):raise ValueError('bridge service, floor or literal member identity differs')
    anchors=[{a['equipment_id']for a in g['independent_branch_anchors']}for g in groups]
    if any(len(a)<2 for a in anchors)or anchors[0]&anchors[1]:raise ValueError('bridge endpoint cohorts are not independent')
    relation=endpoint_relation(axis,eid,floor,system);readonly=copy.deepcopy(edge)
    if relation['path_orientation']=='end_to_start':readonly['attribute_paths']=[list(reversed(readonly['attribute_paths'][0]))]
    horizontal_domain(dict(axis,edges=[readonly]),dict(kind='same_floor_T_to_T_main',iso_edges=[eid],floor=floor,system=system,iso_start=edge['start_node_id'],iso_end=edge['end_node_id']),angles)
    original=coverage(ad,axis,[eid],hashes['axis_source'],hashes['axis_graph']);handles=unique_path(original)
    if len(handles)!=1 or any(g['axis_primary_LINE']!=handles[0]for g in groups):raise ValueError('bridge leaves independently identified primary native LINE')
    tees=[native_tee(ad,axis,p['axis_node_id'],hashes['axis_source'],hashes['axis_graph'])for p in ports]
    if any(len(t['junctions'])!=1 or len(t['junctions'][0]['source_rays'])!=3 for t in tees):raise ValueError('bridge endpoints lack native three-ray evidence')
    xy=[[pn[p['member_node_id']]['x'],pn[p['member_node_id']]['y']]for p in ports];candidates=[]
    for e in plan['edges']:
        if e['system']==system and e.get('source_flexible_joints') and all(any(_on(p,a,b,.05)for path in e['attribute_paths']for a,b in zip(path,path[1:]))for p in xy):candidates.append(e)
    if len(candidates)!=1:raise ValueError('unique source inline corridor between member boundaries required')
    source_edge=candidates[0];source=inline_chain(pd,plan,pi,dict(source_sha256=hashes['plan_source'],graph_sha256=hashes['plan_graph'],inventory_sha256=hashes['plan_inventory'],
        block_name=template['block_name'],block_fingerprint_sha256=template['block_fingerprint_sha256'],edges=[source_edge['edge_id']]),dict(source_sha256=hashes['plan_source'],graph_sha256=hashes['plan_graph'],inventory_sha256=hashes['plan_inventory']))['records'][0]
    pieces=clip_chain(source,*xy);joint_handles=[p['source_handle']for p in pieces if p['kind']=='native_inline_joint']
    if any(not(units['plan_window'][0]<=p[0]<=units['plan_window'][1]and units['plan_window'][2]<=p[1]<=units['plan_window'][3])for part in pieces for p in part['points']):raise ValueError('bridge leaves metric plan domain')
    # Source circles inside the interval require an additional topological split.
    if any(_on(list(c.ocs().to_wcs(c.dxf.center))[:2],*xy,.05)and min(math.dist(list(c.ocs().to_wcs(c.dxf.center))[:2],p)for p in xy)>.05 for c in pd.modelspace().query('CIRCLE')):raise ValueError('interior source circle requires another member interface')
    annotation_barrier(pd,*xy)
    nominal=members[0]['nominal_mm']
    if not math.isfinite(nominal)or nominal<=0 or any(m['nominal_mm']!=nominal for m in members):raise ValueError('boundary plan DN inheritance conflicts')
    dn_guard=native_label_guard(ad,handles,nominal,axis_captions)
    axy=[[an[p['axis_node_id']]['x'],an[p['axis_node_id']]['y']]for p in ports];matches=match_components(component_order(pd,pi,source_edge,*xy),component_order(ad,ai,edge,*axy),joint_handles)
    projected=sum(p['measured_plan_pipe_projection_mm']or 0 for p in pieces);token='MEMBER-BRIDGE:'+hashlib.sha256(encode(sorted(p['member_node_id']for p in ports))).hexdigest()[:16]
    local=dict(edge_id=token,start_node_id=ports[0]['member_node_id'],end_node_id=ports[1]['member_node_id'],system=system,floor_start=floor,floor_end=floor,
        attribute_paths=[p['points']for p in pieces if p['kind']=='native_pipe'],source_handles=[p['source_handle']for p in pieces if p['kind']=='native_pipe'],
        source_flexible_joints=[copy.deepcopy(j)for j in source_edge['source_flexible_joints']if j['source_handle']in joint_handles],
        equipment_names=[m['plan']['device_name']for m in matches],diameter_nominal_mm=nominal,plan_pipe_projection_mm=projected,path_length_complete=False,
        component_member_allocation='source_instance_order_qualified_for_this_bridge_only',installed_whole_length_mm=None,net_pipe_cut_length_mm=None,source_parent_plan_edge=source_edge['edge_id'])
    record=dict(mapping_id=token,axis_edge_id=eid,plan_member_edge_id=token,source_parent_plan_edge=source_edge['edge_id'],floor=floor,system=system,nominal_mm=nominal,literal_level_key=level,
        plan_pipe_projection_mm=projected,plan_pieces=pieces,native_plan_inline_chain=source,native_axis_path=original,native_axis_Ts=tees,native_axis_DN_crosschecks=dn_guard,
        plan_declarations=[d for m in members for d in copy.deepcopy(m['plan_declarations'])],DN_inheritance_chain=[m['mapping_id']for m in members],
        DN_value_source='two_independently_qualified_plan_primary_members_through_true_Ts_no_intervening_annotation',DN_used_for_mapping=False,
        component_correspondences=matches,axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
        source_hashes=copy.deepcopy(hashes),whole_centerline_length_mm=None,installed_whole_length_mm=None,net_pipe_cut_length_mm=None,physical_elevation_mm=None,
        inline_graphic_spans_used_as_physical_length=False,original_component_assignments_mutated=False,human_accepted=False)
    return record,local

def collect(pd,ad,plan,axis,parent,pi,ai,template,hashes,units,angles):
    if template.get('confirmation_basis')!='source_geometry_calibrated'or not template.get('expert_evidence')or fingerprint(pd.blocks[template['block_name']])!=template['block_fingerprint_sha256']:raise ValueError('preserved source-calibrated inline template required')
    ports=collections.defaultdict(list)
    for g in parent['groups']:
        for p in g['external_ports']:ports[p['axis_edge_id']].append(p)
    records=[];pending=[];local=copy.deepcopy(parent['member_local_graph']);axis_captions=captions(ad)
    for eid,pp in sorted(ports.items()):
        try:r,e=bridge(pd,ad,plan,axis,parent,pp,pi,ai,template,hashes,units,angles,axis_captions)
        except ValueError as exc:pending.append(dict(axis_edge_id=eid,reason=str(exc),retained_ports=copy.deepcopy(pp)));continue
        if any(x['edge_id']==e['edge_id']for x in local['edges']):raise ValueError('duplicate member bridge')
        local['edges'].append(e);records.append(r)
    used={r['axis_edge_id']for r in records};local['external_ports']=[p for p in local['external_ports']if p['axis_edge_id']not in used]
    assigned=[m['plan']['device_name']for r in records for m in r['component_correspondences']]
    if len(assigned)!=len(set(assigned))or any(name in e.get('equipment_names',[])for e in parent['member_local_graph']['edges']for name in assigned):raise ValueError('plan component member ownership duplicated')
    return dict(mode=MODE,records=records,pending=pending,member_local_graph=local,original_external_ports=copy.deepcopy(parent['member_local_graph']['external_ports']),
        counts=dict(external_axis_edges_screened=len(ports),qualified_bridges=len(records),new_member_edges=len(records),qualified_component_pairs=len(assigned),remaining_external_axis_edges=len(pending)),
        source_hashes=hashes,DN_used_for_mapping=False,source_drawing_graphs_unchanged=True,member_topology_rebuilt=True,installed_lengths_assigned=0,human_accepted=False)
