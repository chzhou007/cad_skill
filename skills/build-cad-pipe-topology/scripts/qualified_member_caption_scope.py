"""Reapply an original whole-LINE guard with independently owned prefix captions.

Only a caption proved on a disjoint upstream member is excluded from the
downstream member's private annotation view. Source drawings remain untouched.
"""
import math,copy
from pipe_annotation_attributes import parse_dn_annotation
from native_line_path_evidence import _on,LAYERS
from riser_header_interval_application import member_dn_guard,CaptionOwnedProjection

def departure_guard(doc,approach,departure,captions,origin):
    before=approach['member']['nominal_mm'];after=departure['member']['nominal_mm']
    paths=approach['attribute_paths'];target=departure['attribute_paths']
    if (before==after or approach['system']!=departure['system']or len(paths)!=1 or len(paths[0])!=2
        or not target or math.dist(paths[0][-1],target[0][0])>.05):raise ValueError('distinct members sharing an already proved prefix boundary required')
    prior=member_dn_guard(doc,approach,captions,origin);common=set(approach['source_handles'])&set(departure['source_handles']);excluded=[]
    a,b=paths[0];size=math.dist(a,b)
    if size<=.05:raise ValueError('degenerate prefix member')
    for row in prior['other_native_DN_checks']:
        if row['source_LINE']not in common:continue
        if row['rule']!='unique_native_direct_annotation_crosscheck':continue
        ent=doc.entitydb.get(row['text_handle']);line=doc.entitydb.get(row['source_LINE'])
        if ent is None or ent.dxftype()!='TEXT'or line is None or line.dxftype()!='LINE'or line.dxf.layer!=LAYERS[approach['system']]:raise ValueError('qualified native prefix owner changed')
        parsed=parse_dn_annotation(ent.plain_text())
        if not parsed or parsed['nominal_mm']!=before:raise ValueError('prefix caption nominal differs')
        p=list(ent.ocs().to_wcs(ent.dxf.insert));t=sum((p[i]-a[i])*(b[i]-a[i])for i in(0,1))/(size*size);foot=[a[i]+t*(b[i]-a[i])for i in(0,1)]
        if not .05<t*size<size-.05:continue
        if any(_on(foot,x,y,.05)for path in target for x,y in zip(path,path[1:])):continue
        start,end=list(line.dxf.start),list(line.dxf.end)
        if not all(_on(q,start[:2],end[:2],.05)for q in [a,b])or abs(start[2]-end[2])>.05 or abs(p[2]-start[2])>.05:raise ValueError('prefix caption source XYZ differs')
        excluded.append(dict(text_handle=ent.dxf.handle,raw_text=ent.plain_text(),source_LINE=line.dxf.handle,source_text_WCS=p,projection_foot=foot,prefix_scope=copy.deepcopy(paths[0]),source_Z=start[2],original_native_owner=copy.deepcopy(row),caption_strictly_inside_prior_member=True,caption_outside_departure_paths=True))
    if len({r['text_handle']for r in excluded})!=len(excluded):raise ValueError('duplicate prefix caption exclusion')
    private=CaptionOwnedProjection(doc,{r['text_handle']for r in excluded})
    guarded=member_dn_guard(private,departure,captions,origin)
    return dict(qualified_prefix_guard=prior,independently_owned_outside_prefix_captions=excluded,departure_DN_guard=guarded,
        original_guard_reexecuted=True,original_thresholds_unchanged=True,F_and_other_new_DN_guards_retained=True,source_document_mutated=False)
