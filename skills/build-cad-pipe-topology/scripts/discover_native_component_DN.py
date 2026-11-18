"""Enumerate existing native component-DN reader inputs across a complete plan.

Candidate enumeration is not attribution. The inherited exact qualifier,
shared-hub leader, native ports, template and unique-owner checks make the
decision. Component DN is never emitted as pipe DN.
"""
import collections,math,re
from qualified_inline_DN_evidence import collect
from repair_native_flexible_joints import fingerprint


def discover(doc,graph,source_hash,graph_hash):
    texts=list(doc.modelspace().query('TEXT'));candidates=[];accepted=[];pending=[];used_text=set();used_strokes=set()
    blocks=sorted({r.get('source_block')for e in graph['edges']for r in e.get('source_flexible_joints',[])if r.get('source_block')})
    templates={}
    for name in blocks:
        if name in doc.blocks and sorted(e.dxftype()for e in doc.blocks[name])==['LINE','LINE','POINT','POINT','SPLINE']:
            templates[name]=fingerprint(doc.blocks[name])
    lines=list(doc.modelspace().query('LINE'))
    for qualifier in texts:
        if not qualifier.plain_text().startswith('金属软管'):continue
        q=list(qualifier.dxf.insert);height=float(qualifier.dxf.height);angle=math.radians(qualifier.dxf.rotation)
        axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]]
        nearby=[]
        for dn in texts:
            if not re.fullmatch(r'DN[1-9][0-9]*(?:\.[0-9]+)?',dn.plain_text()):continue
            if (dn.dxf.layer!=qualifier.dxf.layer or dn.dxf.style!=qualifier.dxf.style
                or abs(dn.dxf.height-height)>.01 or abs(dn.dxf.rotation-qualifier.dxf.rotation)>.001):continue
            p=list(dn.dxf.insert);delta=[q[i]-p[i]for i in (0,1)]
            if abs(sum(delta[i]*axis[i]for i in (0,1)))<=height and .5*height<sum(delta[i]*normal[i]for i in (0,1))<3*height:nearby.append(dn)
        for dn in nearby:
            p=list(dn.dxf.insert);specs=[];rejected=collections.Counter();candidates.append(dict(qualifier_handle=qualifier.dxf.handle,dn_handle=dn.dxf.handle))
            layer_lines=[e for e in lines if e.dxf.layer==dn.dxf.layer];hubs=[]
            for line in layer_lines:
                a,b=list(line.dxf.start),list(line.dxf.end);length=math.dist(a,b)
                if length<=height or abs(sum((b[i]-a[i])*normal[i]for i in (0,1)))>.05:continue
                direction=[(b[i]-a[i])/length for i in (0,1)]
                if (not all(0<sum((v[i]-a[i])*direction[i]for i in (0,1))<length for v in (p,q))
                    or not -.00001<sum((q[i]-a[i])*normal[i]for i in (0,1))<height
                    or not -2*height<sum((p[i]-a[i])*normal[i]for i in (0,1))<0):continue
                for point in (a,b):
                    if not any(math.dist(point,h)<=.00001 for h in hubs):hubs.append(point)
            for hub in hubs:
                star=[e for e in layer_lines if min(math.dist(list(e.dxf.start),hub),math.dist(list(e.dxf.end),hub))<=.00001]
                if len(star)<2:continue
                for name,signature in templates.items():
                    native=[]
                    for ins in doc.modelspace().query('INSERT'):
                        if ins.dxf.name==name:
                            ports=[list(e.dxf.location)for e in ins.virtual_entities()if e.dxftype()=='POINT']
                            native.append((ins.dxf.handle,ports))
                    handles=[]
                    for line in star:
                        a,b=list(line.dxf.start),list(line.dxf.end);leaf=b if math.dist(a,hub)<=.00001 else a
                        from component_DN_underline_end import contact_fraction
                        handles.extend(h for h,ports in native if contact_fraction(leaf,ports)is not None)
                    if not handles:continue
                    spec=dict(qualifier_handle=qualifier.dxf.handle,dn_handle=dn.dxf.handle,expected_text=dn.plain_text(),
                        leader_handles=[e.dxf.handle for e in star],expected_component_handles=sorted(set(handles)))
                    policy=dict(source_sha256=source_hash,graph_sha256=graph_hash,block_name=name,block_fingerprint_sha256=signature,labels=[spec])
                    try:proof=collect(doc,graph,policy,source_hash,graph_hash)
                    except ValueError as first:
                        from component_DN_underline_end import collect as either_end
                        try:proof=either_end(doc,graph,policy,source_hash,graph_hash)
                        except ValueError as exc:rejected[str(first)+'; '+str(exc)]+=1;continue
                    specs.append((policy,proof))
            if len(specs)!=1:
                pending.append(dict(qualifier_handle=qualifier.dxf.handle,dn_handle=dn.dxf.handle,reason='component_caption_without_unique_native_leader_port_and_owner_binding',verified_candidates=len(specs),rejected_candidates=dict(rejected)))
                continue
            policy,proof=specs[0]
            if dn.dxf.handle in used_text or used_strokes.intersection(proof['consumed_leader_handles']):raise ValueError('component DN discovered twice')
            used_text.add(dn.dxf.handle);used_strokes.update(proof['consumed_leader_handles']);accepted.append(dict(policy=policy,evidence=proof))
    return dict(status='native_component_DN_discovered_and_replayed_not_pipe_DN',records=accepted,pending=pending,
        candidate_component_DN_text_handles=sorted({c['dn_handle']for c in candidates}),
        consumed_DN_text_handles=sorted(used_text),consumed_leader_handles=sorted(used_strokes),
        source_sha256=source_hash,graph_sha256=graph_hash,pipe_DN_inferred=False,graph_mutated=False,human_accepted=False)
