"""Dispatch complete edge batches to the inherited LINE path reader.

Multi-path edges get explicit read-only per-path projections. The source graph
hash and projection hash stay distinct. Missing spans never become connectivity
or metric proof merely because each visible fragment was read.
"""
import copy
import hashlib
from confirm_crossview_paths import encode
from native_path_coverage_audit import audit


def collect(doc,graph,edge_ids,source_hash,graph_hash):
    by={e['edge_id']:e for e in graph['edges']};single=[];multi=[];unresolved=[]
    for eid in edge_ids:
        if eid not in by:raise ValueError('batch path edge missing')
        count=len(by[eid].get('attribute_paths',[]))
        if count==1:single.append(eid)
        elif count>1:multi.append(eid)
        else:unresolved.append(dict(edge_id=eid,reason='no_source_attribute_paths'))
    result=audit(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=single),source_hash,graph_hash) if single else dict(edges=[])
    for eid in multi:
        edge=by[eid];segments=[];proofs=[]
        for pi,path in enumerate(edge['attribute_paths']):
            projected=dict(edge,attribute_paths=[copy.deepcopy(path)])
            private=dict(graph,edges=[projected])
            projection_hash=hashlib.sha256(encode(private)).hexdigest()
            proof=audit(doc,private,dict(source_sha256=source_hash,graph_sha256=projection_hash,edges=[eid]),source_hash,projection_hash)
            for segment in proof['edges'][0]['segments']:
                segments.append(dict(segment,path_index=pi))
            proofs.append(dict(path_index=pi,reading_projection_sha256=projection_hash,evidence=proof))
        result['edges'].append(dict(edge_id=eid,system=edge['system'],segments=segments,
            coverage_mode='separate_native_path_fragments_not_gap_or_whole_route_proof',
            original_attribute_paths=copy.deepcopy(edge['attribute_paths']),path_projections=proofs,
            physical_gap_lengths_assigned=0,continuity_proved_by_this_reader=False))
    result.update(source_sha256=source_hash,graph_sha256=graph_hash,multi_path_edges=multi,unresolved=unresolved,
        source_graph_mutated=False,multi_path_continuity_or_whole_length_proved=False)
    return result
