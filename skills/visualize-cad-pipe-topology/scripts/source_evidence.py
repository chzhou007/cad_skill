"""Validate native terminal glyphs and read-only instance metadata for display."""
from instance_geometry import source_paths

def readable(text):
    if not isinstance(text,str) or '\ufffd' in text or any(0xd800<=ord(c)<=0xdfff for c in text):
        raise ValueError('Unreadable native source metadata')
    return text

def attributes(doc,instance):
    records=instance.get('source_attributes') or []
    if not isinstance(records,list):raise ValueError('Invalid native source attributes')
    owner=doc.entitydb.get(instance.get('source_top_handle',''))
    owned={a.dxf.handle for a in owner.attribs} if owner is not None and owner.dxftype()=='INSERT' else set()
    for record in records:
        h=record.get('source_handle');a=doc.entitydb.get(h)
        if h not in owned or a is None or a.dxftype()!='ATTRIB':raise ValueError('Source attribute is not attached to the declared native instance')
        if readable(record.get('text'))!=readable(a.dxf.text) or record.get('tag')!=a.dxf.tag or record.get('invisible')!=bool(a.dxf.flags&1):
            raise ValueError('Native source attribute identity differs')
    return records

def sideview_interface_glyph(graph,edge):
    from native_sideview_equipment_branch_evidence import validate_owner
    record=validate_owner(graph,edge,graph.get('metadata',{}).get('source_sha256'))
    original=record['original_canonical_endpoint']
    native=original if record['original_canonical_interface_kind']=='node' else original.get('legacy_node',{})
    handles=native.get('source_handles')
    scope='complete_recorded_interface_glyph'
    if record['original_canonical_interface_kind']=='non_node_boundary' and original.get('source_circle_handle'):
        glyphs=original.get('source_glyph_handles')
        if glyphs is not None:
            if not isinstance(glyphs,list) or len(glyphs)!=4:raise ValueError('sideview source boundary glyph handles incomplete')
            handles=[original['source_circle_handle']]+glyphs
        elif not isinstance(handles,list) or len(handles)!=5:
            # Legacy unresolved terminals recorded the pipe, not the glyph.
            # Render the explicitly bound native circle; never invent the arms.
            handles=[original['source_circle_handle']];scope='recorded_boundary_circle_only'
    if not isinstance(handles,list) or len(handles) not in (1,5) or len(set(handles))!=len(handles):raise ValueError('sideview original glyph lacks recorded native handles')
    return dict(id='SIDEVIEW-'+record['original_canonical_interface_id'],kind='sideview_source_equipment_interface',
        node_id=record['equipment_id'],edge_id=edge['edge_id'],original_interface_id=record['original_canonical_interface_id'],
        source_handles=handles,native_glyph_scope=scope,system=edge['system'],floor=record['endpoint_floor_evidence']['floor'],remote_continuation_confirmed=False)


