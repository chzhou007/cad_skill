"""Validate scoped native axis DN display records, never whole-edge values."""
import math,re


def on(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    if not length:return False
    u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
    return -.05/length<=u<=1+.05/length and math.dist(p,[a[0]+u*dx,a[1]+u*dy])<=.05


def validate(graph,native_doc=None,native_source_sha256=None):
    edge_rows=[r for e in graph['edges'] for r in e.get('axis_riser_attributes',[])];root=graph.get('sourceAxisRiserSegmentAttributes')
    if not edge_rows and root is None:return 0
    if (not edge_rows or not isinstance(root,dict) or root.get('status')!='source_checked_axis_segment_DN_hil_pending'
        or root.get('local_topology_and_all_plan_attributes_preserved') is not True or root.get('human_accepted') is not False
        or root.get('whole_edge_DN_assigned')!=0 or root.get('installed_lengths_assigned')!=0):raise ValueError('invalid axis riser attribute root or extent')
    if native_doc is None or not native_source_sha256 or root.get('source_sha256')!=native_source_sha256:raise ValueError('axis riser attribute validation needs its original native source context')
    key=lambda r:(r['edge_id'],r['path_index'],r['segment_index']);declared=root.get('records',[])
    if len({key(r) for r in edge_rows})!=len(edge_rows) or {key(r):r for r in declared}!={key(r):r for r in edge_rows} or len(declared)!=len(edge_rows):raise ValueError('axis riser root and unique edge records differ')
    layers={'supply':'\u7a7a\u8c03\u51b7\u51bb\u6c34\u4f9b\u6c34','return':'\u7a7a\u8c03\u51b7\u51bb\u6c34\u56de\u6c34'};hash=re.compile(r'[0-9a-f]{64}')
    for edge in graph['edges']:
        for r in edge.get('axis_riser_attributes',[]):
            pi=r['path_index'];si=r['segment_index'];value=r.get('nominal_mm');paths=edge.get('attribute_paths',[])
            if (not isinstance(pi,int) or isinstance(pi,bool) or not isinstance(si,int) or isinstance(si,bool) or not 0<=pi<len(paths)
                or not 0<=si<len(paths[pi])-1 or r.get('scope_points')!=paths[pi][si:si+2] or r['edge_id']!=edge['edge_id'] or r['system']!=edge['system']):raise ValueError('axis riser segment placement differs')
            if (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0
                or r.get('scope')!='native_axis_vertical_segment_DN_only' or r.get('human_accepted') is not False
                or r.get('whole_edge_nominal_mm') is not None or r.get('physical_length_mm') is not None or r.get('whole_edge_physical_length_mm') is not None):raise ValueError('axis riser record promotes unknown mixed-edge values')
            if any(not hash.fullmatch(r.get(k,'')) for k in ('source_scope_sha256','source_sha256','local_graph_sha256','attribute_parent_graph_sha256')):raise ValueError('axis riser source hash missing')
            if any(r.get(k)!=root.get(k) for k in ('source_scope_sha256','source_sha256','local_graph_sha256','attribute_parent_graph_sha256')):raise ValueError('axis riser record source differs from root')
            line=native_doc.entitydb.get(r.get('source_line_handle'))
            if line is None or line not in native_doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=layers.get(edge['system']):raise ValueError('axis riser native LINE/system differs')
            a,b=[list(line.dxf.start)[:2],list(line.dxf.end)[:2]]
            if not all(on(p,a,b) for p in r['scope_points']):raise ValueError('axis riser points lack original native LINE coverage')
    return len(edge_rows)
