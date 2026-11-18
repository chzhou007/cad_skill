"""Read an existing native detail-circle T without requiring an equipment owner.

Reuse the original canonical detail T verifier. This proves only local native
incidence and pipe rays, never a main/detail alias, physical port or metric.
"""
import math
from canonicalize_confirmed_sideviews import verify_tee
from crossview_equipment_branch_inventory import index_graph
from native_line_path_evidence import LAYERS,_on

STATUS='native_local_detail_circle_T_replayed_without_equipment_owner'

def collect(doc,graph,node_id,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);node=nodes[node_id];incident=adj[node_id]
    branches=[e for e in incident if e.get('source_detail_circle_length_evidence')]
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash
        or node.get('node_type')!='tee' or node.get('review_required')is True
        or node.get('system')not in LAYERS or len(incident)!=3 or len(branches)!=1
        or {e.get('system')for e in incident}!={node['system']}):
        raise ValueError('local detail T source/incidence/service is not uniquely established')
    branch=branches[0];circle_proof=branch['source_detail_circle_length_evidence'];point=[node['x'],node['y']]
    circle=doc.entitydb.get(circle_proof.get('source_circle_handle',''));contact=circle_proof.get('line_contact',[])
    if (not circle or circle.dxftype()!='CIRCLE'or circle not in doc.modelspace()
        or circle_proof.get('circle_center_to_rim_is_display_only')is not True
        or circle_proof.get('physical_connection_length')!='unknown'
        or circle_proof.get('source_line_handle')not in branch.get('source_handles',[])
        or len(contact)!=2 or len(circle_proof.get('circle_center',[]))!=2
        or math.dist(circle_proof['circle_center'],point)>.05
        or math.dist(list(circle.dxf.center)[:2],point)>.05
        or abs(math.dist(contact,point)-circle.dxf.radius)>.05
        or abs(circle_proof.get('circle_radius_drawing_units',-1)-circle.dxf.radius)>.05):
        raise ValueError('local detail circle/rim display-only source contract differs')
    matches=[c for c in doc.modelspace().query('CIRCLE')if math.dist(list(c.dxf.center)[:2],point)<=.05 and abs(c.dxf.radius-circle.dxf.radius)<=.05]
    if len(matches)!=1:raise ValueError('local detail circle source is ambiguous')
    terminal=[branch.get(k)for k in ('start_node_id','end_node_id','start_boundary_id','end_boundary_id')if branch.get(k)and branch[k]!=node_id]
    if len(terminal)!=1:raise ValueError('local detail branch terminal is ambiguous')
    proof,checked=verify_tee(doc,graph,branch,terminal[0])
    if proof['tee']!=node_id or checked!=branch:raise ValueError('native detail T requires a separate source-path repair')
    by={r['edge_id']:r['native_handles']for r in proof['native_rays']};rays=[]
    for edge in incident:
        handles=by[edge['edge_id']]
        if len(handles)!=1:raise ValueError('local detail native ray source is ambiguous')
        handle=handles[0];line=doc.entitydb.get(handle)
        if not line or line.dxftype()!='LINE' or line not in doc.modelspace()or line.dxf.layer!=LAYERS[node['system']]:
            raise ValueError('local detail source LINE/service differs')
        xyz=[list(line.dxf.start),list(line.dxf.end)]
        if any(not math.isfinite(v)for p in xyz for v in p):raise ValueError('nonfinite native detail XYZ')
        anchor=branch['source_detail_circle_length_evidence']['line_contact']if edge is branch else point
        contacts=[]
        for path in edge['attribute_paths']:
            for a,b in zip(path,path[1:]):
                if math.dist(a,anchor)<=.05 and math.dist(b,anchor)>.05:contacts.append((a,b))
                elif math.dist(b,anchor)<=.05 and math.dist(a,anchor)>.05:contacts.append((b,a))
        if len(contacts)!=1:raise ValueError('local detail graph ray is ambiguous')
        a,b=contacts[0]
        if not all(_on(p,xyz[0][:2],xyz[1][:2],.05)for p in (a,b)):raise ValueError('local detail ray leaves its original LINE')
        competitors=[e.dxf.handle for e in doc.modelspace().query('LINE')if e.dxf.layer==LAYERS[node['system']]
            and all(_on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)for p in (a,b))]
        if competitors!=[handle]:raise ValueError('competing native detail source LINEs')
        rays.append(dict(edge_id=edge['edge_id'],source_line_handle=handle,graph_segment=[a,b],
            direction=[(b[i]-a[i])/math.dist(a,b)for i in (0,1)],native_endpoints_wcs=xyz,
            scope='local_detail_circle_rim'if edge is branch else'native_local_detail_main_LINE'))
    return dict(status=STATUS,source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=point,source_rays=rays)],
        local_terminal_id=terminal[0],original_detail_T_verification=proof,
        equipment_ownership_inferred=False,main_detail_correspondence_inferred=False,
        source_view_domain='detail_drawing_only_not_plan_metric_proof',physical_ports_verified=False,
        physical_length_mm=None,graph_mutated=False,human_accepted=False,hil_ready=False)
