"""Source-bound exploded-LINE F labels: ordered attributes, never connectivity."""
import argparse,json,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from pipe_annotation_attributes import parse_dn_annotation,contact
from native_line_path_evidence import LAYERS,_on
from source_direct_dn_evidence import _projection
from source_readability import read_source

def text_pose(entity):
    if entity.dxftype()!='TEXT':raise ValueError('F label must be native TEXT')
    d=entity.dxf;normal=d.get('extrusion',(0,0,1));height=float(d.height);angle=math.radians(d.get('rotation',0));width=float(d.get('width',1))
    if (abs(normal[0])>1e-9 or abs(normal[1])>1e-9 or abs(abs(normal[2])-1)>1e-9
        or d.get('halign',0) or d.get('valign',0) or abs(d.get('oblique',0))>1e-9 or d.get('text_generation_flag',0) not in (0,2,4,6)
        or d.get('invisible',0) or height<=0 or width<=0):raise ValueError('unsupported F text transform')
    point=entity.ocs().to_wcs(d.insert);axis=entity.ocs().to_wcs((math.cos(angle),math.sin(angle),0))
    if not all(math.isfinite(v) for v in (*point,*axis,height,width)):raise ValueError('nonfinite F text')
    text=entity.plain_text();parsed=parse_dn_annotation(text)
    if parsed is None or '\ufffd' in text:raise ValueError('unsupported or unreadable F DN text')
    return dict(handle=d.handle,text=text,position=list(point),axis=list(axis)[:2],height=height,layer=d.layer,entity_type='TEXT',**parsed)

