"""Locate a source-owned axis DN on an exact original drawing segment.

Drawing direction and graph floor fields describe evidence domains. They do
not prove a physical drop length, an inter-floor riser or an extent match.
"""
import math
from native_line_path_evidence import _on,LAYERS


def locate(graph,ownership,source_hash,graph_hash):
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash or ownership.get('source_sha256')!=source_hash
        or ownership.get('graph_sha256')!=graph_hash or ownership.get('graph_mutated') is not False
        or ownership.get('physical_values_fused') is not False or ownership.get('human_accepted') is not False):
        raise ValueError('current source-owned local axis DN scope required')
    edges={e['edge_id']:e for e in graph['edges']};seen=set();records=[]
    if len(edges)!=len(graph['edges']) or not ownership.get('records'):raise ValueError('unique nonempty local DN ownership required')
    for proof in ownership['records']:
        eid=proof['current_edge_id'];binding=proof['native_binding'];text=proof['source_text'];handle=text['handle'];edge=edges.get(eid)
        if (not edge or handle in seen or text.get('source_sha256')!=source_hash or binding.get('current_graph_owners')!=[eid]
            or binding.get('layer')!=LAYERS.get(edge['system']) or proof.get('source_chain')!=[binding.get('root_handle'),binding.get('child_handle')]
            or proof.get('scope')!='native_nested_branch_annotation_only_not_whole_edge_DN'
            or proof.get('whole_edge_DN_assigned') is not False or proof.get('human_accepted') is not False):
            raise ValueError('local DN native identity, system or extent differs')
        seen.add(handle);point=binding['projection'];native=binding['XYZ']
        if (len(point)!=2 or len(native)!=2 or any(len(p)!=3 for p in native)
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for p in [point]+native for v in p)):
            raise ValueError('finite native DN projection and XYZ required')
        matches=[]
        for pi,path in enumerate(edge.get('attribute_paths',[])):
            for si,(a,b) in enumerate(zip(path,path[1:])):
                if not _on(point,a,b,.05):continue
                if not all(_on(p,native[0][:2],native[1][:2],.05) for p in (a,b)) or math.dist(a,b)<=.05:
                    raise ValueError('DN owner segment leaves its native source line')
                dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1]);direction='vertical_stroke_in_CAD_WCS' if dx<=.05 else 'horizontal_stroke_in_CAD_WCS' if dy<=.05 else 'oblique_stroke_in_CAD_WCS'
                matches.append(dict(path_index=pi,segment_index=si,scope_points=[list(a),list(b)],drawing_direction=direction,drawing_span_units=math.dist(a,b)))
        if len(matches)!=1:raise ValueError('local DN must locate one unique nonzero original axis segment')
        floors=[]
        for fields in (('floor_start','start_floor'),('floor_end','end_floor')):
            declared=[edge[k] for k in fields if k in edge]
            if any(isinstance(f,bool) or not isinstance(f,int) for f in declared) or len(set(declared))>1:raise ValueError('local DN graph floor fields conflict')
            floors.append(declared[0] if declared else None)
        relation='unknown_graph_floor_domain' if None in floors else 'same_floor_graph_scope' if floors[0]==floors[1] else 'different_floor_graph_scope'
        records.append(dict(edge_id=eid,text_handle=handle,nominal_mm=proof['nominal_mm_candidate'],source_chain=list(proof['source_chain']),
            native_label_projection=list(point),native_source_XYZ=[list(p) for p in native],segment=matches[0],floor_start=floors[0],floor_end=floors[1],
            graph_floor_relation=relation,source_sha256=source_hash,graph_sha256=graph_hash,
            physical_vertical_length_mm=None,inter_floor_riser_proved=False,equal_plan_axis_segment_extents_proved=False,human_accepted=False))
    return dict(status='source_owned_DN_original_axis_segment_domains_not_physical_extents',records=records,source_sha256=source_hash,graph_sha256=graph_hash,
        graph_mutated=False,physical_values_assigned=0,physical_direction_or_length_proved=False,human_accepted=False)
