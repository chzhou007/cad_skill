"""Read an explicitly expert-targeted circle's native main/branch identities.

An omitted projected branch may have no ray at the circle and may project
parallel to one main arm. Preserve actual geometry instead of fabricating a
third orthogonal ray. Authority is limited to the original marked source box.
"""
import copy,hashlib,json,math
from pathlib import Path
from crossview_equipment_branch_inventory import index_graph
from native_line_path_evidence import LAYERS,_on

STATUS='native_explicit_expert_projected_circle_main_identity_replayed'
BASIS='original_native_main_LINE_children_and_explicit_expert_projected_branch'
AUTHORITY='expert_explicit_leftmost_circle_within_original_source_bounds'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def authorities(specs):
    result=[]
    for spec in specs:
        path=Path(spec['issue']['path'])
        if spec['basis']!=AUTHORITY or sha(path)!=spec['issue']['sha256']:raise ValueError('projected-circle expert authority changed')
        issue=json.loads(path.read_text(encoding='utf8'))
        if issue['issue']['note']!=spec['expected_expert_note']:raise ValueError('explicit expert source extent/note changed')
        box=issue['issue']['sourceBounds']
        if len(box)!=4 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in box)or min(box[2:])<=0:raise ValueError('original marked native source box required')
        result.append(dict(issue=copy.deepcopy(spec['issue']),basis=AUTHORITY,source_sha256=issue['sourceHashes']['main_dxf'],
            issue_label=issue['issue']['label'],source_bounds=box,explicit_expert_note=issue['issue']['note']))
    return result
def inside(point,box):return box[0]-.05<=point[0]<=box[0]+box[2]+.05 and box[1]-.05<=point[1]<=box[1]+box[3]+.05

