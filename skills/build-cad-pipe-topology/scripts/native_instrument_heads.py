"""Complete native body/head/tap recognition without hydraulic capillary links."""
import math,re
from ezdxf import bbox
import pipe_geometry as pg
from equipment_assemblies import native_primitives
from native_proxy_evidence import block_fingerprint


def recognize(symbol,edges,doc,gauges,rules):
    rule=next((r for r in rules if r['block']==symbol['block']),None)
    if rule is None:return None
    entity=symbol.get('entity');result={'source_sensor_handle':symbol['handle'],'source_handles':[symbol['handle']],
        'status':'pending_native_head_or_tap','candidate_head_handles':[],'candidate_edge_ids':[],'edge_ids':[],'hydraulic_connection':False}
    if entity is None:return result
    if block_fingerprint(doc.blocks[entity.dxf.name])!=rule['fingerprint']:raise ValueError('Instrument native prototype changed')
    parts=native_primitives(entity)
    captions=[e.plain_text().strip()for e in parts if e.dxftype()in ('TEXT','MTEXT')]
    polys=[e for e in parts if e.dxftype()=='LWPOLYLINE'and e.closed and len(e)==4 and not any(abs(p[4])>1e-9 for p in e.get_points())]
    if captions!=[rule['body_caption']]or len(polys)!=1:raise ValueError('Instrument complete native body signature differs')
    poly=[pg.xy(p)for p in polys[0].vertices_in_wcs()];center=(sum(p[0]for p in poly)/4,sum(p[1]for p in poly)/4)
    diag=max(pg.dist(a,b)for a in poly for b in poly);tol=float(rule['contact_tolerance']);leaders=[]
    def outline(p):return min(pg.segdist(p,a,b)for a,b in zip(poly,poly[1:]+poly[:1]))
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer not in rule['leader_layers']:continue
        a,b=pg.xy(line.dxf.start),pg.xy(line.dxf.end);length=pg.dist(a,b)
        if not tol<length<=diag*float(rule['maximum_leader_body_diagonals']):continue
        for near,far in [(a,b),(b,a)]:
            if outline(near)<=tol and pg.dot(pg.sub(far,near),pg.sub(near,center))>0:
                leaders.append({'handle':line.dxf.handle,'near':near,'far':far,'axis':pg.sub(far,near)})
    heads=[]
    for leader in leaders:
        for gauge in gauges:
            if gauge['kind']not in rule['head_kinds']or gauge['entity'].dxf.layer not in rule['leader_layers']:continue
            c,r=gauge['center'],gauge['radius'];axis=leader['axis'];length=pg.dist(leader['near'],leader['far'])
            if pg.dist(leader['far'],c)>r+tol or abs(pg.cross(pg.sub(c,leader['near']),axis))/length>tol:continue
            if pg.dot(pg.sub(c,leader['near']),axis)<=0:continue
            heads.append((leader,gauge))
    result['candidate_head_handles']=sorted({q['entity'].dxf.handle for _,q in heads})
    if len(result['candidate_head_handles'])!=1:
        result['status']='pending_ambiguous_heads'if heads else'pending_no_proven_head';return result
    headleader,head=heads[0];taps=[]
    for leader in leaders:
        if leader['handle']==headleader['handle']:continue
        u,v=leader['axis'],headleader['axis'];lu,lv=math.hypot(*u),math.hypot(*v)
        if pg.dot(u,v)/(lu*lv)>-.999 or abs(pg.cross(u,v))/(lu*lv)>.001:continue
        owners=[]
        for edge in edges:
            for path in edge.get('attribute_paths',[edge['path_points']]):
                for a,b in zip(path,path[1:]):
                    if pg.segdist(leader['far'],a,b)>tol:continue
                    w=pg.sub(b,a);length=math.hypot(*w)
                    if length and abs(pg.dot(u,w))/(lu*length)<.01:owners.append(edge['edge_id']);break
                else:continue
                break
        if owners:taps.append((leader,sorted(set(owners))))
    if len(taps)!=1:
        result['status']='pending_no_unique_native_tap_leader';return result
    tapleader,ids=taps[0];result['candidate_edge_ids']=ids
    services={e['system']for e in edges if e['edge_id']in ids}
    if len(services)!=1 or next(iter(services))in ['unclassified_water','unresolved','pending']:
        result['status']='pending_tap_service_conflict';return result
    hs=set([symbol['handle'],headleader['handle'],tapleader['handle']]+head['handles']);tags=[]
    for text in doc.modelspace():
        if text.dxftype()not in ('TEXT','MTEXT')or text.dxf.layer!=head['entity'].dxf.layer:continue
        bb=bbox.extents([text],fast=True)
        if not bb.has_data:continue
        c=((bb.extmin.x+bb.extmax.x)/2,(bb.extmin.y+bb.extmax.y)/2)
        if pg.dist(c,head['center'])<=head['radius']*.9:
            hs.add(text.dxf.handle);value=text.plain_text().strip()
            if re.fullmatch(r'(CHWS|CHWR|CWS|CWR)-[A-Za-z0-9]+',value):tags.append(value)
    source_classes={rule.get('source_service_tags',{}).get(t.split('-')[0])for t in tags}-{None}
    result.update(status='complete_tagged_head',source_handles=sorted(hs),source_head_handle=head['entity'].dxf.handle,source_head_tag=head['tag'],
        leader_handles=[headleader['handle'],tapleader['handle']],source_service_tags=tags,edge_ids=ids,
        source_service_tag_conflict=bool(source_classes and source_classes!=services),tap_source_services=sorted(services),
        tap_point=list(tapleader['far']),body_axis=[headleader['near'],tapleader['near']],native_block_lead=False,
        rule='verified_native_body_opposed_source_leaders_unique_typed_head_and_exact_perpendicular_main_tap',label=rule['label'],type_code=rule['type_code'])
    return result
