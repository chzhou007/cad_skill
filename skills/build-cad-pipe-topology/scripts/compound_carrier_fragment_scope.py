"""Do not lift a label from one arm of a composite edge onto another arm.

Only discharge an unbound proposal on an orthogonal native LINE when the whole
selected interval has its own independently unique, direct native DN reading.
Parallel or unsupported label geometry retains the original member barrier.
"""
import copy,math
from source_direct_dn_evidence import collect as direct
from native_dn_text_position import supported
from native_line_path_evidence import _on


def qualify(doc,graph,row,value,corridors,source_hash,graph_hash):
    result=dict(corridors=copy.deepcopy(corridors),excluded_unbound_fragment_proposals=[],
        direct_native_evidence=None,physical_member_identity_inferred=False,graph_mutated=False)
    if not corridors:return result
    dn=value['plan_DN_record'];edge=next(e for e in graph['edges']if e['edge_id']==row['plan_edges'][0])
    seeds=[e for group in dn.get('lineage',[])for e in group.get('evidence',[])]
    if dn.get('status')!='direct_plan_DN' or len(seeds)!=1 or seeds[0].get('edge_path')!=row['plan_edges']or seeds[0].get('transfers'):
        result['pending_reason']='no_unique_existing_direct_native_DN_scope';return result
    handle=seeds[0]['evidence_id'].split(':',1)[-1];text=doc.entitydb.get(handle)
    if text is None or text.dxftype()!='TEXT' or text not in doc.modelspace() or not supported(text):
        result['pending_reason']='unsupported_direct_source_text';return result
    # Every source path atom must belong to one candidate native LINE; no
    # unrelated corner arm is smuggled into a whole-edge annotation decision.
    owners=[]
    for c in corridors:
        line=doc.entitydb.get(c['source_LINE'])
        if line is not None and all(_on(p,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)
            for path in edge['attribute_paths']for p in path):owners.append(c['source_LINE'])
    if len(set(owners))!=1:
        result['pending_reason']='selected_interval_has_no_single_native_carrier';return result
    policy=dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=[text.dxf.layer],
        selections=[dict(text_handle=handle,expected_text=text.plain_text(),edge_id=edge['edge_id'],source_line_handle=owners[0])])
    try:proof=direct(doc,graph,policy,source_hash,graph_hash)
    except ValueError as e:result['pending_reason']=str(e);return result
    if len(proof['observations'])!=1 or proof['observations'][0]['nominal_mm']!=value['nominal_mm']:
        raise ValueError('direct source DN disagrees with qualified observation')
    result['direct_native_evidence']=proof;retained=[]
    for corridor in corridors:
        line=doc.entitydb[corridor['source_LINE']];v=line.dxf.end-line.dxf.start;length=math.hypot(v.x,v.y)
        excluded=[];keep=[]
        for declaration in corridor['declarations']:
            native=doc.entitydb.get(declaration['handle'])
            if native is None or native.dxftype()!='TEXT' or native not in doc.modelspace()or not supported(native)or native.plain_text()!=declaration['raw_text']or length<=.05:
                keep.append(declaration);continue
            angle=math.radians(native.dxf.rotation);ocs=native.ocs();zero=ocs.to_wcs((0,0,0));axis=ocs.to_wcs((math.cos(angle),math.sin(angle),0))-zero;norm=math.hypot(axis.x,axis.y)
            perpendicular=norm>.99 and abs(axis.z)<.001 and abs((axis.x*v.x+axis.y*v.y)/(norm*length))<=math.sin(math.radians(2))
            if perpendicular:excluded.append(dict(declaration=copy.deepcopy(declaration),native_TEXT_baseline_WCS=list(axis),native_LINE=corridor['source_LINE'],native_LINE_direction_WCS=list(v),reason='unbound_label_on_orthogonal_composite_edge_arm_not_this_directly_annotated_interval'))
            else:keep.append(declaration)
        result['excluded_unbound_fragment_proposals'].extend(excluded)
        if keep:retained.append(dict(corridor,declarations=keep))
    result['corridors']=retained
    return result
