"""Read existing separate drawing ports without naming a remote connection.

This is the geometry portion of the native capped/external-port readers. A
common marker and its centre spans never create a pipe-to-pipe connection.
"""
import math
from crossview_equipment_branch_inventory import index_graph
from native_external_pipe_destination import on_segment
from native_named_riser_evidence import xyz,LAYERS
from native_path_coverage_audit import audit

MODE='native_separate_drawing_marker_port_geometry_v1'

def collect(doc,graph,node_id,source_hash,graph_hash):
    if graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('marker source graph differs')
    nodes,edges,adj=index_graph(graph);node=nodes[node_id];marker=doc.entitydb.get(node.get('source_marker_handle'))
    if node.get('node_type')!='virtual_equipment'or node.get('subtype')!='external_system_interface':raise ValueError('drawing marker is not a typed source interface')
    if marker is None or marker not in doc.modelspace()or marker.dxftype()!='LWPOLYLINE'or marker.dxf.layer!='DIM_SYMB'or marker.closed or marker.has_arc or marker.has_width or tuple(marker.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('unsupported native drawing marker')
    vertices=[[float(x),float(y),float(marker.dxf.elevation)]for x,y in marker.get_points('xy')]
    if len(vertices)<3 or any(not math.isfinite(v)for p in vertices for v in p):raise ValueError('invalid drawing marker vertices')
    ports=node.get('ports',[])
    if not ports or len({p['port_id']for p in ports})!=len(ports):raise ValueError('unique separate drawing ports required')
    rows=[];claimed=set();edge_ids=set()
    for port in ports:
        matches=[(e,side)for e in adj[node_id]for side in('start','end')if e.get(side+'_node_id')==node_id and e.get(side+'_port_id')==port['port_id']]
        if len(matches)!=1:raise ValueError('drawing port has no unique edge owner')
        edge,side=matches[0]
        if edge.get('connection_mode')!='standalone_omission_to_first_tee':raise ValueError('unsupported drawing boundary branch owner')
        if port.get('node_id',node_id)!=node_id or port.get('source_marker_handle')!=marker.dxf.handle or edge.get('source_insert_handle')!=marker.dxf.handle or edge['system']!=port['system']or edge['edge_id']in edge_ids:raise ValueError('drawing port source or system differs')
        paths=edge.get('attribute_paths',[])
        if len(paths)!=1 or len(paths[0])<3:raise ValueError('drawing port lacks source pipe after centre span')
        ordered=paths[0]if side=='start'else list(reversed(paths[0]))
        if math.dist(ordered[0],[node['x'],node['y']])>.05 or math.dist(ordered[1],[port['x'],port['y']])>.05:raise ValueError('drawing centre or port display span changed')
        proof=audit(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge['edge_id']]),source_hash,graph_hash)
        segments=proof['edges'][0]['segments'];display=0 if side=='start'else len(segments)-1;physical=[s for s in segments if s['index']!=display]
        if not physical or any(s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 or s['witnesses'][0]['scope']!='modelspace'for s in physical):raise ValueError('physical source branch has unverified segments')
        adjacent=segments[1 if side=='start'else len(segments)-2];line=doc.entitydb[adjacent['witnesses'][0]['source_handle']];ends=xyz(line)
        hits=[point for point in ends if math.dist(point[:2],[port['x'],port['y']])<=.05 and any(on_segment(point,a,b)for a,b in zip(vertices,vertices[1:]))]
        if len(hits)!=1 or line.dxf.layer!=LAYERS[port['system']]or line.dxf.handle in claimed:raise ValueError('drawing port misses its unique typed native pipe endpoint')
        claimed.add(line.dxf.handle);edge_ids.add(edge['edge_id'])
        rows.append(dict(node_id=node_id,port_id=port['port_id'],edge_id=edge['edge_id'],system=edge['system'],source_line_handle=line.dxf.handle,
            native_pipe_endpoint=hits[0],native_pipe_XYZ=ends,display_segment_index=display,display_only_centre_span=ordered[:2],physical_segments=physical,native_path_coverage=proof,
            physical_port_verified=False,physical_length_mm=None,human_accepted=False))
    if {e['edge_id']for e in adj[node_id]}!=edge_ids:raise ValueError('drawing marker port inventory is incomplete')
    contacts={line.dxf.handle for line in doc.modelspace().query('LINE')if line.dxf.layer in LAYERS.values()and any(on_segment(p,a,b)for p in xyz(line)for a,b in zip(vertices,vertices[1:]))}
    if contacts!=claimed:raise ValueError('drawing marker has extra or missing source pipe contacts')
    return dict(mode=MODE,node_id=node_id,source_marker_handle=marker.dxf.handle,marker_vertices=vertices,records=rows,
        common_marker_creates_pipe_connection=False,remote_destination_or_cap_role_assigned=False,physical_values_assigned=0,graph_mutated=False,human_accepted=False)
