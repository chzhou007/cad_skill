"""Native endpoint caption and floor evidence; no physical-unit assumption."""
from decimal import Decimal
import copy,math
from confirm_crossview_paths import encode
from axis_unbranched_vertical_DN import source_key,chain_evidence
from axis_floor_elevation_texts import collect as level_reader
from native_level_evidence import floor_number,elevation_value
from crossview_equipment_branch_inventory import native_tee,index_graph

def floor_at(graph,route,scope,point,items):
    nodes,edges,adj=index_graph(graph);edge=edges[scope['edge_id']];path=edge['attribute_paths'][scope['path_index']]
    matches=[i for i,p in enumerate(path) if math.dist(p,point)<=.05]
    if len(matches)!=1:raise ValueError('vertical endpoint is not one original path vertex')
    vertex=matches[0];by={source_key(r):r for r in route['records']};choices=[]
    for side,index in [('start',0),('end',len(path)-1)]:
        nid=edge[side+'_node_id'];node=nodes[nid]
        if math.dist([node['x'],node['y']],path[index])>.05:continue
        low,high=sorted((vertex,index));walk=[by[edge['edge_id'],scope['path_index'],si] for si in range(low,high)]
        if any(r['direction_class']!='horizontal' for r in walk):continue
        evidence=chain_evidence(walk,None,items) if walk else None
        choices.append(dict(floor=node['floor'],source_endpoint_node=nid,horizontal_walk=evidence))
    if not choices and edge['floor_start']==edge['floor_end']:
        # A same-floor edge supplies a floor identity only; never a height.
        if {nodes[edge[k]]['floor'] for k in ('start_node_id','end_node_id')}!={edge['floor_start']}:raise ValueError('same-floor graph endpoints disagree')
        choices=[dict(floor=edge['floor_start'],source_endpoint_nodes=[edge['start_node_id'],edge['end_node_id']],same_floor_identity_only=True)]
    if not choices or len({c['floor'] for c in choices})!=1:raise ValueError('endpoint floor not bound without crossing a vertical')
    return choices


def binding(doc,graph,route,target,seed,point,items,sh,gh):
    nodes,edges,adj=index_graph(graph)
    if (target['edge_id'],target['path_index'])==(seed['edge_id'],seed['path_index']):
        low,high=sorted((target['segment_index'],seed['segment_index']))
        if high-low!=1:raise ValueError('direct endpoint caption is not on the adjacent path segment')
        by={source_key(r):r for r in route['records']}
        return dict(kind='original_native_two_arm_bend',proof=chain_evidence([by[target['edge_id'],target['path_index'],i] for i in range(low,high+1)],None,items))
    junctions=[n for n in nodes.values() if n.get('node_type') in ('tee','physical_junction') and math.dist([n['x'],n['y']],point)<=.05
        and {target['edge_id'],seed['edge_id']}<={e['edge_id'] for e in adj[n['node_id']]}]
    if len(junctions)!=1:raise ValueError('caption and vertical endpoint do not share one original physical T')
    return dict(kind='original_native_T',proof=native_tee(doc,graph,junctions[0]['node_id'],sh,gh))


def collect(doc,graph,route,seeds,items,source_hash,graph_hash):
    before=encode(graph),encode(route),encode(seeds),encode(items)
    if (seeds['source_graph_sha256']!=graph_hash or graph['metadata']['source_sha256']!=source_hash
        or route['inputs']['source']['sha256']!=source_hash or route['inputs']['graph']['sha256']!=graph_hash):
        raise ValueError('native level source/route/seed identity differs')
    levels=level_reader(doc,source_hash)
    floors={floor_number(x['floor_text']['text']):x for x in levels['records']}
    if None in floors or len(floors)!=len(levels['records']):raise ValueError('native floor identity is ambiguous')
    observations=[]
    for row in seeds['records']:
        if row['direction_class']!='horizontal':continue
        raw=row['observations'][0]['native_evidence']['parenthesized_source_value']
        if raw is not None:observations.append(dict(row,raw_level=raw))
    records=[];pending=[];coverage={0:0,1:0,2:0}
    for target in route['records']:
        if target['direction_class']!='vertical':continue
        ends=[]
        for point in target['scope_points']:
            hits=[s for s in observations if s['system']==target['system'] and min(math.dist(point,p) for p in s['scope_points'])<=.05]
            ends.append((point,hits))
        coverage[sum(bool(h) for _,h in ends)]+=1
        if not all(h for _,h in ends):continue
        try:
            bound=[]
            for point,hits in ends:
                if len({str(h['raw_level']) for h in hits})!=1:raise ValueError('competing literal endpoint levels')
                floor_proof=floor_at(graph,route,target,point,items);floor=floor_proof[0]['floor']
                if floor not in floors:raise ValueError('floor lacks native elevation TEXT and glyph')
                proofs=[binding(doc,graph,route,target,h,point,items,source_hash,graph_hash) for h in hits]
                offset=Decimal(str(hits[0]['raw_level']));datum=elevation_value(floors[floor]['source_elevation_text']['text'])
                bound.append(dict(point_xy=point,floor=floor,floor_identity_evidence=floor_proof,floor_native_elevation=floors[floor],
                    caption_evidence=hits,connection_evidence=proofs,raw_pipe_level=str(offset),raw_floor_datum=str(datum),
                    absolute_candidate_if_floor_relative=str(datum+offset),pipe_level_reference_confirmed=False,unit_selected=False))
            difference=abs(Decimal(bound[1]['absolute_candidate_if_floor_relative'])-Decimal(bound[0]['absolute_candidate_if_floor_relative']))
            records.append(dict(edge_id=target['edge_id'],path_index=target['path_index'],segment_index=target['segment_index'],system=target['system'],endpoints=bound,
                candidate_difference_in_source_level_units=str(difference),physical_length_mm=None,
                pending='project_level_unit_and_floor_relative_pipe_center_reference',drawing_Y_used_as_length=False,human_accepted=False))
        except (ValueError,KeyError) as exc:pending.append(dict(edge_id=target['edge_id'],path_index=target['path_index'],segment_index=target['segment_index'],reason=str(exc)))
    if before!=(encode(graph),encode(route),encode(seeds),encode(items)):raise ValueError('native level inputs mutated')
    return dict(mode='native_axis_direct_endpoint_level_evidence_v1',native_floor_levels=levels,records=records,pending=pending,
        direct_caption_endpoint_coverage=coverage,physical_lengths_assigned=0,unit_selected=False,pipe_level_reference_confirmed=False,
        graph_mutated=False,human_accepted=False)