def terminal_geometry(doc,glyph,nodes,edges,graph=None):
    n=nodes.get(glyph.get('node_id'));e=edges.get(glyph.get('edge_id'))
    if n is None or e is None or n['node_id'] not in (e['start_node_id'],e['end_node_id']):
        raise ValueError('Source terminal glyph has no adjacent node/edge witness')
    if glyph.get('kind')=='sideview_source_equipment_interface':
        import math
        if graph is None:raise ValueError('sideview source glyph requires complete ownership graph evidence')
        expected=sideview_interface_glyph(graph,e)
        if any(glyph.get(k)!=v for k,v in expected.items()):raise ValueError('sideview glyph identity differs from source ownership')
        record=e['source_sideview_equipment_interface'];original=record['original_canonical_endpoint']
        native=original if record['original_canonical_interface_kind']=='node' else original.get('legacy_node',{})
        handles=expected['source_handles'];circle_handle=original.get('source_circle_handle') or native.get('source_handle');circle=doc.entitydb.get(circle_handle);lines=[doc.entitydb.get(h) for h in handles if h!=circle_handle]
        layers={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
        if (circle is None or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or circle.dxf.layer!=layers.get(e['system'])
            or len(lines)!=(0 if expected['native_glyph_scope']=='recorded_boundary_circle_only' else 4)
            or any(x is None or x.dxftype()!='LINE' or x not in doc.modelspace() or x.dxf.layer!='空调立管、水平支管' for x in lines)):
            raise ValueError('sideview source native glyph differs')
        center_tolerance=.05
        if record['original_canonical_interface_kind']=='non_node_boundary' and original.get('source_circle_handle'):
            # Reuse the original typed-boundary display bound, not a larger
            # topology snap. Its preserved native pipe endpoint is checked too.
            user=original.get('kind')=='user_confirmed_non_node_source_boundary'
            pipe=doc.entitydb.get(original.get('source_pipe_handle'))
            if (original.get('kind') not in ('expert_non_node_source_boundary','user_confirmed_non_node_source_boundary')
                or pipe is None or pipe.dxftype()!='LINE' or pipe not in doc.modelspace() or pipe.dxf.layer!=circle.dxf.layer
                or original.get('source_pipe_handle') not in e.get('source_handles',[])
                or [original.get('x'),original.get('y')]!=[native.get('x'),native.get('y')]
                or min(math.dist([v.x,v.y],[original['x'],original['y']]) for v in (pipe.dxf.start,pipe.dxf.end))>(1.0 if user else .01)):
                raise ValueError('sideview original boundary native pipe differs')
            center_tolerance=1.0
        if math.dist([circle.dxf.center.x,circle.dxf.center.y],[native.get('x'),native.get('y')])>center_tolerance:raise ValueError('sideview native glyph center changed')
        endpoint=e['path_points'][0 if record['interface_side']=='start' else -1]
        if math.dist(endpoint,[native['x'],native['y']])>.05:raise ValueError('sideview source endpoint no longer meets native marker')
        return source_paths(doc,handles)
    if glyph.get('kind') in ('confirmed_equipment_interface','calibrated_source_equipment_interface'):
        import math
        calibrated=glyph.get('kind')=='calibrated_source_equipment_interface'
        record=e.get('source_layout_equipment_interface',{}) if calibrated else e.get('confirmed_equipment_interface',{})
        original=record.get('original_interface',{});side=record.get('interface_side');confirmation=record.get('confirmation',{})
        handles=glyph.get('source_handles');expected=original.get('source_handles')
        if calibrated:
            snapshot=record.get('endpoint_snapshot',{})
            ownership_paths=e.get('attribute_paths')
            normalized=e.get('source_circle_path_normalization')
            if normalized:
                before=normalized.get('input_snapshot',{});after=normalized.get('output_snapshot',{})
                if (normalized.get('source_sha256')!=record.get('source_sha256') or normalized.get('human_accepted') is not False
                    or normalized.get('physical_connector_length') is not None or e.get('physical_length')!='unknown' or e.get('path_length_complete') is not False
                    or any(before.get(k)!=e.get(k) or after.get(k)!=e.get(k) for k in ('start_node_id','end_node_id','system'))
                    or after.get('attribute_paths')!=e.get('attribute_paths')):raise ValueError('Normalized circle interface snapshot invalid')
                from native_circle_rim_junction_evidence import collect
                collect(doc,dict(nodes=list(nodes.values()),edges=list(edges.values())),normalized['node_id'],record['source_sha256'],'read_only_native_interface_projection')
                ownership_paths=before.get('attribute_paths')
            if (record.get('status')!='source_calibrated_logical_ownership' or record.get('human_accepted') is not False
                or record.get('equipment_id')!=n['node_id'] or record.get('edge_id')!=e['edge_id']
                or record.get('system')!=e['system'] or glyph.get('remote_continuation_confirmed') is not False
                or snapshot.get('start_node_id')!=e['start_node_id'] or snapshot.get('end_node_id')!=e['end_node_id']
                or snapshot.get('attribute_paths')!=ownership_paths):raise ValueError('Calibrated source interface ownership invalid')
        elif confirmation.get('confirmed_by')!='user' or not confirmation.get('answer'):raise ValueError('Confirmed source interface ownership invalid')
        if n.get('node_type')!='equipment' or side not in ('start','end') or e.get(side+'_node_id')!=n['node_id']:raise ValueError('Confirmed source interface ownership invalid')
        if original.get('node_type')!='virtual_equipment' or original.get('subtype')!='out_of_plane_interface' or original.get('system')!=e.get('system') or str(original.get('floor'))!=str(n.get('floor')):raise ValueError('Confirmed source interface scope invalid')
        if glyph.get('system')!=e.get('system') or str(glyph.get('floor'))!=str(n.get('floor')) or glyph.get('original_interface_id')!=original.get('node_id'):raise ValueError('Confirmed source interface identity differs')
        if record.get('physical_port_verified') is not False or record.get('interface_to_equipment_length_known') is not False:raise ValueError('Unverified port or length incorrectly claimed')
        if not isinstance(handles,list) or handles!=expected or len(handles)!=5 or len(set(handles))!=5:raise ValueError('Confirmed source interface handles differ')
        circle=doc.entitydb.get(original.get('source_handle'));lines=[doc.entitydb.get(h) for h in handles if h!=original.get('source_handle')]
        layers={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
        if circle is None or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or circle.dxf.layer!=layers.get(e['system']) or len(lines)!=4 or any(x is None or x.dxftype()!='LINE' or x not in doc.modelspace() or x.dxf.layer!='空调立管、水平支管' for x in lines):raise ValueError('Confirmed source interface native glyph differs')
        if math.hypot(circle.dxf.center.x-original['x'],circle.dxf.center.y-original['y'])>.05:raise ValueError('Confirmed source interface center differs')
        endpoint=e['path_points'][0 if side=='start' else -1]
        if math.dist(endpoint,(original['x'],original['y']))>.05:raise ValueError('Confirmed source path no longer meets marker')
        paths=source_paths(doc,handles)
        if not paths:raise ValueError('Confirmed source interface has no native geometry')
        return paths
    if glyph.get('kind')=='native_system_conflict':
        import math
        evidence=n.get('source_glyph_system_conflict',{});handles=glyph.get('source_handles');circle=doc.entitydb.get(evidence.get('circle_handle'));pipe=doc.entitydb.get(evidence.get('pipe_handle'));layers={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
        expected=[evidence.get('circle_handle')]+evidence.get('glyph_handles',[])
        if n.get('node_type')!='virtual_equipment' or evidence.get('status')!='source_system_conflict_unresolved' or evidence.get('remote_connection')!='unknown' or glyph.get('remote_continuation_confirmed') is not False:raise ValueError('Conflict glyph status invalid')
        if evidence.get('edge_id')!=e['edge_id'] or glyph.get('system')!=e.get('system') or evidence.get('pipe_source_system')!=e.get('system') or evidence.get('circle_source_system') not in layers or evidence.get('circle_source_system')==e.get('system') or str(glyph.get('floor'))!=str(n.get('floor')):raise ValueError('Conflict glyph system or edge mismatch')
        if not isinstance(handles,list) or handles!=expected or len(handles)!=5 or len(set(handles))!=5:raise ValueError('Conflict glyph handles differ')
        lines=[doc.entitydb.get(h) for h in handles[1:]]
        if circle is None or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or circle.dxf.layer!=layers[evidence['circle_source_system']] or pipe is None or pipe.dxftype()!='LINE' or pipe not in doc.modelspace() or pipe.dxf.layer!=layers[e['system']] or evidence['pipe_handle'] not in e.get('source_handles',[]) or any(x is None or x.dxftype()!='LINE' or x not in doc.modelspace() or x.dxf.layer!='空调立管、水平支管' for x in lines):raise ValueError('Conflict glyph native source mismatch')
        if evidence.get('circle_source_layer')!=circle.dxf.layer or evidence.get('pipe_source_layer')!=pipe.dxf.layer or math.hypot(circle.dxf.center.x-n['x'],circle.dxf.center.y-n['y'])>.05 or min(math.hypot(p.x-n['x'],p.y-n['y']) for p in (pipe.dxf.start,pipe.dxf.end))>.05:raise ValueError('Conflict glyph native contact mismatch')
        endpoint=e['path_points'][0 if e['start_node_id']==n['node_id'] else -1]
        if math.dist(endpoint,(n['x'],n['y']))>.05:raise ValueError('Conflict glyph graph contact mismatch')
        paths=source_paths(doc,handles)
        if not paths:raise ValueError('Conflict glyph has no native geometry')
        return paths
    if n['node_type']!='virtual_equipment' or glyph['id'] not in n.get('source_terminal_glyph_ids',[]):
        raise ValueError('Native terminal glyph must retain its source boundary owner')
    if glyph.get('remote_continuation_confirmed') is not False:raise ValueError('Native end mark does not confirm a remote connection')
    if glyph.get('system')!=e['system'] or str(glyph.get('floor'))!=str(n['floor']):raise ValueError('Native terminal glyph source scope differs')
    handles=glyph.get('source_handles')
    if not isinstance(handles,list) or not handles or len(handles)!=len(set(handles)):raise ValueError('Native terminal glyph needs unique native handles')
    if glyph.get('kind')=='native_downturn_terminal':
        if len(handles)!=1 or doc.entitydb.get(handles[0]) is None or doc.entitydb[handles[0]].dxftype()!='CIRCLE':raise ValueError('Native downturn is not the declared source CIRCLE')
        circle=doc.entitydb[handles[0]];evidence=n.get('source_downturn_evidence',{})
        if evidence.get('circle_handle')!=handles[0] or evidence.get('pipe_handle') not in e.get('source_handles',[]) or evidence.get('source_layer')!=circle.dxf.layer:raise ValueError('Native downturn source identity mismatch')
        if 'radius_native' in evidence and abs(circle.dxf.radius-evidence['radius_native'])>1e-6:raise ValueError('Native downturn radius mismatch')
        if abs(circle.dxf.center.x-n['x'])>.01 or abs(circle.dxf.center.y-n['y'])>.01:raise ValueError('Native downturn circle is not centered on endpoint')
    elif glyph.get('kind')=='native_concentric_circle_candidate':
        evidence=n.get('source_concentric_candidate',{});circles=[doc.entitydb.get(h) for h in handles]
        if len(handles)!=2 or evidence.get('source_circle_handles')!=handles or any(c is None or c.dxftype()!='CIRCLE' for c in circles):raise ValueError('Native concentric circles are missing')
        if evidence.get('source_line_handle') not in e.get('source_handles',[]):raise ValueError('Native concentric pipe source differs')
        line=doc.entitydb.get(evidence['source_line_handle']);center=evidence.get('center',[]);radii=evidence.get('radii',[])
        if line is None or line.dxftype()!='LINE' or len(center)!=2 or len(radii)!=2 or any(c.dxf.layer!=line.dxf.layer or abs(c.dxf.center.x-center[0])>.5 or abs(c.dxf.center.y-center[1])>.5 or abs(c.dxf.radius-r)>1e-6 for c,r in zip(circles,radii)):raise ValueError('Native concentric geometry differs')
        import math
        if not any(abs(math.hypot(n['x']-center[0],n['y']-center[1])-r)<=.5 for r in radii) or not any(math.hypot(p.x-n['x'],p.y-n['y'])<=.5 for p in (line.dxf.start,line.dxf.end)):raise ValueError('Native concentric endpoint is not witnessed')
    elif glyph.get('kind')=='native_insert_wave_terminal':
        from ezdxf import bbox
        evidence=n.get('source_wave_insert_evidence',{});ins=doc.entitydb.get(handles[0]) if len(handles)==1 else None
        if ins is None or ins.dxftype()!='INSERT' or ins.dxf.name!=evidence.get('block_name') or evidence.get('source_handle')!=handles[0] or evidence.get('source_line_handle') not in e.get('source_handles',[]):raise ValueError('Native wave insert identity mismatch')
        box=bbox.extents(ins.virtual_entities());tol=float(evidence.get('contact_tolerance',0))
        if not 0<tol<=.5 or not (box.extmin.x-tol<=n['x']<=box.extmax.x+tol and box.extmin.y-tol<=n['y']<=box.extmax.y+tol):raise ValueError('Native wave insert does not enclose terminal')
    elif glyph.get('kind')=='native_tangent_circle_candidate':
        import math
        evidence=n.get('source_tangent_circle_candidate',{});circle=doc.entitydb.get(handles[0]) if len(handles)==1 else None;other=doc.entitydb.get(evidence.get('paired_circle_handle'));line=doc.entitydb.get(evidence.get('source_line_handle'));peer=nodes.get(evidence.get('paired_node_id'))
        if circle is None or circle.dxftype()!='CIRCLE' or evidence.get('source_circle_handle')!=handles[0] or other is None or other.dxftype()!='CIRCLE' or line is None or line.dxftype()!='LINE' or line.dxf.handle not in e.get('source_handles',[]) or line.dxf.layer!=circle.dxf.layer:raise ValueError('Native tangent circle source identity mismatch')
        a=circle.ocs().to_wcs(circle.dxf.center);b=other.ocs().to_wcs(other.dxf.center)
        if peer is None or peer.get('system')==n.get('system') or str(peer.get('floor'))!=str(n.get('floor')) or math.hypot(n['x']-a.x,n['y']-a.y)>.1 or min(math.hypot(p.x-a.x,p.y-a.y) for p in (line.dxf.start,line.dxf.end))>.1 or abs(math.hypot(a.x-b.x,a.y-b.y)-circle.dxf.radius-other.dxf.radius)>.1:raise ValueError('Native tangent circle geometry differs')
    elif any(doc.entitydb.get(h) is None or doc.entitydb[h].dxftype()!='SPLINE' for h in handles):raise ValueError('Native waveform is not the declared source SPLINE')
    paths=source_paths(doc,handles)
    if not paths:raise ValueError('Native terminal glyph has no source geometry')
    return paths
