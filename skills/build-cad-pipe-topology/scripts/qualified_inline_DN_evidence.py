"""Bind explicit component-qualified DN leaders; never infer a pipe diameter."""
import math,re
from collections import Counter
from native_dn_text_position import supported
from repair_native_flexible_joints import fingerprint


def collect(doc,graph,policy,source_hash,graph_hash):
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('qualified component DN source/graph differs')
    block=policy.get('block_name');expected=policy.get('block_fingerprint_sha256')
    if block not in doc.blocks or fingerprint(doc.blocks[block])!=expected:raise ValueError('qualified component template differs')
    if sorted(e.dxftype() for e in doc.blocks[block])!=['LINE','LINE','POINT','POINT','SPLINE']:raise ValueError('qualified component is not the supported two-port flexible joint')
    native=[]
    for ins in doc.modelspace().query('INSERT'):
        if ins.dxf.name!=block:continue
        pts=[list(e.dxf.location) for e in ins.virtual_entities() if e.dxftype()=='POINT']
        if len(pts)!=2 or any(not math.isfinite(v) for p in pts for v in p):raise ValueError('component native ports unavailable')
        native.append((ins,pts))
    ownership={}
    for edge in graph['edges']:
        for item in edge.get('source_flexible_joints',[]):
            h=item['source_handle']
            if h in ownership:raise ValueError('component ownership is not unique')
            names=[n for n in edge.get('equipment_names',[]) if n.endswith('-'+h)]
            if len(names)!=1 or edge.get('equipment_counts',{}).get('flexible_joint',0)<1:raise ValueError('component canonical identity missing')
            ownership[h]=(edge,item,names[0])
    records=[];used_text=set();used_strokes=set();used_components=set()
    for spec in policy.get('labels',[]):
        qualifier=doc.entitydb.get(spec.get('qualifier_handle'));dn=doc.entitydb.get(spec.get('dn_handle'))
        if (qualifier is None or dn is None or qualifier not in doc.modelspace() or dn not in doc.modelspace()
            or qualifier.dxftype()!='TEXT' or dn.dxftype()!='TEXT' or not supported(qualifier) or not supported(dn)
            or qualifier.plain_text()!='金属软管' or dn.plain_text()!=spec.get('expected_text')
            or qualifier.dxf.layer!=dn.dxf.layer or qualifier.dxf.style!=dn.dxf.style
            or abs(qualifier.dxf.height-dn.dxf.height)>.01 or abs(qualifier.dxf.rotation-dn.dxf.rotation)>.001):raise ValueError('component DN qualifier/text differs')
        match=re.fullmatch(r'DN([1-9][0-9]*(?:\.[0-9]+)?)',dn.plain_text())
        if not match:raise ValueError('component DN is not an explicit scalar label')
        angle=math.radians(dn.dxf.rotation);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]];height=dn.dxf.height
        q=list(qualifier.dxf.insert);p=list(dn.dxf.insert);delta=[q[i]-p[i] for i in (0,1)]
        if abs(sum(delta[i]*axis[i] for i in (0,1)))>height or not .5*height<sum(delta[i]*normal[i] for i in (0,1))<3*height:raise ValueError('component qualifier does not share the native two-line label')
        handles=spec.get('leader_handles',[]);segments=[]
        if len(handles)<2 or len(handles)!=len(set(handles)):raise ValueError('component leader must be an explicit unique star')
        for h in handles:
            e=doc.entitydb.get(h)
            if e is None or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=dn.dxf.layer:raise ValueError('component leader native line differs')
            segments.append((h,list(e.dxf.start),list(e.dxf.end)))
        points=[]
        for _,a,b in segments:
            for point in (a,b):
                if not any(math.dist(point,x)<=.00001 for x in points):points.append(point)
        hubs=[x for x in points if sum(min(math.dist(x,a),math.dist(x,b))<=.00001 for _,a,b in segments)==len(segments)]
        if len(hubs)!=1:raise ValueError('component leader is not one native shared hub')
        hub=hubs[0];to_q=sum((q[i]-hub[i])*normal[i] for i in (0,1));to_p=sum((p[i]-hub[i])*normal[i] for i in (0,1))
        if not -.00001<to_q<height or not -2*height<to_p<0 or any(not -height<sum((x[i]-hub[i])*axis[i] for i in (0,1))<2*height for x in (p,q)):raise ValueError('component text is not located at this leader hub')
        leaders=[];underlines=[]
        for h,a,b in segments:
            leaf=b if math.dist(a,hub)<=.00001 else a;delta=[leaf[i]-hub[i] for i in (0,1)]
            if abs(sum(delta[i]*normal[i] for i in (0,1)))<=.05 and sum(delta[i]*axis[i] for i in (0,1))>height:underlines.append(h);continue
            matches=[(ins,pts) for ins,pts in native if any(math.dist(leaf,pt)<=.00001 for pt in pts)]
            if len(matches)!=1:raise ValueError('component leader does not uniquely reach a native joint contact')
            ins,pts=matches[0];hjoint=ins.dxf.handle
            if hjoint not in ownership or hjoint in used_components:raise ValueError('component leader has no unique assigned owner')
            edge,item,name=ownership[hjoint]
            if item.get('source_block')!=block or item.get('physical_length')!='unknown' or item.get('parameter_status')!='unknown_not_zero':raise ValueError('component source/unknown parameter scope differs')
            if sorted(map(tuple,item.get('source_contact_points',[])))!=sorted(tuple(pt[:2]) for pt in pts):raise ValueError('component source contacts changed')
            leaders.append(dict(leader_handle=h,source_handle=hjoint,device_name=name,edge_id=edge['edge_id'],system=edge['system'],native_contact_wcs=leaf,native_joint_contacts_wcs=pts,physical_port_verified=False))
            used_components.add(hjoint)
        if len(underlines)!=1 or len(leaders)!=len(handles)-1 or not leaders:raise ValueError('unclassified leaf remains in component leader')
        if set(spec.get('expected_component_handles',[]))!={r['source_handle'] for r in leaders}:raise ValueError('component leader population differs')
        if any(h in used_text for h in (qualifier.dxf.handle,dn.dxf.handle)) or used_strokes.intersection(handles):raise ValueError('component label ownership repeated')
        used_text.update((qualifier.dxf.handle,dn.dxf.handle));used_strokes.update(handles)
        records.append(dict(dn_text_handle=dn.dxf.handle,qualifier_handle=qualifier.dxf.handle,source_text=dn.plain_text(),source_qualifier=qualifier.plain_text(),nominal_mm=float(match[1]),
            component_type='flexible_joint',status='native_component_DN_annotation_not_pipe_scope',leader_handles=list(handles),native_leader_segments_wcs=segments,bindings=leaders,
            physical_parameter_verified=False,physical_length_mm=None,resistance_parameter=None,human_accepted=False))
    if not records:raise ValueError('explicit component label scope is empty')
    return dict(source_sha256=source_hash,graph_sha256=graph_hash,records=records,consumed_DN_text_handles=[r['dn_text_handle'] for r in records],consumed_leader_handles=sorted(used_strokes),
        graph_mutated=False,pipe_DN_inferred=False,human_accepted=False)
