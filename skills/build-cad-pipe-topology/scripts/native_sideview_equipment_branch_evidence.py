"""Replay current logical owners and native detail T rays after alias binding."""
import hashlib,math
from confirm_crossview_paths import encode
from canonicalize_confirmed_sideviews import verify_tee,DECISION
from reconstruct_sideview_equipment_ownership import MODE
from native_line_path_evidence import LAYERS,_on

def validate_owner(graph,edge,source_hash):
    meta=edge.get('source_sideview_equipment_interface',{});root=graph.get('sourceSideviewEquipmentOwnership',{})
    nodes={n['node_id']:n for n in graph['nodes']};owner=nodes.get(meta.get('equipment_id'));snapshot=meta.get('endpoint_snapshot',{})
    if (root.get('mode')!=MODE or root.get('source_sha256')!=source_hash or meta.get('source_sha256')!=source_hash
        or graph.get('metadata',{}).get('source_sha256')!=source_hash or meta.get('input_graph_sha256')!=root.get('input_graph_sha256')
        or root.get('records',[]).count(meta)!=1 or root.get('human_accepted') is not False or root.get('physical_ports_verified') is not False
        or meta.get('physical_port_verified') is not False or meta.get('interface_to_equipment_length_known') is not False or meta.get('human_accepted') is not False):raise ValueError('sideview logical owner root/source/unknown scope differs')
    if (not owner or owner.get('node_type')!='equipment' or owner.get('source_handle')!=meta.get('body_evidence',{}).get('equipment_handle')
        or snapshot.get('equipment_source_handle')!=owner.get('source_handle') or snapshot.get('equipment_xy')!=[owner.get('x'),owner.get('y')]
        or edge.get('edge_id')!=meta.get('edge_id') or edge.get('system')!=meta.get('system')
        or edge.get(meta.get('interface_side','')+'_node_id')!=owner['node_id']):raise ValueError('sideview current equipment owner differs')
    for key in ('start_node_id','end_node_id','start_boundary_id','end_boundary_id','attribute_paths','system'):
        if snapshot.get(key)!=edge.get(key):raise ValueError('sideview current endpoint/source path snapshot differs')
    if edge.get('physical_length')!='unknown' or edge.get('path_length_complete') is not False or edge.get('equipment_connector_length_mm') is not None:raise ValueError('sideview physical connector was promoted')
    state=graph.get('confirmedSideviewCanonicalization',{})
    if hashlib.sha256(encode(state)).hexdigest()!=meta.get('sideview_root_sha256'):raise ValueError('sideview confirmed original alias changed')
    nid=meta.get('original_canonical_interface_id');kind=meta.get('original_canonical_interface_kind');alias=meta.get('source_alias',{})
    original=[r for r in state.get('records',[]) if r.get('canonical_edge')==edge['edge_id'] and r.get('canonical_interface')==nid]
    if (len(original)!=1 or original[0].get('question_id')!=meta.get('question_id') or original[0].get('pair_sha256')!=meta.get('pair_sha256')
        or original[0].get('answer',{}).get('decision')!=DECISION or original[0].get('canonical_interface_kind')!=kind
        or alias.get('canonical_edge')!=edge['edge_id'] or alias.get('canonical_interface')!=nid or alias.get('canonical_interface_kind')!=kind):raise ValueError('sideview original question/Pair/endpoint binding differs')
    if kind=='node':
        values=[n for n in root.get('retired_interface_nodes',[]) if n.get('node_id')==nid];aliases=root.get('node_aliases',{})
        if nid in nodes:raise ValueError('retired sideview interface was restored as a physical node')
    elif kind=='non_node_boundary':
        values=[n for n in root.get('retired_boundary_anchors',[]) if n.get('boundary_id')==nid];aliases=root.get('boundary_aliases',{})
        if nid in nodes or any(a.get('boundary_id')==nid for a in graph.get('boundary_anchors',[])):raise ValueError('resolved source boundary was restored as active topology')
    else:raise ValueError('unsupported original sideview endpoint role')
    if len(values)!=1 or values[0]!=meta.get('original_canonical_endpoint') or aliases.get(nid)!=owner['node_id']:raise ValueError('sideview retired source endpoint/alias changed')
    endpoint=values[0];direct=endpoint.get('floor');legacy=endpoint.get('legacy_node',{}).get('floor');floor=direct if direct is not None else legacy
    if (direct is not None and legacy is not None and direct!=legacy) or floor!=owner.get('floor') or meta.get('endpoint_floor_evidence',{}).get('floor')!=floor:raise ValueError('sideview endpoint floor evidence differs')
    role=edge.get('source_view_context',{})
    if (role.get('kind')!='confirmed_detail_view' or role.get('source_sha256')!=source_hash or role.get('input_graph_sha256')!=root['input_graph_sha256']
        or role.get('confirmed_alias_root_sha256')!=meta['sideview_root_sha256'] or role.get('physical_length_from_drawing_span') is not False
        or role.get('metric_verified_by_this_stage') is not False or edge['edge_id'] not in root.get('detail_edge_ids',[])):raise ValueError('sideview detail drawing/metric distinction changed')
    return meta

