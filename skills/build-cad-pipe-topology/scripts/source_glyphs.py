import pipe_geometry as pg_constants
"""Conservative exploded source glyphs. No ordinary terminal is promoted."""
from pipe_geometry import *

def exploded_flange_spans(segments,entities,layers):
    vs,ps,adj=build_network(segments)
    ends=[vs[v] for (sy,v),ids in adj.items() if sy=='physical' and len(ids)==1]
    lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer in layers]
    matches=[]
    for i,e in enumerate(lines):
        a,b=xy(e.dxf.start),xy(e.dxf.end);length=dist(a,b)
        if length<=pg_constants.TOL*10:continue
        p=((a[0]+b[0])/2,(a[1]+b[1])/2)
        if not any(dist(p,z)<=pg_constants.TOL for z in ends):continue
        for f in lines[i+1:]:
            if f.dxf.layer!=e.dxf.layer:continue
            c,d=xy(f.dxf.start),xy(f.dxf.end);q=((c[0]+d[0])/2,(c[1]+d[1])/2);axis=sub(q,p)
            if abs(dist(c,d)-length)>.02*length or not .1*length<=dist(p,q)<=.8*length:continue
            if abs(cross(sub(b,a),sub(d,c)))>.02*length*length or abs(dot(sub(b,a),axis))>pg_constants.TOL*length:continue
            if not any(dist(q,z)<=pg_constants.TOL for z in ends):continue
            tails=[[s for s in segments if min(dist(z,s['a']),dist(z,s['b']))<=pg_constants.TOL]for z in [p,q]]
            if not all(tails) or any(abs(cross(sub(s['b'],s['a']),axis))>pg_constants.TOL*dist(s['a'],s['b']) for ss in tails for s in ss):continue
            if not any(dot(sub(z,p),axis)<0 for s in tails[0]for z in [s['a'],s['b']]if dist(z,p)>pg_constants.TOL):continue
            if not any(dot(sub(z,q),axis)>0 for s in tails[1]for z in [s['a'],s['b']]if dist(z,q)>pg_constants.TOL):continue
            matches.append((p,q,[e.dxf.handle,f.dxf.handle]))
    bridges=[];audit=[]
    for p,q,handles in matches:
        if sum(any(dist(z,t)<=pg_constants.TOL for z in [p,q]for t in [r,s])for r,s,h in matches)!=1:continue
        bridges.append(dict(a=p,b=q,system='physical',source_system='unclassified_water',handle='FLANGES-'+handles[0],source_handles=handles,normalization='exploded_parallel_flanges_opposed_source_pipe_terminals'))
        audit.append(dict(a=p,b=q,source_handles=handles,status='recovered',rule='two_equal_parallel_flanges_with_midpoint_contacts_and_opposed_collinear_source_pipes',semantic_class='unclassified_inline_source_glyph'))
    return bridges,audit

def source_cup_terminals(entities,vertices,pieces,adj,rules):
    """Identify a full U-and-short-bar source terminal, independently of flow direction."""
    found=[];audit=[]
    for rule in rules:
        lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer in rule['symbol_layers']]
        candidates={}
        for bar in lines:
            a,b=xy(bar.dxf.start),xy(bar.dxf.end);w=dist(a,b)
            if w<=pg_constants.TOL*10:continue
            ux,uy=(b[0]-a[0])/w,(b[1]-a[1])/w
            def local(p):v=sub(p,a);return(dot(v,(ux,uy)),cross((ux,uy),v))
            for sign in [-1,1]:
                walls=[];short=[]
                for e in lines:
                    if e is bar:continue
                    c,d=local(xy(e.dxf.start)),local(xy(e.dxf.end))
                    lo,hi=sorted([c,d],key=lambda p:p[1]*sign)
                    if abs(c[0]-d[0])<=.03*w and abs(lo[1])<=.06*w and .25*w<=hi[1]*sign<=.75*w:
                        mid=(c[0]+d[0])/2
                        if min(abs(mid),abs(mid-w))<=.06*w:walls.append((mid,e))
                    if abs(c[1]-d[1])<=.03*w and -.4*w<=(c[1]+d[1])*sign/2<=-.15*w and .5*w<=abs(c[0]-d[0])<=.85*w and abs((c[0]+d[0])/2-w/2)<=.08*w:short.append(e)
                left=[e for x,e in walls if abs(x)<=.06*w];right=[e for x,e in walls if abs(x-w)<=.06*w]
                if len(left)!=1 or len(right)!=1 or len(short)!=1:continue
                handles=sorted({bar.dxf.handle,left[0].dxf.handle,right[0].dxf.handle,short[0].dxf.handle})
                for v,p in enumerate(vertices):
                    ids=adj.get(('physical',v),[])
                    if len(ids)!=1:continue
                    x,y=local(p)
                    if abs(x-w/2)>.08*w or not 0<y*sign<=.35*w:continue
                    if rule.get('pipe_layers') and not any(e.dxf.handle in pieces[ids[0]]['source_handles'] and e.dxf.layer in rule['pipe_layers'] for e in entities):continue
                    other=vertices[next(k for k in pieces[ids[0]]['vertices']if k!=v)];ox,oy=local(other)
                    if abs(ox-x)>.08*w or oy*sign<=y*sign:continue
                    evidence={'source_note_handle':bar.dxf.handle,'source_symbol_handles':handles,'source_note':'Full native cup and lower bar terminal signature; terminal function and flow direction are not inferred.','status':'source_marked_terminal_semantics_pending','rule':'complete_cup_two_walls_short_bar_and_centered_source_pipe_end','system':rule['system']}
                    candidates[v]={'vertex':v,'system':rule['system'],'label':rule.get('label','Source-marked Terminal'),'evidence':evidence}
        found+=list(candidates.values());audit += [c['evidence']for c in candidates.values()]
    return found,audit
