"""Read native floor/elevation glyphs without assigning pipe lengths or units."""
import math,re
from pipe_annotation_attributes import source_texts

MODE='native_axis_floor_elevation_text_evidence_v1'

def number(text):
    match=re.fullmatch(r'\s*([+\-±]?)(\d+\.\d{3})\s*',text)
    if not match:return None
    value=float(match[2])*(-1 if match[1]=='-'else 1)
    return None if match[1]=='±'and value!=0 else value

def collect(doc,source_hash,tol=.05):
    texts=source_texts(doc,'axis',source_hash)
    if any('\ufffd'in t['text']for t in texts):raise ValueError('unreadable source annotation')
    floors=[t for t in texts if re.fullmatch(r'(?:[1-9]\d*F|[一二三四五六七八九十]+层)',t['text'])]
    values=[t for t in texts if number(t['text'])is not None]
    lines=list(doc.modelspace().query('LINE'));diagonal=[];records=[];pending=[];seen=set()
    for line in lines:
        a,b=list(line.dxf.start),list(line.dxf.end);dx,dy=b[0]-a[0],b[1]-a[1]
        if min(abs(dx),abs(dy))>tol and abs(abs(dx)-abs(dy))<=tol and abs(a[2]-b[2])<=tol:diagonal.append((line,a,b))
    for i,(left,a,b)in enumerate(diagonal):
        for right,c,d in diagonal[i+1:]:
            if left.dxf.layer!=right.dxf.layer:continue
            for tip,outer,tip2,outer2 in[(a,b,c,d),(a,b,d,c),(b,a,c,d),(b,a,d,c)]:
                if math.dist(tip,tip2)>tol or abs(outer[1]-outer2[1])>tol or abs(abs(outer[0]-tip[0])-abs(outer2[0]-tip[0]))>tol or (outer[0]-tip[0])*(outer2[0]-tip[0])>=0:continue
                arms={left.dxf.handle,right.dxf.handle};candidates=[]
                for bar in lines:
                    if bar.dxf.handle in arms or bar.dxf.layer!=left.dxf.layer:continue
                    u,v=list(bar.dxf.start),list(bar.dxf.end)
                    if abs(u[1]-v[1])>tol or abs(u[2]-tip[2])>tol or abs(v[2]-tip[2])>tol:continue
                    if min(math.dist(p,q)for p in(u,v)for q in(outer,outer2))>tol:continue
                    width=abs(u[0]-v[0]);arm=abs(outer[0]-tip[0])
                    if width<3*arm:continue
                    x0,x1=sorted([u[0],v[0]]);y=u[1]
                    numeric=[t for t in values if t['layer']==bar.dxf.layer and abs(t['rotation'])<.01 and x0-.5*t['height']<=t['position'][0]<=x1+.5*t['height']and 0<=t['position'][1]-y<=2*t['height']]
                    labels=[t for t in floors if t['layer']==bar.dxf.layer and abs(t['rotation'])<.01 and abs(t['position'][0]-tip[0])<=4*width and 0<=t['position'][1]-y<=2*t['height']]
                    baselines=[l for l in lines if l.dxf.handle not in arms|{bar.dxf.handle}and abs(l.dxf.start.y-tip[1])<=tol and abs(l.dxf.end.y-tip[1])<=tol and abs(l.dxf.start.z-tip[2])<=tol and abs(l.dxf.end.z-tip[2])<=tol and min(l.dxf.start.x,l.dxf.end.x)<tip[0]<max(l.dxf.start.x,l.dxf.end.x)and abs(l.dxf.end.x-l.dxf.start.x)>=3*width]
                    if not numeric and not labels:continue
                    candidates.append((bar,numeric,labels,baselines))
                key=tuple(sorted(arms))
                if key in seen or not candidates:continue
                seen.add(key)
                if len(candidates)!=1 or any(len(x)!=1 for x in candidates[0][1:]):
                    pending.append(dict(arm_handles=list(key),reason='floor_elevation_text_bar_or_baseline_not_unique'));continue
                bar,nums,labels,bases=candidates[0];numeric,label=nums[0],labels[0]
                if abs(numeric['position'][1]-label['position'][1])>max(numeric['height'],label['height']):
                    pending.append(dict(arm_handles=list(key),reason='floor_and_elevation_text_rows_differ'));continue
                records.append(dict(floor_text=label,source_elevation_text=numeric,elevation_source_value=number(numeric['text']),unit_status='source_elevation_unit_not_selected',
                    native_elevation_symbol=dict(arm_handles=list(key),bar_handle=bar.dxf.handle,baseline_handle=bases[0].dxf.handle,tip_WCS=tip),
                    pipe_endpoint_binding=None,physical_pipe_length_mm=None,human_accepted=False))
    return dict(mode=MODE,source_sha256=source_hash,records=sorted(records,key=lambda r:r['native_elevation_symbol']['tip_WCS'][1]),pending=pending,
        native_DIMENSION_count=len(doc.modelspace().query('DIMENSION')),floor_level_is_not_pipe_center_height=True,modelspace_TEXT_and_LINE_only=True,
        physical_lengths_assigned=0,graph_mutated=False,human_accepted=False)
