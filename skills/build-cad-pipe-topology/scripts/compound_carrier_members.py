"""Split source declaration roles from a merged planar drawing carrier.

Only independently witnessed device-branch T intervals gain a member graph.
Literal source-level correspondence selects a plan declaration; axis DN is a
cross-check. Other pipes, drawing contacts and installed lengths stay unknown.
"""
import copy,hashlib,math
from confirm_crossview_paths import encode
from compound_pipe_label_evidence import collect as labels
from source_compound_dn_evidence import extract
from pipe_annotation_attributes import source_texts
from native_paired_end_labels import level_key
from native_line_path_evidence import LAYERS,_on
from native_main_endpoint_extent import endpoint_relation

def carrier_risks(doc,graph,source_hash):
    declarations=labels(doc,source_hash);by={r['handle']:r for r in declarations['records']}
    candidates=extract(source_texts(doc,'plan',source_hash),graph['edges'],{r['layer']for r in declarations['records']})
    pipes={e.dxf.handle:e for e in doc.modelspace().query('LINE')if e.dxf.layer in LAYERS.values()};byedge={e['edge_id']:e for e in graph['edges']};corridors={}
    for row in candidates['records']:
        for eid in row['candidate_edge_ids']:
            edge=byedge[eid]
            for handle in edge.get('source_handles',[]):
                line=pipes.get(handle)
                if line is None or line.dxf.layer!=LAYERS.get(edge['system']):continue
                a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2]
                if not any(_on(p,a,b,.05)and _on(q,a,b,.05)and math.dist(p,q)>.05 for path in edge.get('attribute_paths',[])for p,q in zip(path,path[1:])):continue
                corridor=corridors.setdefault(handle,dict(source_LINE=handle,system=edge['system'],native_endpoints=[a,b],declarations={},edges=[]))
                corridor['declarations'][row['source_text']['handle']]=by[row['source_text']['handle']]
    for handle,corridor in corridors.items():
        a,b=corridor['native_endpoints']
        for edge in graph['edges']:
            if edge['system']!=corridor['system']or handle not in edge.get('source_handles',[]):continue
            touched=[]
            for pi,path in enumerate(edge.get('attribute_paths',[])):
                for si,(p,q)in enumerate(zip(path,path[1:])):
                    if _on(p,a,b,.05)and _on(q,a,b,.05)and math.dist(p,q)>.05:touched.append(dict(path_index=pi,segment_index=si,points=[p,q]))
            if touched:corridor['edges'].append(dict(edge_id=edge['edge_id'],segments=touched))
        corridor['declarations']=list(corridor['declarations'].values())
    return dict(status='native_compound_carrier_LINE_lineage_barriers_not_member_assignments',corridors=list(corridors.values()),
        barriers_propagated_by_exact_source_LINE_not_proximity=True,scalar_DN_allowed_without_member_proof=False)

