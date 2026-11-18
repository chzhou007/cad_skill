"""Reapply unchanged legacy omission geometry and crossover kernels.

Thirty drawing units locate an existing nonphysical omission boundary, never
another pipe node or equipment. Native gap spans remain unknown lengths and do
not join the crossed pipe, including a same-system crossing.
"""
import collections,copy,dataclasses,math
from inherited_exploded_ball_profiles import owner
from crossview_equipment_branch_inventory import index_graph
from native_drawing_marker_ports import collect as original_ports
from native_path_coverage_audit import audit as original_paths
from native_line_path_evidence import LAYERS
from legacy_named_provider_inventory import require

MODE='inherited_native_omission_marker_and_crossover_evidence_v1'
BRIDGE='original_native_crossover_gap_replayed'

def same_pair(a,b,c,d):
    return min(max(math.dist(a,c),math.dist(b,d)),max(math.dist(a,d),math.dist(b,c)))<=.05

def population(doc,source_hash):
    old=owner();reverse={v:k for k,v in LAYERS.items()};lines=[e for e in doc.modelspace().query('LINE')if e.dxf.layer in reverse]
    segments=[old.graph.Segment(reverse[e.dxf.layer],tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2])for e in lines]
    healed,bridges=old.graph.bridge_pipe_crossover_gaps(segments)
    tees=lambda ss:{(t.system,t.x,t.y)for t in old.graph.detect_tee_nodes(ss)}
    require(tees(segments)==tees(healed),'original crossover reapplication changed the native T population')
    markers={}
    for e in doc.modelspace().query('LWPOLYLINE'):
        if e.dxf.layer!='DIM_SYMB'or e.closed or e.has_arc or e.has_width or tuple(e.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):continue
        vertices=[tuple(float(v)for v in p)for p in e.get_points('xy')]
        if len(vertices)==6 and all(math.isfinite(v)for p in vertices for v in p):markers[e.dxf.handle]=vertices
    endpoints={}
    for system in('supply','return'):
        adj,points=old.equipment_graph.build_owner_network([s for s in healed if s.system==system],[])
        endpoints[system]={key:point for key,point in points.items()if len(adj[key])==1}
    return dict(source_sha256=source_hash,doc=doc,owner=old,lines=lines,bridges=[dataclasses.asdict(b)for b in bridges],markers=markers,endpoints=endpoints,
                proof=dict(mode=MODE,source_sha256=source_hash,native_typed_LINE_count=len(lines),original_crossover_count=len(bridges),native_T_population_before_after_equal=True,
                    original_marker_tolerance=old.VIRTUAL_PORT_MARKER_TOLERANCE,original_crossover_maximum=old.graph.MAX_CROSSOVER_GAP_LENGTH,
                    source_graph_mutated=False,new_nodes_created=0,physical_gap_lengths_assigned=0))

def crossover_for_segment(doc,segment,system,pop):
    a,b=segment['start'],segment['end'];hits=[v for v in pop['bridges']if v['system']==system and same_pair(a,b,[v['start_x'],v['start_y']],[v['end_x'],v['end_y']])]
    require(len(hits)==1,'source fragment is not one original native crossover gap')
    bridge=hits[0];endpoints=[]
    for p in(a,b):
        lines=[e for e in pop['lines']if e.dxf.layer==LAYERS[system]and min(math.dist(p,list(e.dxf.start)[:2]),math.dist(p,list(e.dxf.end)[:2]))<=.05]
        require(len(lines)==1,'crossover gap has competing or missing native endpoint LINEs')
        e=lines[0];tip=min((e.dxf.start,e.dxf.end),key=lambda q:math.dist(p,list(q)[:2]))
        endpoints.append(dict(source_handle=e.dxf.handle,native_endpoint_WCS=list(tip),native_LINE_WCS=[list(e.dxf.start),list(e.dxf.end)]))
    require(endpoints[0]['source_handle']!=endpoints[1]['source_handle']and abs(endpoints[0]['native_endpoint_WCS'][2]-endpoints[1]['native_endpoint_WCS'][2])<=.05,'crossover endpoints have another source owner or Z plane')
    crossing=[bridge['crossing_x'],bridge['crossing_y']];old=pop['owner'];chord=old.graph.Segment(system,tuple(a),tuple(b));hosts=[]
    for e in pop['lines']:
        if e.dxf.handle in {v['source_handle']for v in endpoints}:continue
        host=old.graph.Segment({v:k for k,v in LAYERS.items()}[e.dxf.layer],tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]);v=old.graph.segment_intersection_parameters(chord,host)
        if v is not None and 1e-6<v[1]<1-1e-6 and 1e-6<v[2]<1-1e-6 and math.dist(v[0],crossing)<=.05:hosts.append(e)
    require(len(hosts)==1 and hosts[0].dxf.layer==LAYERS[bridge['crossed_system']],'original crossover host is not unique')
    return dict(original_bridge=copy.deepcopy(bridge),source_endpoints=endpoints,crossed_source_LINE=dict(handle=hosts[0].dxf.handle,layer=hosts[0].dxf.layer,XYZ=[list(hosts[0].dxf.start),list(hosts[0].dxf.end)]),
        native_T_population_before_after_equal=True,crossed_pipe_connected=False,new_graph_nodes_created=0,physical_gap_length_mm=None,source_graph_mutated=False)

