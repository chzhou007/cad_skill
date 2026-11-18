"""Unled native caption pairs with F-frame precedence and geometric ownership.

Values never choose a pipe. Nominal TEXT height defines conservative baseline
clearance, not a measured glyph box, physical level or flow direction.
"""
import itertools,math
from native_paired_end_labels import observe,pair as end_pair
from native_line_path_evidence import LAYERS,_on
from pipe_annotation_attributes import source_texts,recognize_f_leaders
from source_direct_dn_evidence import _projection
from calibrated_direct_dn_evidence import profile
from native_dn_text_position import supported

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def vector(a,b):return [b[i]-a[i] for i in (0,1)]

def leader_claims(doc,texts):
    """Reserve even pending/ambiguous F text; never bind a DN in this guard."""
    source=source_texts(doc,'source','');layers={t['layer'] for t in source if 'DN' in t['text'].upper()}
    frames=recognize_f_leaders(doc,source,[],[],layers);claimed={};strokes=[]
    for e in doc.modelspace():
        if e.dxf.layer not in layers:continue
        if e.dxftype()=='LINE':pairs=[(list(e.dxf.start)[:2],list(e.dxf.end)[:2])]
        elif e.dxftype()=='LWPOLYLINE' and not e.closed and not any(abs(p[4])>1e-9 for p in e.get_points()):
            points=[list(p)[:2] for p in e.vertices_in_wcs()];pairs=list(zip(points,points[1:]))
        else:continue
        strokes.extend(dict(handle=e.dxf.handle,layer=e.dxf.layer,a=a,b=b) for a,b in pairs if math.dist(a,b)>.05)
    def near(text,stroke):
        angle=math.radians(text['rotation']);axis=[math.cos(angle),math.sin(angle)];v=vector(stroke['a'],stroke['b']);length=math.hypot(*v)
        foot=_projection(text['position'],stroke['a'],stroke['b'])
        return (stroke['layer']==text['profile']['layer'] and abs(dot(axis,v)/length)>=math.cos(math.radians(2))
            and foot is not None and 0<foot[0]<1 and foot[1]<=2*text['profile']['height'])
    # Existing L/folded-frame recognition owns all near-bar candidates, including
    # cases where its unique text selection itself is pending.
    for frame in frames:
        parts=[s for s in strokes if s['handle'] in frame['leader_handles']]
        for text in texts:
            if any(near(text,s) for s in parts):claimed.setdefault(text['handle'],[]).append(dict(kind='native_polyline_F_frame',handles=frame['leader_handles'],status=frame['status']))
    # Exploded LINE F frames have the same ownership priority even when their
    # original ordered reader would decline a third crossing/text/bar.
    bars=[s for s in strokes if any(near(t,s) for t in texts)]
    for stem in strokes:
        v=vector(stem['a'],stem['b']);length=math.hypot(*v);groups=[[],[]]
        for bar in bars:
            if bar is stem or bar['layer']!=stem['layer'] or bar['handle']==stem['handle']:continue
            w=vector(bar['a'],bar['b']);size=math.hypot(*w)
            if abs(dot(v,w)/(length*size))>math.sin(math.radians(2)):continue
            contacts=[p for p in (bar['a'],bar['b']) if _on(p,stem['a'],stem['b'],.05)]
            if len(contacts)!=1:continue
            base=contacts[0];tip=bar['b'] if base==bar['a'] else bar['a'];direction=vector(base,tip)
            side=0 if v[0]*direction[1]-v[1]*direction[0]>0 else 1
            groups[side].append(bar)
        for group in groups:
            if len({s['handle'] for s in group})<2:continue
            for text in texts:
                if any(near(text,s) for s in group):claimed.setdefault(text['handle'],[]).append(dict(kind='native_exploded_F_frame_candidate',stem=stem['handle'],bars=sorted({s['handle'] for s in group})))
    return claimed

