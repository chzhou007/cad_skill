"""Batch discovery feeding the inherited strict caption/leader/frontier reader.

Discovery proposes native handles; the existing collector remains authoritative.
No nearest-endpoint inference, callout-quantity expansion or graph mutation.
"""
import math,re,copy
from native_capped_branch_annotations import collect,frontier_geometry,text_frame,xy,sub,dot,TOL

CAPTION=re.compile(r'预留支管接口[/／]共([1-9][0-9]*)处')

def qualifier_matches(caption,qualifier):
    p,u,v,h=text_frame(caption);q,qu,qv,qh=text_frame(qualifier)
    delta=sub(xy(q),xy(p));qx,qy=dot(delta,u),dot(delta,v)
    return (caption.dxf.layer==qualifier.dxf.layer and abs(qh/h-1)<=.01 and dot(u,qu)>=1-1e-8 and dot(v,qv)>=1-1e-8
        and abs(qx)<=.05*h and -2.5*h<=qy<=-.8*h)

def leader_paths(caption,qualifier,lines):
    p,u,v,h=text_frame(caption);q,_,_,_=text_frame(qualifier);qy=dot(sub(xy(q),xy(p)),v)
    def root(point):
        delta=sub(point,xy(p));a,b=dot(delta,u),dot(delta,v)
        return -.5*h<=a<=.05*h and qy<=b<=.05*h
    pending=[]
    for line in lines:
        a,b=xy(line.dxf.start),xy(line.dxf.end)
        for start,end in ((a,b),(b,a)):
            if root(start):pending.append((end,[line.dxf.handle]))
    paths=[]
    while pending:
        cursor,path=pending.pop();paths.append((cursor,path))
        if len(path)>=8:continue
        for line in lines:
            if line.dxf.handle in path:continue
            a,b=xy(line.dxf.start),xy(line.dxf.end)
            if math.dist(a,cursor)<=TOL:pending.append((b,path+[line.dxf.handle]))
            if math.dist(b,cursor)<=TOL:pending.append((a,path+[line.dxf.handle]))
    return paths

def discover(doc,graph,source_hash,graph_hash):
    if graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('capped discovery source identity differs')
    before=copy.deepcopy(graph);model=list(doc.modelspace())
    captions=sorted((e for e in model if e.dxftype()=='TEXT'and CAPTION.fullmatch(e.plain_text().strip())),key=lambda e:e.dxf.handle)
    qualifiers=[e for e in model if e.dxftype()=='TEXT'and e.plain_text().strip()=='盲板封堵']
    leaves=[n for n in graph['nodes']if n.get('node_type')=='virtual_equipment'and n.get('subtype')=='unresolved_source_terminal']
    lines=[e for e in model if e.dxftype()=='LINE'];selected=[];pending=[];rows=[]
    for caption in captions:
        handle=caption.dxf.handle;row=dict(caption_handle=handle,text=caption.plain_text().strip(),candidate_count=0)
        paired=[]
        for qualifier in qualifiers:
            try:matches=qualifier_matches(caption,qualifier)
            except(ValueError,TypeError):continue
            if matches:paired.append(qualifier)
        if len(paired)!=1:
            pending.append(dict(caption_handle=handle,reason='native_qualifier_missing_or_competing',candidate_qualifiers=[q.dxf.handle for q in paired]));rows.append(row);continue
        qualifier=paired[0];row['qualifier_handle']=qualifier.dxf.handle
        if not leaves:
            pending.append(dict(caption_handle=handle,reason='no_supported_unresolved_plan_frontier_existing_typed_ports_need_their_own_reader'));rows.append(row);continue
        layer_lines=[e for e in lines if e.dxf.layer==caption.dxf.layer];candidates={}
        for tip,path in leader_paths(caption,qualifier,layer_lines):
            outer=[bar for bar in layer_lines if bar.dxf.handle not in path and math.dist([(bar.dxf.start[i]+bar.dxf.end[i])/2 for i in (0,1)],tip)<=TOL]
            for short in outer:
                for node in leaves:
                    for pipe in node.get('source_handles',[]):
                        for long in layer_lines:
                            if long.dxf.handle==short.dxf.handle or long.dxf.handle in path:continue
                            try:frontier_geometry(doc,node,pipe,[long,short])
                            except(ValueError,KeyError,TypeError):continue
                            choice=dict(node_id=node['node_id'],pipe_handle=pipe,marker_handles=[long.dxf.handle,short.dxf.handle],
                                caption_handle=handle,qualifier_handle=qualifier.dxf.handle,leader_handles=path)
                            try:collect(doc,graph,source_hash,[choice])
                            except(ValueError,KeyError,TypeError):continue
                            key=(choice['node_id'],pipe,tuple(choice['marker_handles']),tuple(path));candidates[key]=choice
        row['candidate_count']=len(candidates)
        if len(candidates)==1:selected.append(next(iter(candidates.values())))
        else:pending.append(dict(caption_handle=handle,reason='native_complete_witness_missing_or_competing',candidates=list(candidates.values())))
        rows.append(row)
    conflicts={}
    for choice in selected:
        for key in [('node',choice['node_id'])]+[('marker',h)for h in choice['marker_handles']]:conflicts.setdefault(key,[]).append(choice)
    rejected={c['caption_handle']for uses in conflicts.values()if len(uses)>1 for c in uses}
    if rejected:pending.extend(dict(caption_handle=h,reason='caption_claims_compete_for_one_frontier_or_marker')for h in sorted(rejected))
    selected=[c for c in selected if c['caption_handle']not in rejected]
    inventory=collect(doc,graph,source_hash,selected)if selected else None
    if graph!=before:raise ValueError('annotation discovery changed local topology')
    return dict(mode='native_capped_annotation_discovery_v1',source_sha256=source_hash,graph_sha256=graph_hash,
        captions=rows,selections=selected,pending=pending,source_inventory=inventory,
        graph_mutated=False,physical_values_assigned=0,quantity_expanded_into_ports=False,human_accepted=False,hil_ready=False)
