"""Measure a plan XY centreline through independently replayed drafting crossings.

This is a full horizontal projection, never installed or net-cut length. Keep
the old gap's unknown physical length/elevation verbatim. No wave omission,
inline joint, circle-radius connector, detail view or new topology is measured.
"""
import copy,hashlib,math
from confirm_crossview_paths import encode
from native_main_interval_metrics import coalesced_scope
from inherited_circle_branch_inventory import path_evidence
from native_plan_projection_lengths import lengths
from native_main_endpoint_extent import endpoint_relation

MODE='native_plan_drafted_crossover_complete_XY_centerline_v1'

def measure(doc,graph,eid,units,source_hash,graph_hash):
    before=encode(graph);edges=[e for e in graph['edges']if e['edge_id']==eid]
    if len(edges)!=1 or graph['metadata']['source_sha256']!=source_hash:raise ValueError('unique source-bound original plan edge required')
    edge=edges[0];paths=edge['attribute_paths'];gaps=edge.get('source_normalized_crossovers',[])
    if units.get('status')!='native_mm_units_corroborated_not_pipe_dimension_assignment':raise ValueError('corroborated original plan millimetres required')
    if not gaps or len(paths)<2:raise ValueError('original source-normalized drafting crossovers required')
    if any(edge.get(k)for k in('source_view_context','source_flexible_joints','source_wave_omission','source_omission')):raise ValueError('detail, inline or wave span retains its original length owner')
    try:private,binding=coalesced_scope(graph,dict(plan_edges=[eid]))
    except ValueError as exc:
        if str(exc)!='no exact touching source subdivisions':raise
        private=graph;binding=None
    target=next(e for e in private['edges']if e['edge_id']==eid);parts=target['attribute_paths']
    ph=hashlib.sha256(encode(private)).hexdigest()if binding else graph_hash
    replay=path_evidence(doc,private,target,source_hash,ph);proof=replay['evidence']
    if proof.get('status')!='native_source_paths_and_excluded_crossovers_replayed'or len(proof['crossovers'])!=len(gaps)or len(parts)!=len(gaps)+1:raise ValueError('every separated path requires one independently replayed drafting crossing')
    box=units['plan_window'];bridges=[];used=set();joined=copy.deepcopy(parts[0]);pieces=[]
    for index,(left,right)in enumerate(zip(parts,parts[1:])):
        a,b=left[-1],right[0]
        hits=[(i,g)for i,g in enumerate(gaps)if (math.dist(a,g['a'])<=.05 and math.dist(b,g['b'])<=.05)or(math.dist(a,g['b'])<=.05 and math.dist(b,g['a'])<=.05)]
        if len(hits)!=1 or hits[0][0]in used:raise ValueError('drafting crossing does not uniquely bound adjacent original paths')
        gi,g=hits[0];used.add(gi)
        if g['crossing_connectivity']!='independent_pipes_no_junction'or len(g['crossings'])!=1 or g['crossings'][0]['crossed_source_system']==edge['system']:raise ValueError('same-system junction or ambiguous crossing is not a drafted underpass')
        if any(not(box[0]<=p[0]<=box[1]and box[2]<=p[1]<=box[3])for p in(a,b)):raise ValueError('drafting crossing outside corroborated plan window')
        native=[r for r in proof['crossovers']if r['source_gap_id']==g['source_gap_id']]
        if len(native)!=1:raise ValueError('unique original gap replay required')
        span=math.dist(a,b)
        bridges.append(dict(kind='source_replayed_drafting_crossover_XY_projection',source_gap_id=g['source_gap_id'],points=copy.deepcopy([a,b]),horizontal_projection_mm=span,native_replay=copy.deepcopy(native[0]),original_gap=copy.deepcopy(g),physical_gap_length_mm=None,relative_elevation_mm=None))
        joined.extend(copy.deepcopy(right))
    if len(used)!=len(gaps):raise ValueError('unconsumed original crossing')
    reading=dict(private,edges=[dict(e,attribute_paths=[joined])if e['edge_id']==eid else e for e in private['edges']])
    relation=endpoint_relation(reading,eid,edge.get('floor_start',edge.get('start_floor')),edge['system'])
    audits=[dict(s,path_index=p['original_path_index'])for p in proof['paths']for s in p['coverage']['segments']]
    coverage=dict(edges=[dict(edge_id=eid,system=edge['system'],segments=audits,coverage_mode='native_plan_paths_excluding_replayed_crossovers',source_path_evidence=proof)])
    projection=lengths(private,coverage,dict(plan_edges=[eid],system=edge['system']),units)
    for p in projection['pieces']:
        if binding:
            pi,si=binding['original_indices'][p['path_index']][p['segment_index']]
            if p['points']!=paths[pi][si:si+2]:raise ValueError('native projection altered an original source interval')
            p.update(path_index=pi,segment_index=si)
        pieces.append(dict(p,kind='native_plan_pipe_XY_projection'))
    value=projection['value_mm']+sum(g['horizontal_projection_mm']for g in bridges)
    if not math.isfinite(value)or value<=0 or abs(sum(math.dist(a,b)for a,b in zip(joined,joined[1:]))-value)>.0001:raise ValueError('full endpoint-bounded XY projection does not conserve source pieces')
    if encode(graph)!=before:raise ValueError('source graph mutated')
    return dict(mode=MODE,plan_edge_id=eid,system=edge['system'],floor=edge.get('floor_start',edge.get('start_floor')),plan_nodes=[edge['start_node_id'],edge['end_node_id']],original_attribute_paths=copy.deepcopy(paths),source_path_projection=binding,native_crossover_replay=replay,endpoint_relation=relation,pipe_projection_mm=projection['value_mm'],pipe_pieces=pieces,crossover_projections=bridges,complete_horizontal_centerline_projection_mm=value,measurement_kind='floor_plan_complete_XY_centerline_projection_not_installed_length',source_sha256=source_hash,graph_sha256=graph_hash,installed_length_mm=None,net_pipe_cut_length_mm=None,physical_gap_lengths_assigned=0,source_paths_mutated=False,new_connections_added=0,human_accepted=False)