def collect(doc,graph,nid,source_hash,graph_hash,allowed):
    nodes,edges,adj=index_graph(graph);node=nodes[nid];incident=adj[nid];point=[node['x'],node['y']]
    if graph.get('metadata',{}).get('source_sha256')!=source_hash or node.get('node_type')!='tee' or node.get('review_required')is True or len(incident)!=3 or {e['system']for e in incident}!={node.get('system')} or node.get('system')not in LAYERS:raise ValueError('projected circle current T/service/source differs')
    branches=[e for e in incident if e.get('source_expert_circle_link')];meta=node.get('expert_circle_evidence',{})
    if len(branches)!=1 or not meta:raise ValueError('projected circle original branch/main identity missing')
    branch=branches[0];link=branch['source_expert_circle_link'];circle=doc.entitydb.get(link.get('circle_handle',''));main=doc.entitydb.get(link.get('main_source_handle',''));tail=doc.entitydb.get(link.get('branch_source_handle',''))
    if (not circle or circle.dxftype()!='CIRCLE'or not main or not tail or main.dxftype()!='LINE'or tail.dxftype()!='LINE'
        or any(e not in doc.modelspace()or e.dxf.layer!=LAYERS[node['system']]for e in (circle,main,tail))
        or meta.get('circle_handle')!=link['circle_handle']or meta.get('main_handle')!=link['main_source_handle']or meta.get('branch_handle')!=link['branch_source_handle']
        or meta.get('expert_issue')!=link.get('expert_issue')or link.get('logical_projection_is_not_a_measured_pipe')is not True
        or link.get('physical_length')!='unknown'or link.get('relative_elevation')!='unknown'
        or math.dist(list(circle.dxf.center)[:2],point)>.05 or math.dist(link.get('circle_center',[]),point)>.05
        or not _on(point,list(main.dxf.start)[:2],list(main.dxf.end)[:2],.05)):
        raise ValueError('projected circle native source identity or display-only contract differs')
    endpoint=link.get('source_endpoint',[])
    if len(endpoint)!=2 or math.dist(endpoint,point)<=circle.dxf.radius or min(math.dist(endpoint,list(p)[:2])for p in (tail.dxf.start,tail.dxf.end))>.05:raise ValueError('native remote branch endpoint differs')
    matches=[a for a in allowed if a['source_sha256']==source_hash and a['issue_label']==link['expert_issue']and inside(point,a['source_bounds'])and inside(endpoint,a['source_bounds'])]
    if len(matches)!=1:raise ValueError('projected circle connection lies outside an explicit expert source extent; similar-location inference remains pending')
    authority=matches[0];circles=[c for c in doc.modelspace().query('CIRCLE')if c.dxf.layer==LAYERS[node['system']]and inside(list(c.dxf.center)[:2],authority['source_bounds'])]
    if (not circles or abs(min(c.dxf.center.x for c in circles)-point[0])>.05
        or len([c for c in circles if abs(c.dxf.center.x-point[0])<=.05])!=1):raise ValueError('expert leftmost source circle is not unique')
    mains=[e for e in incident if e is not branch];rays=[]
    for edge in mains:
        if link['main_source_handle']not in edge.get('source_handles',[]):raise ValueError('main children leave the explicitly targeted original LINE')
        hits=[]
        for path in edge['attribute_paths']:
            for a,b in zip(path,path[1:]):
                if math.dist(a,point)<=.05 and math.dist(b,point)>.05:hits.append((a,b))
                elif math.dist(b,point)<=.05 and math.dist(a,point)>.05:hits.append((b,a))
        if len(hits)!=1:raise ValueError('native main child center ray ambiguous')
        a,b=hits[0]
        if not all(_on(p,list(main.dxf.start)[:2],list(main.dxf.end)[:2],.05)for p in (a,b)):raise ValueError('main child ray not on original LINE')
        competing=[e.dxf.handle for e in doc.modelspace().query('LINE')if e.dxf.layer==LAYERS[node['system']]and all(_on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)for p in (a,b))]
        if competing!=[main.dxf.handle]:raise ValueError('competing native main LINEs')
        rays.append(dict(edge_id=edge['edge_id'],source_line_handle=main.dxf.handle,graph_segment=[a,b],direction=[(b[i]-a[i])/math.dist(a,b)for i in (0,1)],scope='native_original_main_LINE_child'))
    if sum(a*b for a,b in zip(rays[0]['direction'],rays[1]['direction']))>-math.cos(math.radians(1)):raise ValueError('original main children are not opposing native arms')
    contacts=[]
    for path in branch['attribute_paths']:
        for a,b in zip(path,path[1:]):
            if math.dist(a,endpoint)<=.05:contacts.append((a,b))
            elif math.dist(b,endpoint)<=.05:contacts.append((b,a))
    if len(contacts)!=1 or link['branch_source_handle']not in branch.get('source_handles',[]):raise ValueError('native omitted branch source contact is ambiguous')
    a,b=contacts[0]
    if not all(_on(p,list(tail.dxf.start)[:2],list(tail.dxf.end)[:2],.05)for p in (a,b)):raise ValueError('projected branch contact leaves original LINE')
    competing=[e.dxf.handle for e in doc.modelspace().query('LINE')if e.dxf.layer==LAYERS[node['system']]and all(_on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)for p in (a,b))]
    if competing!=[tail.dxf.handle]:raise ValueError('competing native projected branch LINEs')
    rays.append(dict(edge_id=branch['edge_id'],source_line_handle=tail.dxf.handle,graph_segment=[a,b],direction=[(b[i]-a[i])/math.dist(a,b)for i in (0,1)],scope='actual_remote_native_branch_LINE_not_a_center_ray'))
    return dict(status=STATUS,source_sha256=source_hash,graph_sha256=graph_hash,graph_mutated=False,human_accepted=False,
        junctions=[dict(node_id=nid,system=node['system'],position=point,source_rays=rays)],
        original_main_identity=dict(through=sorted(e['edge_id']for e in mains),branch=branch['edge_id'],main_source_handle=main.dxf.handle,circle_handle=circle.dxf.handle,branch_source_handle=tail.dxf.handle),
        explicit_expert_authority=copy.deepcopy(authority),branch_center_ray_fabricated=False,physical_connector_length_mm=None,physical_flow_direction_inferred=False)

def role(graph,nid,proof,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);identity=proof.get('original_main_identity',{});ids=identity.get('through',[])+[identity.get('branch')]
    if (proof.get('status')!=STATUS or proof.get('source_sha256')!=source_hash or proof.get('graph_sha256')!=graph_hash or proof.get('graph_mutated')is not False
        or proof.get('branch_center_ray_fabricated')is not False or proof.get('physical_connector_length_mm')is not None
        or len(identity.get('through',[]))!=2 or len(set(ids))!=3 or set(ids)!={e['edge_id']for e in adj[nid]}or {edges[e]['system']for e in ids}!={nodes[nid].get('system')}
        or nodes[nid].get('review_required')is True or nodes[nid]['node_type']!='tee'
        or not inside([nodes[nid]['x'],nodes[nid]['y']],proof.get('explicit_expert_authority',{}).get('source_bounds',[0,0,-1,-1]))):raise ValueError('explicit projected-circle role source contract differs')
    link=edges[identity['branch']].get('source_expert_circle_link',{})
    if link.get('main_source_handle')!=identity['main_source_handle']or link.get('branch_source_handle')!=identity['branch_source_handle']or link.get('circle_handle')!=identity['circle_handle']:raise ValueError('projected-circle role no longer matches current source identity')
    return dict(through=copy.deepcopy(identity['through']),branch=identity['branch'],source_T_proof=copy.deepcopy(proof),role_basis=BASIS,physical_flow_direction_inferred=False)
