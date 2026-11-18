"""Reuse current native main ancestry before the original crossover metric core."""
import math,re
from source_checked_plan_path_coverage import audit as original_audit
from source_reviewed_circle_branch_evidence import branch_coverage
from crossview_equipment_branch_inventory import index_graph
from legacy_named_provider_inventory import require

def audit(doc,graph,edge_id,anchor,source_hash,graph_hash,reader):
    nodes,edges,adj=index_graph(graph);edge=edges[edge_id];policy=dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge_id])
    if len(edge.get('attribute_paths',[]))<=1:return original_audit(doc,graph,policy,source_hash,graph_hash)
    current=reader(doc,graph,anchor,source_hash,graph_hash)
    if not current.get('current_main_lineage'):return original_audit(doc,graph,policy,source_hash,graph_hash)
    require(current.get('status')=='native_historical_circle_ray_evidence_unreviewed'and current.get('source_sha256')==source_hash and current.get('graph_sha256')==graph_hash and current.get('graph_mutated')is False and current.get('historical_reader_or_globals_changed')is False,'current main ancestry lacks its original native source witness')
    junctions=current.get('junctions',[]);require(len(junctions)==1 and junctions[0].get('node_id')==anchor,'current crossover anchor differs')
    rays=junctions[0].get('source_rays',[]);star={e['edge_id']for e in adj[anchor]}
    require(len(star)==len(rays)==3 and {r['edge_id']for r in rays}==star and {e['system']for e in adj[anchor]}=={edge['system']},'current native T star is incomplete or mixed')
    rim=[r for r in rays if r.get('scope')=='historical_source_reviewed_circle_rim'];require(len(rim)==1 and rim[0]['edge_id']==edge_id,'current proof does not establish this circle branch')
    mains=star-{edge_id}
    for row in current['current_main_lineage']:
        require(row.get('kind')=='source_bound_main_split'and row.get('current_edge_id')in mains and bool(row.get('original_edge_id'))and re.fullmatch('[0-9a-f]{64}',row.get('parent_sha256',''))is not None,'unproved main descendant cannot replace the historical path entry')
    proof=branch_coverage(doc,graph,edge,source_hash,graph_hash)
    require(proof['status']=='native_source_paths_and_excluded_crossovers_replayed'and proof.get('graph_mutated')is False,'original source crossover replay failed')
    segments=[dict(s,path_index=p['original_path_index'])for p in proof['paths']for s in p['coverage']['segments']]
    return dict(status='partial_source_coverage_not_physical_length',source_sha256=source_hash,graph_sha256=graph_hash,
        edges=[dict(edge_id=edge_id,system=edge['system'],segments=segments,coverage_mode='native_plan_paths_excluding_replayed_crossovers',source_path_evidence=proof,junction_evidence=current,
                    source_covered_drawing_length=sum(s['drawing_length']for s in segments),unverified_drawing_length=0,physical_length='unknown',current_main_lineage_reapplied=True)],
        graph_mutated=False,hil_ready=False,historical_reader_or_globals_changed=False,physical_gap_lengths_assigned=0)
