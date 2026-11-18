"""Create viewer-only leaf proxies for explicit, source-pinned non-node boundaries."""
import copy, hashlib, math

def adapt_typed_boundaries(graph, source_path, doc):
    if graph.get('metadata', {}).get('graph_format') != 'experimental-typed-boundaries-v1':
        return copy.deepcopy(graph)
    g = copy.deepcopy(graph)
    if g['metadata'].get('hil_ready') is not False:
        raise ValueError('Experimental boundary graph must keep HIL disabled')
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if g['metadata'].get('source_sha256') != digest:
        raise ValueError('Typed boundary source hash mismatch')
    nodes = {n['node_id']: n for n in g['nodes']}
    anchors = g.get('boundary_anchors')
    if not isinstance(anchors, list):
        raise ValueError('Typed boundary list required')
    by_id = {a['boundary_id']: a for a in anchors}
    if len(by_id) != len(anchors) or set(by_id) & set(nodes):
        raise ValueError('Boundary ID collision')
    counts = {k: 0 for k in by_id}
    for edge in g['edges']:
        for side in ('start', 'end'):
            nid = edge.get(side+'_node_id'); bid = edge.get(side+'_boundary_id')
            if bool(nid) == bool(bid):
                raise ValueError('Every edge endpoint needs exactly one node or boundary')
            if nid:
                if nid not in nodes: raise ValueError('Missing edge node')
                continue
            if bid not in by_id: raise ValueError('Missing boundary anchor')
            a = by_id[bid]
            if a.get('system') != edge.get('system') or a.get('source_pipe_handle') not in edge.get('source_handles', []):
                raise ValueError('Boundary and edge source/system mismatch')
            counts[bid] += 1
            edge[side+'_node_id'] = bid
            edge[side+'_viewer_boundary_id'] = edge.pop(side+'_boundary_id')
            edge[side+'_port_id'] = bid+'-'+edge['edge_id']
    if any(v != 1 for v in counts.values()):
        raise ValueError('Only one-edge boundary leaves can be adapted')
    for aid, a in by_id.items():
        old = a.get('legacy_node', {})
        user = a.get('kind') == 'user_confirmed_non_node_source_boundary'
        if user:
            if len(a.get('user_confirmation_sha256','')) != 64 or a.get('destination_kind') != 'terminal_air_conditioning_equipment' or a.get('destination_instance') != 'unknown' or a.get('destination_port') != 'unknown':
                raise ValueError('User boundary evidence incomplete')
            glyphs=a.get('source_glyph_handles',[])
            if len(glyphs)!=4 or len(set(glyphs))!=4 or any(not doc.entitydb.get(h) or doc.entitydb.get(h).dxftype()!='LINE' or doc.entitydb.get(h).dxf.layer!='空调立管、水平支管' for h in glyphs):
                raise ValueError('User boundary glyph evidence incomplete')
        elif a.get('kind') != 'expert_non_node_source_boundary' or not a.get('expert_issue') or a.get('connectivity_beyond_boundary') != 'unknown':
            raise ValueError('Boundary evidence incomplete')
        if old.get('node_type') != 'virtual_equipment' or old.get('subtype') not in (('unresolved_source_terminal','out_of_plane_interface') if user else ('unresolved_source_terminal',)) or old.get('system') != a.get('system'):
            raise ValueError('Invalid source endpoint proxy')
        pipe = doc.entitydb.get(a['source_pipe_handle'])
        if not pipe or pipe.dxftype() != 'LINE': raise ValueError('Boundary source line missing')
        x,y=a['x'],a['y']
        if min(math.hypot(p.x-x,p.y-y) for p in (pipe.dxf.start,pipe.dxf.end))>(1.0 if user else .01):
            raise ValueError('Boundary source coordinate mismatch')
        if a.get('source_marker_kind')=='two_bar':
            handles=a.get('source_marker_handles',[]); bars=[doc.entitydb.get(h) for h in handles]
            if len(handles)!=2 or len(set(handles))!=2 or any(not e or e.dxftype()!='LINE' or e.dxf.layer!=a.get('source_marker_layer') for e in bars):raise ValueError('Boundary two-bar marker missing')
            first,second=bars;u,v=first.dxf.start,first.dxf.end;r,s=second.dxf.start,second.dxf.end;lengths=a.get('source_marker_lengths',[])
            if len(lengths)!=2 or abs(u.y-v.y)>.01 or abs(r.y-s.y)>.01 or abs(abs(u.x-v.x)-lengths[0])>.2 or abs(abs(r.x-s.x)-lengths[1])>.2 or abs((u.x+v.x-r.x-s.x)/2)>.1 or abs(abs(u.y-r.y)-a['source_marker_spacing'])>.2 or math.hypot((u.x+v.x)/2-x,u.y-y)>.6:raise ValueError('Boundary two-bar marker geometry mismatch')
            if a.get('evidence_basis')=='source_similar_inferred':
                ref=a.get('reference_marker_handles',[]);refbars=[doc.entitydb.get(h) for h in ref];refpipe=doc.entitydb.get(a.get('reference_pipe_handle'))
                if a.get('expert_review')!='unreviewed' or not a.get('reference_expert_node_id') or len(ref)!=2 or any(not z or z.dxftype()!='LINE' or z.dxf.layer!=a.get('source_marker_layer') for z in refbars) or not refpipe or refpipe.dxftype()!='LINE' or refpipe.dxf.layer!=pipe.dxf.layer:raise ValueError('Inferred boundary reference missing')
        else:
            circle = doc.entitydb.get(a['source_circle_handle'])
            if not circle or circle.dxftype() != 'CIRCLE' or circle.dxf.layer != pipe.dxf.layer:raise ValueError('Boundary circle and pipe mismatch')
            if math.hypot(circle.dxf.center.x-x,circle.dxf.center.y-y)>1:raise ValueError('Boundary circle coordinate mismatch')
            if user and any(max(math.hypot(v.x-circle.dxf.center.x,v.y-circle.dxf.center.y) for v in (doc.entitydb.get(h).dxf.start,doc.entitydb.get(h).dxf.end))>220 for h in a['source_glyph_handles']):raise ValueError('User boundary glyph location mismatch')
        if old.get('x') != x or old.get('y') != y:
            raise ValueError('Boundary and legacy coordinates mismatch')
        proxy=copy.deepcopy(old); proxy.update(node_id=aid, subtype='viewer_non_node_boundary', boundary_type='viewer_non_node_boundary', viewer_non_node_boundary=True, boundary_evidence=copy.deepcopy(a), review_required=True)
        incident=next(e for e in g['edges'] if aid in (e.get('start_node_id'),e.get('end_node_id')))
        proxy['ports']=[dict(port_id=aid+'-'+incident['edge_id'],x=x,y=y,system=a['system'],status='viewer_proxy_not_physical_port',physical_port_verified=False)]
        g['nodes'].append(proxy)
    g['metadata']['viewer_boundary_adapter']='viewer-only proxies; canonical graph has separate boundary anchors'
    return g