def path_coverage(doc,graph,edge_id,source_hash,graph_hash,pop):
    require(pop['doc']is doc and pop['source_sha256']==source_hash,'native population belongs to another source')
    result=original_paths(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge_id]),source_hash,graph_hash)
    edge=next(e for e in graph['edges']if e['edge_id']==edge_id);node_index={n['node_id']:n for n in graph['nodes']}
    marks=[(side,node_index.get(edge.get(side+'_node_id'),{}))for side in('start','end')if node_index.get(edge.get(side+'_node_id'),{}).get('subtype')=='external_system_interface']
    require(len(marks)==1 and len(edge.get('attribute_paths',[]))==1,'explicit one-marker drawing branch required')
    side,node=marks[0];segments=result['edges'][0]['segments'];display=0 if side=='start'else len(segments)-1
    for s in segments:
        if s['index']==display or s['status']=='single_source_line_covers':continue
        require(s['status']=='no_witness_in_scoped_search','a competing native path needs its own source owner')
        s['source_crossover_evidence']=crossover_for_segment(doc,s,edge['system'],pop);s['previous_native_LINE_status']=s['status'];s['status']=BRIDGE;s['physical_gap_length_mm']=None
    result.update(coverage_mode=MODE,source_graph_mutated=False,physical_gap_lengths_assigned=0,new_crossing_nodes_created=0)
    return result

def collect(doc,graph,node_id,source_hash,graph_hash,pop):
    """Keep exact original results; otherwise replay original full geometry."""
    try:return original_ports(doc,graph,node_id,source_hash,graph_hash)
    except ValueError:pass
    require(pop['doc']is doc and pop['source_sha256']==source_hash and graph.get('metadata',{}).get('source_sha256')==source_hash,'source marker identity differs')
    old=pop['owner'];nodes,edges,adj=index_graph(graph);node=nodes[node_id];h=node.get('source_marker_handle');vertices=pop['markers'].get(h)
    require(node.get('node_type')=='virtual_equipment'and node.get('subtype')=='external_system_interface'and node.get('placement_rule')=='unowned_standalone_DIM_SYMB_center'and vertices is not None,'original standalone omission marker family required')
    require(math.dist(old.equipment_graph.polyline_center(vertices),[node['x'],node['y']])<=.05,'original drawing marker centre differs')
    tolerance=old.VIRTUAL_PORT_MARKER_TOLERANCE;require(tolerance==30.,'legacy marker calibration changed')
    nearby={(system,key):point for system,points in pop['endpoints'].items()for key,point in points.items()if old.equipment_graph.point_to_polyline_distance(point,vertices)<=tolerance}
    expected={(p['system'],old.graph.point_key((p['x'],p['y']),old.graph.ENDPOINT_QUANTUM))for p in node.get('ports',[])}
    require(len(expected)==len(node.get('ports',[]))and set(nearby)==expected,'native omission terminal population has missing, extra or competing ports')
    rows=[];claimed=set()
    for p in node['ports']:
        matches=[(e,side)for e in adj[node_id]for side in('start','end')if e.get(side+'_node_id')==node_id and e.get(side+'_port_id')==p['port_id']]
        require(len(matches)==1,'drawing port lacks a unique current edge');edge,side=matches[0]
        require(edge.get('connection_mode')=='standalone_omission_to_first_tee'and p.get('source_marker_handle')==h and edge.get('source_insert_handle')==h and edge['system']==p['system'],'original marker/edge/system relation changed')
        paths=edge.get('attribute_paths',[]);require(len(paths)==1 and len(paths[0])>=3,'drawing marker branch has another path mode')
        ordered=paths[0]if side=='start'else list(reversed(paths[0]));require(math.dist(ordered[0],[node['x'],node['y']])<=.05 and math.dist(ordered[1],[p['x'],p['y']])<=.05,'original drawing centre span changed')
        proof=path_coverage(doc,graph,edge['edge_id'],source_hash,graph_hash,pop);segments=proof['edges'][0]['segments'];display=0 if side=='start'else len(segments)-1
        physical=[s for s in segments if s['index']!=display];require(physical and all(s['status']in('single_source_line_covers',BRIDGE)for s in physical),'source branch has another unsupported fragment')
        segment=segments[1 if side=='start'else len(segments)-2];require(segment['status']=='single_source_line_covers'and len(segment['witnesses'])==1 and segment['witnesses'][0]['scope']=='modelspace','native terminal needs its original LINE endpoint')
        line=doc.entitydb[segment['witnesses'][0]['source_handle']];ends=[list(line.dxf.start),list(line.dxf.end)];tips=[v for v in ends if math.dist(v[:2],[p['x'],p['y']])<=.05]
        require(len(tips)==1 and line.dxf.layer==LAYERS[p['system']]and line.dxf.handle not in claimed,'typed native terminal LINE is not unique')
        point=tips[0][:2];markers=[mh for mh,v in pop['markers'].items()if old.equipment_graph.point_to_polyline_distance(point,v)<=tolerance]
        require(markers==[h]or len(markers)==1 and markers[0]==h,'native endpoint competes with another omission marker')
        claimed.add(line.dxf.handle)
        rows.append(dict(node_id=node_id,port_id=p['port_id'],edge_id=edge['edge_id'],system=edge['system'],source_line_handle=line.dxf.handle,native_pipe_endpoint=tips[0],native_pipe_XYZ=ends,
            display_segment_index=display,display_only_centre_span=ordered[:2],physical_segments=physical,native_path_coverage=proof,original_marker_tolerance=tolerance,
            source_endpoint_to_marker_distance=old.equipment_graph.point_to_polyline_distance(point,vertices),physical_port_verified=False,physical_length_mm=None,human_accepted=False))
    require({r['edge_id']for r in rows}=={e['edge_id']for e in adj[node_id]},'drawing port cohort is incomplete')
    return dict(mode=MODE,node_id=node_id,source_marker_handle=h,marker_vertices=vertices,records=rows,original_native_marker_and_crossover_kernels_reused=True,
        common_marker_creates_pipe_connection=False,remote_destination_or_cap_role_assigned=False,physical_values_assigned=0,graph_mutated=False,human_accepted=False)
