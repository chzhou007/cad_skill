"""Native component DN whose fan leader joins either end of its underline.

Extends label placement and accepts a pointed position on the native two-port
axis. This attributes a component label, never a new physical pipe contact.
"""
import math,re
from native_dn_text_position import supported
from repair_native_flexible_joints import fingerprint


def contact_fraction(point,ports,tol=.00001):
    if len(ports)!=2:return None
    a,b=ports;delta=[b[i]-a[i]for i in range(3)];den=sum(x*x for x in delta)
    if den<=tol*tol:return None
    fraction=sum((point[i]-a[i])*delta[i]for i in range(3))/den
    if not 0<=fraction<=1:return None
    foot=[a[i]+fraction*delta[i]for i in range(3)]
    return fraction if math.dist(point,foot)<=tol else None


def collect(doc,graph,policy,source_hash,graph_hash):
    if (policy['source_sha256']!=source_hash or policy['graph_sha256']!=graph_hash
        or graph.get('metadata',{}).get('source_sha256')!=source_hash):raise ValueError('component caption source differs')
    block=policy['block_name']
    if block not in doc.blocks or fingerprint(doc.blocks[block])!=policy['block_fingerprint_sha256']:
        raise ValueError('component caption template differs')
    if sorted(e.dxftype()for e in doc.blocks[block])!=['LINE','LINE','POINT','POINT','SPLINE']:raise ValueError('unsupported flexible-joint template')
    native=[]
    for ins in doc.modelspace().query('INSERT'):
        if ins.dxf.name==block:
            pts=[list(e.dxf.location)for e in ins.virtual_entities()if e.dxftype()=='POINT']
            if len(pts)!=2:raise ValueError('native joint ports unavailable')
            native.append((ins,pts))
    owners={}
    for edge in graph['edges']:
        for item in edge.get('source_flexible_joints',[]):
            h=item['source_handle'];names=[n for n in edge.get('equipment_names',[])if n.endswith('-'+h)]
            if h in owners or len(names)!=1 or edge.get('equipment_counts',{}).get('flexible_joint',0)<1:raise ValueError('component canonical owner differs')
            owners[h]=(edge,item,names[0])
    records=[];texts=set();strokes=set();components=set()
    for spec in policy['labels']:
        q=doc.entitydb.get(spec['qualifier_handle']);dn=doc.entitydb.get(spec['dn_handle'])
        if (q is None or dn is None or q not in doc.modelspace()or dn not in doc.modelspace()
            or q.dxftype()!='TEXT'or dn.dxftype()!='TEXT'or not supported(q)or not supported(dn)
            or not re.fullmatch('金属软管(?:/余同)?',q.plain_text())or dn.plain_text()!=spec['expected_text']):raise ValueError('component caption qualifier differs')
        match=re.fullmatch(r'DN([1-9][0-9]*(?:\.[0-9]+)?)',dn.plain_text())
        if (not match or q.dxf.layer!=dn.dxf.layer or q.dxf.style!=dn.dxf.style or abs(q.dxf.height-dn.dxf.height)>.01
            or abs(q.dxf.rotation-dn.dxf.rotation)>.001):raise ValueError('component caption text pose differs')
        angle=math.radians(dn.dxf.rotation);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]];height=dn.dxf.height
        qp,dp=list(q.dxf.insert),list(dn.dxf.insert);delta=[qp[i]-dp[i]for i in (0,1)]
        if abs(sum(delta[i]*axis[i]for i in (0,1)))>height or not .5*height<sum(delta[i]*normal[i]for i in (0,1))<3*height:raise ValueError('component caption rows differ')
        handles=spec['leader_handles'];segments=[]
        if len(handles)<2 or len(handles)!=len(set(handles))or strokes.intersection(handles):raise ValueError('component leader scope repeated')
        for h in handles:
            line=doc.entitydb.get(h)
            if line is None or line not in doc.modelspace()or line.dxftype()!='LINE'or line.dxf.layer!=dn.dxf.layer:raise ValueError('native component leader differs')
            segments.append((h,list(line.dxf.start),list(line.dxf.end)))
        hub_candidates=[]
        for _,a,b in segments:
            for p in (a,b):
                if all(min(math.dist(p,c),math.dist(p,d))<=.00001 for _,c,d in segments)and not any(math.dist(p,v)<=.00001 for v in hub_candidates):hub_candidates.append(p)
        if len(hub_candidates)!=1:raise ValueError('component leaders lack one shared native hub')
        hub=hub_candidates[0];underlines=[];bindings=[]
        for handle,a,b in segments:
            leaf=b if math.dist(a,hub)<=.00001 else a;length=math.dist(leaf,hub)
            parallel=abs(sum((leaf[i]-hub[i])*normal[i]for i in (0,1)))<=.05
            if parallel and length>height:
                u=[(leaf[i]-hub[i])/length for i in (0,1)]
                if all(0<sum((p[i]-hub[i])*u[i]for i in (0,1))<length for p in (qp,dp)):
                    qn=sum((qp[i]-hub[i])*normal[i]for i in (0,1));pn=sum((dp[i]-hub[i])*normal[i]for i in (0,1))
                    if -.00001<qn<height and -2*height<pn<0:underlines.append(handle);continue
            hits=[(ins,pts,contact_fraction(leaf,pts))for ins,pts in native if contact_fraction(leaf,pts)is not None]
            if len(hits)!=1:raise ValueError('component leader does not identify one native two-port component axis')
            ins,pts,fraction=hits[0];h=ins.dxf.handle
            if h not in owners or h in components:raise ValueError('pointed component has no unique current owner')
            edge,item,name=owners[h]
            if (item.get('source_block')!=block or item.get('physical_length')!='unknown'or item.get('parameter_status')!='unknown_not_zero'
                or sorted(map(tuple,item.get('source_contact_points',[])))!=sorted(tuple(p[:2])for p in pts)):
                raise ValueError('component contacts or unknown parameter semantics differ')
            components.add(h);bindings.append(dict(leader_handle=handle,source_handle=h,device_name=name,edge_id=edge['edge_id'],system=edge['system'],
                native_contact_wcs=leaf,native_joint_contacts_wcs=pts,native_axis_fraction=fraction,
                annotation_target_kind='native_port'if fraction in (0,1)else'native_component_axis_interior',physical_port_verified=False))
        if len(underlines)!=1 or len(bindings)!=len(handles)-1 or {r['source_handle']for r in bindings}!=set(spec['expected_component_handles']):raise ValueError('component fan population differs')
        if q.dxf.handle in texts or dn.dxf.handle in texts:raise ValueError('component caption repeated')
        texts.update((q.dxf.handle,dn.dxf.handle));strokes.update(handles)
        records.append(dict(dn_text_handle=dn.dxf.handle,qualifier_handle=q.dxf.handle,source_text=dn.plain_text(),source_qualifier=q.plain_text(),nominal_mm=float(match[1]),
            component_type='flexible_joint',status='native_component_DN_annotation_not_pipe_scope',leader_handles=list(handles),bindings=bindings,native_hub=hub,
            physical_parameter_verified=False,physical_length_mm=None,resistance_parameter=None,unpointed_same_symbols_inferred=False,human_accepted=False))
    if not records:raise ValueError('component caption selection empty')
    return dict(source_sha256=source_hash,graph_sha256=graph_hash,records=records,consumed_DN_text_handles=[r['dn_text_handle']for r in records],
        consumed_leader_handles=sorted(strokes),graph_mutated=False,pipe_DN_inferred=False,human_accepted=False)
