"""Native paired end captions; joint assignment, never nearest-text DN transfer."""
import itertools,math
from decimal import Decimal,InvalidOperation
from compound_pipe_label_evidence import TOKEN
from calibrated_direct_dn_evidence import profile
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS

def level_key(value):
    if value is None:return None
    try:v=Decimal(value)
    except InvalidOperation:raise ValueError('invalid literal source level')
    if not v.is_finite():raise ValueError('nonfinite literal source level')
    return str(v.normalize())

def observe(doc):
    rows=[]
    for entity in doc.modelspace().query('TEXT'):
        if not supported(entity):continue
        text=entity.plain_text().strip();match=TOKEN.fullmatch(text)
        if not match or match[2]is None or float(match[1])<=0:continue
        rows.append(dict(handle=entity.dxf.handle,text=text,nominal_mm=float(match[1]),source_level_text=match[2],
            literal_level_key=level_key(match[2]),position=list(entity.dxf.insert)[:2],rotation=entity.dxf.rotation,profile=profile(doc,entity)))
    return rows

def candidates(doc,text,tolerance=.05):
    angle=math.radians(text['rotation']);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]]
    height=text['profile']['height'];p=text['position'];rows=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer not in LAYERS.values():continue
        a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2];length=math.dist(a,b)
        if length<=2*height or abs(axis[0]*(b[1]-a[1])-axis[1]*(b[0]-a[0]))/length>math.sin(math.radians(2)):continue
        stations=[sum((q[i]-p[i])*axis[i]for i in(0,1))for q in(a,b)]
        # End captions must be outside the actual native primitive. Interior
        # direct labels retain their original reader and calibration rules.
        if min(stations)>tolerance:side='before_start';gap=min(stations)
        elif max(stations)<-tolerance:side='after_end';gap=-max(stations)
        else:continue
        signed=sum((p[i]-a[i])*normal[i]for i in(0,1))
        if gap>3*height or abs(signed)>2*height or abs(signed)<=tolerance:continue
        rows.append(dict(source_LINE=line.dxf.handle,system=next(s for s,l in LAYERS.items()if l==line.dxf.layer),
            source_layer=line.dxf.layer,ends=[a,b],outside_along_line=gap,signed_normal=signed,end_side=side))
    return rows

def pair(doc,first,second,tolerance=.05):
    if first['profile']!=second['profile']or first['rotation']!=second['rotation']:raise ValueError('end caption profiles differ')
    angle=math.radians(first['rotation']);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]]
    delta=[second['position'][i]-first['position'][i]for i in(0,1)];height=first['profile']['height']
    separation=sum(delta[i]*normal[i]for i in(0,1))
    if abs(sum(delta[i]*axis[i]for i in(0,1)))>tolerance or not .1*height<abs(separation)<=3*height:raise ValueError('captions are not a paired end column')
    options=[candidates(doc,t,tolerance)for t in(first,second)];solutions=[]
    for a,b in itertools.product(*options):
        if a['source_LINE']==b['source_LINE']or {a['system'],b['system']}!={'supply','return'}or a['end_side']!=b['end_side']:continue
        # Two one-to-one captions preserve native pipe order and use the same
        # normal side. No nominal/level value participates in this geometry.
        if a['signed_normal']*b['signed_normal']<=0:continue
        pipe_separation=sum((b['ends'][0][i]-a['ends'][0][i])*normal[i]for i in(0,1))
        if pipe_separation*separation<=0:continue
        solutions.append((a,b))
    if len(solutions)!=1:raise ValueError('paired end caption geometry is not unique')
    return dict(status='unique_native_paired_end_caption_geometry',text_handles=[first['handle'],second['handle']],
        observations=[dict(text=t,native_pipe=c,all_geometric_candidates=all_rows)for t,c,all_rows in zip((first,second),solutions[0],options)],
        DN_or_level_used_to_choose_pipe=False,physical_level_or_units_inferred=False)

def collect(doc):
    texts=observe(doc);accepted=[];pending=[]
    for first,second in itertools.combinations(texts,2):
        if first['profile']!=second['profile']or first['rotation']!=second['rotation']:continue
        angle=math.radians(first['rotation']);axis=[math.cos(angle),math.sin(angle)]
        if abs(sum((second['position'][i]-first['position'][i])*axis[i]for i in(0,1)))>.05:continue
        if math.dist(first['position'],second['position'])>3*first['profile']['height']:continue
        try:accepted.append(pair(doc,first,second))
        except ValueError as exc:pending.append(dict(text_handles=[first['handle'],second['handle']],reason=str(exc)))
    counts={h:sum(h in r['text_handles']for r in accepted)for r in accepted for h in r['text_handles']}
    unique=[]
    for row in accepted:
        if any(counts[h]!=1 for h in row['text_handles']):pending.append(dict(text_handles=row['text_handles'],reason='caption participates in competing pairs'))
        else:unique.append(row)
    return dict(pairs=unique,pending=pending,graph_mutated=False,physical_pipe_membership_assigned=False)
