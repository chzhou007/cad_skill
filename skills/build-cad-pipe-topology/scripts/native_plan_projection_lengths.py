"""Measure only source-witnessed floor-plan projections in corroborated mm.

Native dimensions corroborate drawing units, never become a pipe length merely
by proximity. Installed vertical drops and equipment connectors stay unknown.
"""
import math,re

def unit_evidence(doc,policy):
    if doc.header.get('$INSUNITS')!=4 or policy.get('view_kind')!='floor_plan':raise ValueError('millimetre floor-plan source required')
    box=policy.get('plan_window');title=doc.entitydb.get(policy.get('floor_title_handle',''))
    if (not isinstance(box,list) or len(box)!=4 or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in box)
        or not box[0]<box[1] or not box[2]<box[3]):raise ValueError('explicit plan scope required')
    inside=lambda p:box[0]<=p[0]<=box[1] and box[2]<=p[1]<=box[3]
    if not title or title not in doc.modelspace() or title.dxftype() not in ('TEXT','MTEXT') or title.plain_text()!=policy.get('floor_title') or not inside(title.dxf.insert):raise ValueError('native floor title differs')
    specs=policy.get('unit_dimensions',[])
    if len(specs)<2 or len({x['handle'] for x in specs})!=len(specs):raise ValueError('two distinct native unit dimensions required')
    rows=[];axes=[]
    for spec in specs:
        dim=doc.entitydb.get(spec['handle'])
        if (not dim or dim not in doc.modelspace() or dim.dxftype()!='DIMENSION' or dim.dxf.dimtype&7!=0
            or tuple(dim.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or dim.dxf.get('text','') not in ('','<>')):raise ValueError('unsupported unit dimension or manual text override')
        p,q=dim.dxf.get('defpoint2'),dim.dxf.get('defpoint3')
        if p is None or q is None or not inside(p) or not inside(q):raise ValueError('unit dimension outside plan scope')
        style=doc.dimstyles.get(dim.dxf.dimstyle);overrides=dim.get_acad_dstyle(style)
        factor=overrides.get('dimlfac',style.dxf.get('dimlfac',1.))
        if factor is None:factor=1.
        if isinstance(factor,bool) or not isinstance(factor,(int,float)) or not math.isfinite(factor) or abs(factor-1)>1e-9:raise ValueError('dimension factor does not corroborate mm')
        angle=math.radians(dim.dxf.get('angle',0));axis=[math.cos(angle),math.sin(angle)]
        projected=abs((q.x-p.x)*axis[0]+(q.y-p.y)*axis[1]);measured=float(dim.get_measurement())
        texts=[t for t in doc.blocks[dim.dxf.geometry] if t.dxftype() in ('TEXT','MTEXT')]
        display=[t for t in dim.virtual_entities() if t.dxftype() in ('TEXT','MTEXT')]
        if (len(texts)!=1 or len(display)!=1 or texts[0].dxf.handle!=spec['text_handle'] or texts[0].plain_text()!=spec['text'] or display[0].plain_text()!=spec['text']
            or not re.fullmatch(r'\d+(?:\.\d+)?',spec['text'])):raise ValueError('unit dimension native display changed')
        expected=float(spec['text'])
        if not all(math.isfinite(v) and v>0 for v in (projected,measured,expected)) or max(abs(projected-expected),abs(measured-expected))>.05:raise ValueError('unit dimension projection or value differs')
        axes.append(axis);rows.append(dict(handle=dim.dxf.handle,text_handle=texts[0].dxf.handle,text=spec['text'],projected_mm=projected,
            native_definition_points=[list(p),list(q)],angle_degrees=dim.dxf.get('angle',0),effective_dimlfac=factor))
    if not any(abs(a[0]*b[1]-a[1]*b[0])>.5 for a in axes for b in axes):raise ValueError('independent dimension directions required')
    return dict(status='native_mm_units_corroborated_not_pipe_dimension_assignment',source_units='mm',insunits=4,
        floor_title_handle=title.dxf.handle,floor_title=title.plain_text(),plan_window=box,unit_dimensions=rows)

def lengths(graph,coverage,record,units):
    edges={e['edge_id']:e for e in graph['edges']};audits={e['edge_id']:e for e in coverage['edges']}
    pieces=[];box=units['plan_window']
    for eid in record['plan_edges']:
        edge=edges[eid];audit=audits[eid]
        if edge.get('source_view_context') is not None:
            raise ValueError('source view drawing span needs separately verified floor-plan metric evidence; global units or a detail-view flag are insufficient')
        if edge['system']!=record['system'] or audit['system']!=record['system'] or not audit['segments']:raise ValueError('plan length service or scope differs')
        separate=len(edge['attribute_paths'])!=1
        if separate and (audit.get('coverage_mode')!='native_plan_paths_excluding_replayed_crossovers'
            or audit.get('source_path_evidence',{}).get('status')!='native_source_paths_and_excluded_crossovers_replayed'
            or len(audit.get('source_path_evidence',{}).get('crossovers',[]))!=len(edge['attribute_paths'])-1):raise ValueError('omitted or separate plan paths require their own length scope')
        for segment in audit['segments']:
            idx=segment['index'];pi=segment.get('path_index',0)
            if isinstance(pi,bool) or not isinstance(pi,int) or not 0<=pi<len(edge['attribute_paths']):raise ValueError('plan path projection index differs')
            points=edge['attribute_paths'][pi][idx:idx+2]
            if len(points)!=2 or points!=[segment['start'],segment['end']] or segment['status']!='single_source_line_covers' or len(segment['witnesses'])!=1:raise ValueError('plan projection lacks unique native line coverage')
            if any(not(box[0]<=p[0]<=box[1] and box[2]<=p[1]<=box[3]) for p in points):raise ValueError('plan projection leaves verified floor-plan scope')
            value=math.dist(*points)
            if value<=.05 or abs(value-segment['drawing_length'])>.0001:raise ValueError('native plan length differs')
            witness=segment['witnesses'][0]
            if witness['scope']!='modelspace':raise ValueError('nested model scaling is outside this length mode')
            pieces.append(dict(plan_edge=eid,path_index=pi,segment_index=idx,source_line_handle=witness['source_handle'],points=points,length_mm=value))
    if len({(p['plan_edge'],p['path_index'],p['segment_index']) for p in pieces})!=len(pieces):raise ValueError('plan segment counted twice')
    total=sum(p['length_mm'] for p in pieces)
    return dict(status='native_plan_horizontal_projection_partial_length',value_mm=total,pieces=pieces,
        installed_whole_edge_length_mm=None,unshown_connection_length_mm=None,
        scope='floor-plan XY pipe projection only; no axis drawing lengths or omitted connectors added')
