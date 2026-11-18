"""Retain source-checked detail topology without manufacturing physical length."""
import hashlib,math
from confirm_crossview_paths import encode
from native_plan_projection_lengths import lengths
from reconstruct_sideview_equipment_ownership import MODE

STATUS='source_confirmed_detail_topology_physical_length_unknown'
ALLOCATION='unmeasured_confirmed_detail_view_not_floor_plan_metric'


def has_detail_scope(plan,record):
    edges={e['edge_id']:e for e in plan['edges']}
    return any(edges[eid].get('source_view_context') is not None for eid in record['plan_edges'])


def projection(plan,coverage,record,units,source_hashes,allow_detail=False):
    if not has_detail_scope(plan,record):return lengths(plan,coverage,record,units)
    if allow_detail is not True:raise ValueError('confirmed detail topology needs explicit nonmetric attachment policy')
    root=plan.get('sourceSideviewEquipmentOwnership',{});source=source_hashes.get('plan');graph_hash=source_hashes.get('plan_graph')
    alias_hash=hashlib.sha256(encode(plan.get('confirmedSideviewCanonicalization',{}))).hexdigest()
    if (root.get('mode')!=MODE or root.get('source_sha256')!=source or root.get('human_accepted') is not False
        or root.get('physical_ports_verified') is not False or plan.get('metadata',{}).get('source_sha256')!=source
        or not isinstance(graph_hash,str) or len(graph_hash)!=64):raise ValueError('detail attachment lacks current verified source ownership')
    edges={e['edge_id']:e for e in plan['edges']};audits={e['edge_id']:e for e in coverage['edges']};pieces=[];roles=[]
    for eid in record['plan_edges']:
        edge=edges[eid];role=edge.get('source_view_context') or {};audit=audits[eid]
        if (eid not in root.get('detail_edge_ids',[]) or edge.get('system')!=record['system'] or audit.get('system')!=record['system']
            or role.get('kind')!='confirmed_detail_view' or role.get('coordinate_domain')!='native_detail_drawing'
            or role.get('source_sha256')!=source or role.get('input_graph_sha256')!=root.get('input_graph_sha256')
            or role.get('confirmed_alias_root_sha256')!=alias_hash or role.get('physical_length_from_drawing_span') is not False
            or role.get('metric_verified_by_this_stage') is not False):raise ValueError('mixed or stale detail source-view scope')
        for names in (('floor_start','start_floor'),('floor_end','end_floor')):
            values=[edge[k] for k in names if k in edge]
            if not values or any(v!=record['floor'] for v in values):raise ValueError('detail attachment floor differs')
        if not audit.get('segments'):raise ValueError('detail source pipe coverage missing')
        for segment in audit['segments']:
            pi=segment.get('path_index',0);si=segment['index'];path=edge['attribute_paths'][pi][si:si+2]
            witnesses=segment.get('witnesses',[])
            if (segment.get('status')!='single_source_line_covers' or len(witnesses)!=1 or witnesses[0].get('scope')!='modelspace'
                or path!=[segment['start'],segment['end']] or len(path)!=2
                or any(len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in path)):
                raise ValueError('detail path lacks unique native source evidence')
            pieces.append(dict(plan_edge=eid,path_index=pi,segment_index=si,source_line_handle=witnesses[0]['source_handle'],
                points=path,drawing_span_native_units=math.dist(*path),physical_length_mm=None))
        roles.append(dict(edge_id=eid,source_view_context=role))
    if len({(r['plan_edge'],r['path_index'],r['segment_index']) for r in pieces})!=len(pieces):raise ValueError('detail path counted twice')
    return dict(status=STATUS,value_mm=None,pieces=pieces,installed_whole_edge_length_mm=None,unshown_connection_length_mm=None,
        detail_context=dict(plan_graph_sha256=graph_hash,plan_source_sha256=source,confirmed_alias_root_sha256=alias_hash,plan_edges=list(record['plan_edges']),
            source_view_roles=roles,native_coverage_sha256=hashlib.sha256(encode([audits[eid] for eid in record['plan_edges']])).hexdigest(),
            physical_units_applied=False,human_accepted=False),
        scope='confirmed detail topology and native drawing evidence only; physical pipe length unknown')


def is_unmeasured_detail(metric,record,evidence):
    context=metric.get('detail_context',{})
    return (metric.get('status')==STATUS and metric.get('value_mm') is None and metric.get('edge_value_mm') is None
        and metric.get('allocation')==ALLOCATION and context.get('plan_edges')==record['plan_edges']
        and context.get('plan_graph_sha256')==evidence.get('graph_sha256') and context.get('plan_source_sha256')==evidence.get('source_sha256')
        and context.get('physical_units_applied') is False and context.get('human_accepted') is False)