def member(row,plan,axis,plan_LINE,axis_LINE,corridor,caption,native,metric):
    if row['kind']!='same_floor_T_to_T_main'or len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('one independently mapped main interval required')
    system=row['system'];floor=row['floor'];peid=row['plan_edges'][0];aeid=row['iso_edges'][0]
    if corridor['source_LINE']!=plan_LINE or corridor['system']!=system or caption['native_pipe']['source_LINE']!=axis_LINE or caption['native_pipe']['system']!=system:raise ValueError('member native LINE/service differs')
    relations={view:endpoint_relation(graph,eid,floor,system)for view,graph,eid in(('plan',plan,peid),('iso',axis,aeid))}
    waves={r['tee_id']:r for r in plan.get('sourceWaveMainCohort',{}).get('records',[])}
    anchors=[]
    for pn,an in zip((row['plan_start'],row['plan_end']),(row['iso_start'],row['iso_end'])):
        wave=waves.get(pn)
        if not wave or wave['system']!=system or wave['target']['source_handle']!=plan_LINE:raise ValueError('member needs two independently proved native branch anchors')
        if pn not in native['plan']['junctions']or an not in native['iso']['junctions']:raise ValueError('both views require native T evidence')
        anchors.append(dict(equipment_id=wave['equipment_id'],plan_T=pn,axis_T=an,plan_branch=wave['branch_edge'],native_wave_handle=wave['wave']['wave_handle']))
    if len({a['equipment_id']for a in anchors})!=2:raise ValueError('member anchors are not independent')
    for view,handle in(('plan',plan_LINE),('iso',axis_LINE)):
        audits=native[view]['coverage']['edges']
        if len(audits)!=1 or audits[0]['edge_id']!=row[view+'_edges'][0]:raise ValueError('member native scope differs')
        if any(s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 or s['witnesses'][0].get('scope')!='modelspace'or s['witnesses'][0]['source_handle']!=handle for s in audits[0]['segments']):raise ValueError('member path has mixed or ambiguous native carriers')
    level=caption['text']['literal_level_key'];matches=[]
    for declaration in corridor['declarations']:
        choices=[m for m in declaration['members']if level_key(m['source_level_text'])==level]
        if len(choices)!=1:raise ValueError('literal source level does not select one plan declaration')
        matches.append(dict(text_handle=declaration['handle'],member=choices[0]))
    if not matches or len({m['member']['nominal_mm']for m in matches})!=1:raise ValueError('selected plan declarations conflict')
    nominal=matches[0]['member']['nominal_mm']
    if caption['text']['nominal_mm']!=nominal:raise ValueError('axis cross-check conflicts with selected plan DN')
    edge=next(e for e in plan['edges']if e['edge_id']==peid)
    if metric.get('installed_whole_edge_length_mm')is not None or metric['value_mm']<=0:raise ValueError('member metric provenance differs')
    expected={(pi,si)for pi,path in enumerate(edge['attribute_paths'])for si in range(len(path)-1)}
    if {(p['path_index'],p['segment_index'])for p in metric['pieces']}!=expected or abs(sum(p['length_mm']for p in metric['pieces'])-metric['value_mm'])>.0001:raise ValueError('member metric extent incomplete')
    for piece in metric['pieces']:
        points=edge['attribute_paths'][piece['path_index']][piece['segment_index']:piece['segment_index']+2]
        if piece['plan_edge']!=peid or piece['source_line_handle']!=plan_LINE or piece['points']!=points or abs(math.dist(*points)-piece['length_mm'])>.0001:raise ValueError('member metric native points differ')
    token=hashlib.sha256(encode(dict(plan_LINE=plan_LINE,level=level,system=system,floor=floor))).hexdigest()[:16]
    member_scope='MEMBER:'+token
    return dict(mapping_id=row['mapping_id'],axis_edge_id=aeid,plan_edge_id=peid,floor=floor,system=system,member_scope_id=member_scope,
        member_edge_id=member_scope+':'+peid,member_node_ids=[member_scope+':'+row['plan_start'],member_scope+':'+row['plan_end']],
        source_level_literal=caption['text']['source_level_text'],literal_level_key=level,physical_elevation_mm=None,
        nominal_mm=nominal,DN_value_source='plan_compound_declaration_selected_by_native_member_identity',DN_used_for_mapping=False,
        plan_declarations=copy.deepcopy(matches),axis_caption_crosscheck=copy.deepcopy(caption),plan_LINE=plan_LINE,axis_LINE=axis_LINE,
        anchors=anchors,endpoint_relations=relations,native_evidence=copy.deepcopy(native),plan_attribute_paths=copy.deepcopy(edge['attribute_paths']),
        plan_run_centerline_mm=metric['value_mm'],plan_projection=copy.deepcopy(metric),run_includes_inline_assembly_extents=True,
        plan_component_member_allocation='unresolved',net_pipe_cut_length_mm=None,installed_whole_length_mm=None,
        source_drawing_graph_unchanged=True,other_member_connections_inferred=False,physical_pipe_instance_count_inferred=False,human_accepted=False)