def collect(doc,graph,node_id,source_hash,graph_hash):
    nodes={n['node_id']:n for n in graph['nodes']};node=nodes[node_id];point=[node['x'],node['y']]
    incident=[e for e in graph['edges'] if node_id in (e.get('start_node_id'),e.get('end_node_id'))];owned=[e for e in incident if e.get('source_sideview_equipment_interface')]
    if (node.get('node_type')!='tee' or node.get('review_required') is True or len(incident)!=3 or len(owned)!=1
        or node.get('system') not in LAYERS or {e.get('system') for e in incident}!={node['system']}):raise ValueError('sideview native T incidence unresolved or mixed')
    branch=owned[0];meta=validate_owner(graph,branch,source_hash)
    proof,checked=verify_tee(doc,graph,branch,meta['equipment_id'])
    if proof['tee']!=node_id or checked['attribute_paths']!=branch['attribute_paths']:raise ValueError('sideview T/source paths changed before inventory')
    by={r['edge_id']:r['native_handles'] for r in proof['native_rays']};rays=[];directions=[]
    for edge in incident:
        handles=by.get(edge['edge_id'],[])
        if len(handles)!=1:raise ValueError('sideview native ray source identity is ambiguous')
        handle=handles[0];entity=doc.entitydb.get(handle)
        if entity is None or entity.dxftype()!='LINE' or entity not in doc.modelspace() or entity.dxf.layer!=LAYERS[node['system']]:raise ValueError('sideview native ray source/service changed')
        xyz=[list(entity.dxf.start),list(entity.dxf.end)]
        if any(not math.isfinite(v) for p in xyz for v in p):raise ValueError('sideview nonfinite native XYZ')
        anchor=point;scope='native_detail_main_LINE'
        if edge is branch:
            if not any(min(math.dist(p,point) for p in (path[0],path[-1]))<=.05 for path in edge['attribute_paths']):
                contact=edge.get('source_detail_circle_length_evidence',{}).get('line_contact',[])
                if len(contact)!=2:raise ValueError('sideview rim contact needs original circle evidence')
                anchor=contact;scope='confirmed_sideview_circle_rim'
            else:scope='native_confirmed_detail_branch'
        touches=[]
        for path in edge['attribute_paths']:
            for a,b in zip(path,path[1:]):
                if math.dist(a,anchor)<=.05 and math.dist(b,anchor)>.05:touches.append((a,b))
                elif math.dist(b,anchor)<=.05 and math.dist(a,anchor)>.05:touches.append((b,a))
        if len(touches)!=1:raise ValueError('sideview native graph ray is not unique')
        a,b=touches[0]
        if not _on(a,xyz[0][:2],xyz[1][:2],.05) or not _on(b,xyz[0][:2],xyz[1][:2],.05):raise ValueError('sideview ray leaves its native source LINE')
        candidates=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS[node['system']] and _on(a,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05) and _on(b,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
        if candidates!=[handle]:raise ValueError('sideview native ray has competing source LINEs')
        direction=[(b[i]-a[i])/math.dist(a,b) for i in (0,1)]
        if any(sum(x*y for x,y in zip(direction,u))>math.cos(math.radians(.1)) for u in directions):raise ValueError('sideview coincident T rays')
        directions.append(direction);rays.append(dict(edge_id=edge['edge_id'],source_line_handle=handle,scope=scope,graph_segment=[a,b],direction=direction,native_endpoints_wcs=xyz))
    return dict(status='native_confirmed_sideview_equipment_junction_replayed',source_sha256=source_hash,graph_sha256=graph_hash,junctions=[dict(node_id=node_id,system=node['system'],position=point,source_rays=rays)],
        logical_equipment_owner=meta['equipment_id'],source_view_domain='detail_drawing_only_not_plan_metric_proof',physical_ports_verified=False,physical_length_mm=None,graph_mutated=False,human_accepted=False,hil_ready=False)
