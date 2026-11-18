"""Native rays for an already replayed explicit equipment-pair reconstruction.

The caller must first independently replay the local plan parent stage (as the
branch inventory and plan DN entries do). This reader does not invent an expert
answer, equipment port, rim-to-main pipe or installed length.
"""
import hashlib,math,re
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS,_on
from native_equipment_body import body_straight_segments
from reconstruct_confirmed_equipment_pairs import DECISION

def collect(doc,graph,node_id,source_hash,graph_hash):
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate confirmed-pair graph identity')
    node=nodes[node_id];meta=node.get('source_confirmed_equipment_pair_circle',{});root=graph.get('confirmedEquipmentPairReconstruction',{})
    if (node.get('node_type')!='tee' or node.get('review_required') is True or node.get('system') not in LAYERS
        or root.get('source_sha256')!=source_hash or meta.get('source_sha256')!=source_hash
        or meta.get('input_graph_sha256')!=root.get('input_graph_sha256')
        or root.get('supply_return_independent') is not True or root.get('physical_ports_verified') is not False
        or root.get('physical_lengths_complete') is not False or meta.get('physical_port_verified') is not False
        or meta.get('physical_length')!='unknown' or meta.get('circle_main_offset_is_physical_length') is not False
        or meta.get('confirmation_basis')!='explicit_equipment_pair_reply'):raise ValueError('confirmed-pair source/root/unknown scope differs')
    records=[r for r in root.get('records',[]) if r.get('tee')==node_id or r.get('circle_handle')==meta.get('circle_handle')]
    if len(records)!=1:raise ValueError('confirmed-pair repair record not unique')
    record=records[0];did=record['equipment_id'];branch=edges[record['branch_edge']]
    if (record['tee']!=node_id or record['circle_handle']!=meta.get('circle_handle') or record['system']!=node['system']
        or meta.get('system')!=node['system'] or meta.get('equipment_id')!=did or meta.get('edge_id')!=branch['edge_id']
        or branch.get('source_confirmed_equipment_pair_circle')!=meta or branch.get('system')!=node['system']
        or {branch.get('start_node_id'),branch.get('end_node_id')}!={node_id,did}):raise ValueError('confirmed-pair owner/branch changed')
    owner=nodes.get(did);attachment=branch.get('confirmed_equipment_interface',{});confirmation=attachment.get('confirmation',{})
    if (not owner or owner.get('node_type')!='equipment' or owner.get('source_handle')!=meta.get('equipment_handle')
        or owner.get('floor')!=node.get('floor') or attachment.get('source_sha256')!=source_hash
        or attachment.get('physical_port_verified') is not False or attachment.get('interface_to_equipment_length_known') is not False
        or attachment.get('original_interface',{}).get('source_handle')!=meta.get('interface_handle')
        or confirmation.get('confirmed_by')!='user' or confirmation.get('answer')!=DECISION
        or not re.fullmatch(r'[0-9a-f]{64}',confirmation.get('reply_sha256',''))
        or branch.get(str(attachment.get('interface_side'))+'_node_id')!=did):raise ValueError('confirmed-pair equipment/attachment provenance differs')
    questions=[q for q in root.get('questions',[]) if q.get('question_id')==meta.get('question_id')]
    if (len(questions)!=1 or did not in questions[0].get('question','') or questions[0].get('answer')!=meta.get('answer')
        or questions[0]['answer'].get('decision')!=DECISION or confirmation.get('records',[]).count(questions[0])!=1
        or not re.fullmatch(r'[0-9a-f]{64}',meta.get('pair_sha256',''))):raise ValueError('confirmed-pair original question/answer/Pair differs')
    incident=[e for e in edges.values() if node_id in (e.get('start_node_id'),e.get('end_node_id'))]
    if len(incident)!=3 or {e.get('system') for e in incident}!={node['system']}:raise ValueError('confirmed-pair three-way incidence unresolved or mixed')
    point=[node['x'],node['y']]
    if point!=record.get('topology_anchor') or point!=meta.get('point'):raise ValueError('confirmed-pair topology anchor changed')
    circle=doc.entitydb.get(meta.get('circle_handle'));main=doc.entitydb.get(meta.get('main_handle'));native_branch=doc.entitydb.get(meta.get('branch_handle'))
    if (circle is None or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace()
        or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or circle.dxf.layer!=meta.get('circle_layer')
        or main is None or native_branch is None or any(e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=LAYERS[node['system']] for e in (main,native_branch))):raise ValueError('confirmed-pair native types/layers differ')
    for entity,key in [(main,'native_main_endpoints_wcs'),(native_branch,'native_branch_endpoints_wcs')]:
        actual=[list(entity.dxf.start),list(entity.dxf.end)]
        if actual!=meta.get(key) or any(not math.isfinite(v) for p in actual for v in p):raise ValueError('confirmed-pair native XYZ differs')
    center=list(circle.dxf.center)
    if center!=meta.get('native_circle_center_wcs') or any(not math.isfinite(v) for v in center):raise ValueError('confirmed-pair native circle XYZ differs')
    if any(meta['circle_handle'] in b.get('source_marker_handles',[]) for b in graph.get('boundary_anchors',[])):raise ValueError('confirmed non-node boundary protects this circle')
    rim=meta.get('source_rim',[]);radius=circle.dxf.radius;limit=meta.get('maximum_circle_main_offset_drawing_units')
    if (len(rim)!=2 or any(not math.isfinite(v) for v in rim) or not math.isfinite(radius) or radius<=0
        or isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit) or not 0<=limit<=radius*.02
        or not _on(point,list(main.dxf.start)[:2],list(main.dxf.end)[:2],.05)
        or abs(math.dist(rim,center[:2])-radius)>.05 or min(math.dist(rim,list(p)[:2]) for p in (native_branch.dxf.start,native_branch.dxf.end))>.05
        or math.dist(point,center[:2])>limit+.00001 or abs(math.dist(point,center[:2])-meta.get('actual_circle_main_offset',-1))>.00001):raise ValueError('confirmed-pair rim or original bounded main offset differs')
    a,b=list(native_branch.dxf.start)[:2],list(native_branch.dxf.end)[:2];delta=[b[i]-a[i] for i in (0,1)]
    if math.dist(a,b)<=.05 or abs((center[0]-a[0])*delta[1]-(center[1]-a[1])*delta[0])/math.dist(a,b)>.05:raise ValueError('confirmed circle leaves native branch axis')
    insert=doc.entitydb.get(meta.get('equipment_handle'));caption=doc.entitydb.get(meta.get('native_caption_handle'))
    if (insert is None or insert.dxftype()!='INSERT' or insert not in doc.modelspace() or caption is None
        or caption.dxftype() not in ('TEXT','MTEXT') or caption not in doc.modelspace() or caption.plain_text().strip()!=did):raise ValueError('confirmed-pair native equipment/caption differs')
    segments,unsupported=body_straight_segments(insert)
    if unsupported or not segments:raise ValueError('confirmed equipment native body incomplete')
    pts=[p for a,b in segments for p in (a,b)];bounds=[min(p[0] for p in pts),max(p[0] for p in pts),min(p[1] for p in pts),max(p[1] for p in pts)]
    if any(not math.isfinite(v) for p in pts for v in p) or math.dist([(bounds[0]+bounds[1])/2,(bounds[2]+bounds[3])/2],[owner['x'],owner['y']])>.05:raise ValueError('confirmed native equipment body moved')
    if not bounds[0]<=caption.dxf.insert.x<=bounds[1] or not bounds[2]<=caption.dxf.insert.y<=bounds[3]:raise ValueError('confirmed caption leaves native body')
    rays=[];directions=[]
    for edge in incident:
        anchor=rim if edge is branch else point
        if edge is not branch:
            split=edge.get('split_source_edge',{})
            if edge['edge_id'] not in record.get('main_child_edges',[]) or split.get('edge_id')!=record.get('main_source_edge') or split.get('source_graph_sha256')!=root['input_graph_sha256']:raise ValueError('confirmed-pair unrecorded main child/split')
        touches=[]
        for path in edge.get('attribute_paths',[]):
            for a,b in zip(path,path[1:]):
                if math.dist(a,anchor)<=.05 and math.dist(b,anchor)>.05:touches.append((a,b))
                elif math.dist(b,anchor)<=.05 and math.dist(a,anchor)>.05:touches.append((b,a))
        if len(touches)!=1:raise ValueError('confirmed-pair native graph ray not unique')
        a,b=touches[0];handle=meta['branch_handle'] if edge is branch else meta['main_handle']
        hits=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS[node['system']] and _on(a,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05) and _on(b,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
        if hits!=[handle] or handle not in edge.get('source_handles',[]):raise ValueError('confirmed-pair source ray witness ambiguous or changed')
        direction=[(b[i]-a[i])/math.dist(a,b) for i in (0,1)]
        if any(sum(x*y for x,y in zip(direction,u))>math.cos(math.radians(.1)) for u in directions):raise ValueError('coincident confirmed-pair rays')
        directions.append(direction)
        rays.append(dict(edge_id=edge['edge_id'],source_line_handle=handle,graph_segment=[a,b],direction=direction,scope='explicit_equipment_pair_circle_rim' if edge is branch else 'native_main_LINE'))
    return dict(status='native_confirmed_equipment_pair_circle_replayed_parent_verification_required',source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=point,source_rays=rays)],
        original_confirmation=dict(question_id=meta['question_id'],pair_sha256=meta['pair_sha256'],reply_sha256=confirmation['reply_sha256'],root_sha256=hashlib.sha256(encode(root)).hexdigest()),
        native_XYZ=dict(circle=center,main=meta['native_main_endpoints_wcs'],branch=meta['native_branch_endpoints_wcs']),
        circle_main_offset=meta['actual_circle_main_offset'],physical_connector_length=None,physical_ports_verified=False,graph_mutated=False,human_accepted=False,hil_ready=False)