def interior_pair(doc,first,second,tolerance=.05):
    if first['profile']!=second['profile'] or first['rotation']!=second['rotation']:raise ValueError('paired interior caption profiles differ')
    angle=math.radians(first['rotation']);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]];height=first['profile']['height']
    rows=sorted((first,second),key=lambda t:dot(t['position'],normal));low,high=rows
    if abs(dot(vector(low['position'],high['position']),axis))>2*height:raise ValueError('paired interior captions do not share a local station')
    separation=dot(vector(low['position'],high['position']),normal)
    if not height<separation<=4*height:raise ValueError('interior caption normal separation is unsupported')
    pipes=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer not in LAYERS.values():continue
        a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2];v=vector(a,b);length=math.hypot(*v)
        if length<=2*height or abs(axis[0]*v[1]-axis[1]*v[0])/length>math.sin(math.radians(2)):continue
        stations=sorted(dot(p,axis) for p in (a,b))
        if not all(stations[0]+tolerance<dot(t['position'],axis)<stations[1]-tolerance for t in rows):continue
        signed=[dot(vector(a,t['position']),normal) for t in rows]
        pipes.append(dict(source_LINE=line.dxf.handle,source_layer=line.dxf.layer,system=next(s for s,l in LAYERS.items() if l==line.dxf.layer),ends=[a,b],signed_normals=signed))
    low_station,high_station=dot(low['position'],normal),dot(high['position'],normal)
    bounded=[p for p in pipes if low_station-tolerance<=dot(p['ends'][0],normal)<=high_station+tolerance]
    if len(bounded)!=2:raise ValueError('caption envelope contains other parallel pipes')
    solutions=[]
    for a,b in itertools.permutations(pipes,2):
        if a['system']==b['system']:continue
        # Lower caption below lower pipe by at least its nominal height; upper
        # caption above upper pipe. These inequalities fix order without DN.
        if not -2*height<=a['signed_normals'][0]<=-height-tolerance:continue
        if not tolerance<b['signed_normals'][1]<=2*height:continue
        pa,pb=dot(a['ends'][0],normal),dot(b['ends'][0],normal)
        if not pa+tolerance<pb:continue
        inside=[p for p in pipes if pa-tolerance<=dot(p['ends'][0],normal)<=pb+tolerance]
        if {p['source_LINE'] for p in inside}!={a['source_LINE'],b['source_LINE']}:continue
        solutions.append((a,b))
    if len(solutions)!=1:raise ValueError('paired interior source pipe assignment is not unique')
    return dict(status='unique_native_straddling_interior_caption_geometry',text_handles=[t['handle'] for t in rows],
        observations=[dict(text=t,native_pipe=p,all_geometric_candidates=pipes) for t,p in zip(rows,solutions[0])],
        DN_or_level_used_to_choose_pipe=False,physical_level_or_units_inferred=False)

def collect(doc):
    texts=observe(doc);guard_texts=[]
    for e in doc.modelspace().query('TEXT'):
        if supported(e) and 'DN' in e.plain_text().upper():guard_texts.append(dict(handle=e.dxf.handle,position=list(e.dxf.insert)[:2],rotation=e.dxf.rotation,profile=profile(doc,e)))
    claims=leader_claims(doc,guard_texts);accepted=[];pending=[]
    for first,second in itertools.combinations(texts,2):
        if first['profile']!=second['profile'] or first['rotation']!=second['rotation']:continue
        angle=math.radians(first['rotation']);axis=[math.cos(angle),math.sin(angle)]
        if abs(dot(vector(first['position'],second['position']),axis))>2*first['profile']['height']:continue
        if math.dist(first['position'],second['position'])>5*first['profile']['height']:continue
        handles=[first['handle'],second['handle']]
        if any(h in claims for h in handles):pending.append(dict(text_handles=handles,reason='native_F_leader_owns_text_even_if_ambiguous'));continue
        options=[]
        for reader in (end_pair,interior_pair):
            try:options.append(reader(doc,first,second))
            except ValueError:pass
        if len(options)==1:accepted.append(options[0])
        elif len(options)>1:pending.append(dict(text_handles=handles,reason='competing_end_and_interior_caption_families'))
    counts={h:sum(h in row['text_handles'] for row in accepted) for row in accepted for h in row['text_handles']};unique=[]
    for row in accepted:
        if any(counts[h]!=1 for h in row['text_handles']):pending.append(dict(text_handles=row['text_handles'],reason='caption participates in competing pairs'))
        else:unique.append(row)
    return dict(pairs=unique,pending=pending,F_owned_texts=claims,graph_mutated=False,physical_pipe_membership_assigned=False)