def collect(doc,graph,frames,source_hash,graph_hash):
    if not frames:raise ValueError('explicit exploded F scope required')
    edges=graph['edges'];reverse={v:k for k,v in LAYERS.items()};records=[];claimed=set()
    for spec in frames:
        handles=[spec['stem_handle']]+spec['bar_handles']+spec['text_handles']
        if len(spec['bar_handles'])!=2 or len(spec['text_handles'])!=2 or len(handles)!=len(set(handles)) or claimed.intersection(handles):raise ValueError('invalid or duplicate F frame selections')
        claimed.update(handles);entities=[doc.entitydb.get(h) for h in handles]
        if any(e is None or e not in doc.modelspace() for e in entities) or [e.dxftype() for e in entities[:3]]!=['LINE']*3:raise ValueError('F strokes must be native modelspace LINE')
        stem=entities[0];a=list(stem.dxf.start);b=list(stem.dxf.end);length=math.dist(a[:2],b[:2])
        if length<=.05 or abs(a[2]-b[2])>.05:raise ValueError('invalid 2D F stem')
        axis=[(b[i]-a[i])/length for i in (0,1)];bars=[]
        for entity in entities[1:3]:
            p,q=list(entity.dxf.start),list(entity.dxf.end)
            if abs(p[2]-a[2])>.05 or abs(q[2]-a[2])>.05:raise ValueError('F source stroke Z differs')
            contacts=[r for r in (p,q) if _on(r[:2],a[:2],b[:2],.05)]
            if len(contacts)!=1:raise ValueError('F bar must meet the stem at one endpoint')
            base=contacts[0];tip=q if base==p else p;size=math.dist(base[:2],tip[:2])
            if size<=.05:raise ValueError('zero F bar')
            direction=[(tip[i]-base[i])/size for i in (0,1)]
            if abs(sum(x*y for x,y in zip(direction,axis)))>math.sin(math.radians(2)):raise ValueError('F bar not perpendicular')
            bars.append(dict(handle=entity.dxf.handle,base=base,tip=tip,direction=direction,stem_station=sum((base[i]-a[i])*axis[i] for i in (0,1))))
        if sum(x*y for x,y in zip(bars[0]['direction'],bars[1]['direction']))<math.cos(math.radians(2)) or abs(bars[0]['stem_station']-bars[1]['stem_station'])<=.05:raise ValueError('F bars must be distinct and point to the same side')
        texts=[text_pose(e) for e in entities[3:]];used=set()
        if any(t['layer']!=stem.dxf.layer for t in texts) or any(e.dxf.layer!=stem.dxf.layer for e in entities[1:3]):raise ValueError('F strokes/text layers differ')
        for entity in doc.modelspace().query('LINE'):
            if entity.dxf.handle in handles or entity.dxf.layer!=stem.dxf.layer:continue
            p,q=list(entity.dxf.start)[:2],list(entity.dxf.end)[:2];base=[r for r in (p,q) if _on(r,a[:2],b[:2],.05)]
            if len(base)==1:
                tip=q if base[0]==p else p;size=math.dist(base[0],tip)
                if size>.05 and abs(sum((tip[i]-base[0][i])*axis[i]/size for i in (0,1)))<=math.sin(math.radians(2)):raise ValueError('unselected third F bar competes with the two-bar frame')
        for text in texts:
            if abs(text['position'][2]-a[2])>.05:raise ValueError('F label source Z differs')
            matches=[]
            for bar in bars:
                if abs(sum(x*y for x,y in zip(text['axis'],bar['direction'])))<math.cos(math.radians(2)):continue
                foot=_projection(text['position'][:2],bar['base'][:2],bar['tip'][:2])
                if foot and 0<foot[0]<1 and foot[1]<=2*text['height']:matches.append((foot[1],bar['handle']))
            matches.sort()
            if not matches or len(matches)>1 and matches[1][0]-matches[0][0]<=.5*text['height'] or matches[0][1] in used:raise ValueError('F text-to-bar assignment ambiguous')
            chosen=next(bar for bar in bars if bar['handle']==matches[0][1]);chosen['source_text']=text;used.add(chosen['handle'])
        for entity in doc.modelspace().query('TEXT'):
            if entity.dxf.handle in spec['text_handles'] or entity.dxf.layer!=stem.dxf.layer or parse_dn_annotation(entity.plain_text()) is None:continue
            text=text_pose(entity)
            if any(abs(sum(x*y for x,y in zip(text['axis'],bar['direction'])))>=math.cos(math.radians(2)) and (foot:=_projection(text['position'][:2],bar['base'][:2],bar['tip'][:2])) and 0<foot[0]<1 and foot[1]<=2*text['height'] for bar in bars):raise ValueError('unselected DN text competes for an F bar')
        pipes=[]
        for line in doc.modelspace().query('LINE'):
            p,q=list(line.dxf.start),list(line.dxf.end);point=contact(a[:2],b[:2],p[:2],q[:2])
            if point is None:continue
            if line.dxf.layer not in reverse:
                if any(line.dxf.handle in e.get('source_handles',[]) for e in edges):raise ValueError('F stem crosses an unclassified graph pipe')
                continue
            if abs(p[2]-q[2])>.05 or abs(p[2]-a[2])>.05:raise ValueError('F target pipe source Z differs')
            owners=[e for e in edges if e.get('system')==reverse[line.dxf.layer] and line.dxf.handle in e.get('source_handles',[]) and any(_on(point,u,v,.05) for path in e.get('attribute_paths',[]) for u,v in zip(path,path[1:]))]
            if len(owners)!=1:raise ValueError('F pipe contact has no unique current graph owner')
            pipes.append(dict(source_line_handle=line.dxf.handle,edge_id=owners[0]['edge_id'],system=reverse[line.dxf.layer],point=list(point),stem_station=sum((point[i]-a[i])*axis[i] for i in (0,1))))
        if len(pipes)!=2 or math.dist(pipes[0]['point'],pipes[1]['point'])<=.05:raise ValueError('F stem must cross exactly two distinct source pipes')
        bars.sort(key=lambda r:r['stem_station']);pipes.sort(key=lambda r:r['stem_station'])
        if not (pipes[-1]['stem_station']<bars[0]['stem_station']-.05 or bars[-1]['stem_station']<pipes[0]['stem_station']-.05):raise ValueError('F pipe contacts and label bars interleave')
        bindings=[]
        for index,(bar,pipe) in enumerate(zip(bars,pipes),1):
            text=bar['source_text'];bindings.append(dict(order=index,edge_id=pipe['edge_id'],system=pipe['system'],nominal_mm=text['nominal_mm'],
                parenthesized_source_value=text['parenthesized_source_value'],source_text=text,bar_handle=bar['handle'],source_line_handle=pipe['source_line_handle'],graph_projection=pipe['point'],
                status='ordered_native_LINE_F_annotation',physical_length_from_parentheses=False))
        records.append(dict(stem_handle=stem.dxf.handle,stroke_handles=[e.dxf.handle for e in entities[:3]],text_handles=spec['text_handles'],
            native_stem=[a,b],bars=bars,pipe_contacts=pipes,bindings=bindings,order_rule='same_stem_order_for_label_bars_and_pipe_contacts_in_WCS',graph_mutated=False,human_accepted=False))
    return dict(status='source_checked_exploded_LINE_F_annotation_not_connectivity',source_sha256=source_hash,graph_sha256=graph_hash,frames=records,
        graph_mutated=False,pipe_systems_connected=False,human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();policy=load(args.policy)
    if sha(args.source)!=policy['source_sha256'] or sha(args.graph)!=policy['graph_sha256']:raise ValueError('stale F input')
    doc,preflight=read_source(args.source);result=collect(doc,load(args.graph),policy['frames'],sha(args.source),sha(args.graph));result.update(source_preflight=preflight,policy_sha256=sha(args.policy),implementation_sha256=sha(Path(__file__)))
    with args.output.open('xb') as f:f.write(encode(result))
    print(json.dumps(dict(frames=len(result['frames']),bindings=sum(len(r['bindings']) for r in result['frames']),human_accepted=False)))

if __name__=='__main__':main()
