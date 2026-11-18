"""Use original plan metric readers on source-qualified mapped intervals.

Exactly touching path arrays are bookkeeping subdivisions, never omissions.
Crossovers and flexible joints keep their own original evidence owners. An
unsupported length remains unknown without destroying a valid correspondence.
"""
import copy
from confirm_crossview_paths import encode
import hashlib
from native_plan_projection_lengths import lengths
from inherited_batch_plan_metrics import extend

def coalesced_scope(graph,record):
    if len(record['plan_edges'])!=1:raise ValueError('one interval required for exact path projection')
    eid=record['plan_edges'][0];edge=next(e for e in graph['edges']if e['edge_id']==eid);paths=edge['attribute_paths'];joined=[];origins=[]
    for pi,path in enumerate(paths):
        if len(path)<2:raise ValueError('invalid source path subdivision')
        indices=[(pi,i)for i in range(len(path)-1)]
        if joined and joined[-1][-1]==path[0]:joined[-1].extend(copy.deepcopy(path[1:]));origins[-1].extend(indices)
        else:joined.append(copy.deepcopy(path));origins.append(indices)
    if len(joined)==len(paths):raise ValueError('no exact touching source subdivisions')
    private=dict(graph,edges=[dict(e,attribute_paths=joined)if e['edge_id']==eid else e for e in graph['edges']])
    return private,dict(input_graph_value_sha256=hashlib.sha256(encode(graph)).hexdigest(),projection_graph_sha256=hashlib.sha256(encode(private)).hexdigest(),original_attribute_paths=copy.deepcopy(paths),projected_attribute_paths=joined,original_indices=origins,source_or_topology_changed=False)

def touching_projection(graph,coverage,record,units):
    if len(record['plan_edges'])!=1:raise ValueError('touching metric needs one mapped plan edge')
    eid=record['plan_edges'][0];edge=next(e for e in graph['edges']if e['edge_id']==eid);paths=edge['attribute_paths']
    if len(paths)<2 or any(not isinstance(p,list)or len(p)<2 for p in paths):raise ValueError('multiple nonempty native paths required')
    if any(a[-1]!=b[0]for a,b in zip(paths,paths[1:])):raise ValueError('native path subdivisions do not touch exactly; never bridge their gap')
    audit=next(e for e in coverage['edges']if e['edge_id']==eid);source={(s.get('path_index',0),s['index']):s for s in audit['segments']}
    if len(source)!=len(audit['segments']):raise ValueError('duplicate native path coverage')
    points=copy.deepcopy(paths[0]);origins=[];segments=[]
    for pi,path in enumerate(paths):
        if pi:points.extend(copy.deepcopy(path[1:]))
        for si in range(len(path)-1):
            s=copy.deepcopy(source[(pi,si)])
            if [s['start'],s['end']]!=path[si:si+2]:raise ValueError('native touching path coverage differs')
            s['index']=len(segments);s.pop('path_index',None);segments.append(s);origins.append((pi,si))
    if set(source)!={(pi,si)for pi,p in enumerate(paths)for si in range(len(p)-1)}:raise ValueError('touching path native inventory incomplete')
    private=dict(graph,edges=[dict(edge,attribute_paths=[points])]);projected=dict(edges=[dict(audit,segments=segments)])
    result=lengths(private,projected,record,units)
    for piece,(pi,si)in zip(result['pieces'],origins):piece['path_index']=pi;piece['segment_index']=si
    result.update(metric_reader='inherited_plan_projection_on_exact_touching_subdivisions',source_paths_changed=False,subdivision_connections_added=0,graphic_or_omitted_spans_added=False)
    return result

def measure(doc,graph,inventory,coverage,record,units,hashes,template):
    prior=dict(mapping_id=record['mapping_id'],plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],projection=None)
    attempts=[]
    try:prior.update(projection=lengths(graph,coverage,record,units),reader='inherited_native_plan_projection')
    except ValueError as exc:prior['reason']=str(exc);attempts.append(dict(reader='native_plan_projection',reason=str(exc)))
    if prior['projection']is None:
        try:prior.update(projection=touching_projection(graph,coverage,record,units),reader='inherited_native_exact_touching_subdivisions')
        except ValueError as exc:attempts.append(dict(reader='exact_touching_subdivisions',reason=str(exc)))
    if prior['projection']is None:
        # The original extension independently replays inline/crossover evidence.
        prior=extend(doc,graph,inventory,[record],[prior],units,hashes,template)['records'][0]
        attempts.extend(prior.get('attempts',[]))
    if prior['projection']is None:
        try:
            private,binding=coalesced_scope(graph,record)
            alternative=extend(doc,private,inventory,[record],[prior],units,dict(hashes,graph_sha256=binding['projection_graph_sha256']),template)['records'][0]
            attempts.extend(alternative.get('attempts',[]))
            if alternative['projection']is not None:
                for piece in alternative['projection']['pieces']:
                    pi,si=binding['original_indices'][piece['path_index']][piece['segment_index']]
                    if piece['points']!=binding['original_attribute_paths'][pi][si:si+2]:raise ValueError('coalesced native metric changed a source segment')
                    piece['path_index']=pi;piece['segment_index']=si
                prior=dict(alternative,reader=alternative['reader']+'_after_exact_touching_projection',exact_touching_scope_projection=binding)
        except ValueError as exc:attempts.append(dict(reader='inherited_reader_after_exact_touching_projection',reason=str(exc)))
    return dict(prior,attempts=attempts,installed_whole_edge_length_mm=None,unknown_length_filled_with_zero=False)
