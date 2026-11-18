"""Reuse explicit user circle ancestry with the original crossover path core."""
from current_plan_crossover_path_reapplication import audit as prior_audit
from source_reviewed_circle_branch_evidence import branch_coverage
from source_main_DN_continuity import STATUS
from crossview_equipment_branch_inventory import index_graph
from legacy_named_provider_inventory import require

def audit(doc,graph,edge_id,anchor,source_hash,graph_hash,reader):
    nodes,edges,adj=index_graph(graph);edge=edges[edge_id]
    if len(edge.get('attribute_paths',[]))<=1:return prior_audit(doc,graph,edge_id,anchor,source_hash,graph_hash,reader)
    proof=reader(doc,graph,anchor,source_hash,graph_hash)
    if proof.get('status')!=STATUS:return prior_audit(doc,graph,edge_id,anchor,source_hash,graph_hash,reader)
    require(proof.get('source_sha256')==source_hash and proof.get('graph_sha256')==graph_hash and proof.get('original_main_rays_replayed')is True and proof.get('graph_mutated')is False,'original confirmed circle native source proof changed')
    meta=nodes[anchor].get('user_confirmed_circle',{});review=proof.get('original_review',{})
    require(meta and edge.get('source_user_circle_connection')==meta and review.get('circle_handle')==meta.get('circle_handle')and review.get('original_graph_sha256')==meta.get('source_graph_sha256')and review.get('native_screen_sha256')==meta.get('screen_sha256'),'user circle confirmation belongs to another source scope')
    j=proof.get('junctions',[]);require(len(j)==1 and j[0]['node_id']==anchor and j[0]['system']==edge['system'],'confirmed circle anchor differs')
    rays=j[0]['source_rays'];star={e['edge_id']for e in adj[anchor]}
    require(len(star)==len(rays)==3 and {r['edge_id']for r in rays}==star and {e['system']for e in adj[anchor]}=={edge['system']},'confirmed circle T star is incomplete or mixed')
    rims=[r for r in rays if r.get('scope')=='confirmed_native_circle_rim']
    require(len(rims)==1 and rims[0]['edge_id']==edge_id and all(r.get('scope')=='confirmed_native_circle_center_LINE_endpoint'for r in rays if r not in rims),'selected source path is not the original confirmed rim branch')
    path=branch_coverage(doc,graph,edge,source_hash,graph_hash)
    require(path.get('status')=='native_source_paths_and_excluded_crossovers_replayed'and path.get('graph_mutated')is False,'original crossover reader failed')
    segments=[dict(s,path_index=p['original_path_index'])for p in path['paths']for s in p['coverage']['segments']]
    return dict(status='partial_source_coverage_not_physical_length',source_sha256=source_hash,graph_sha256=graph_hash,
        edges=[dict(edge_id=edge_id,system=edge['system'],segments=segments,coverage_mode='native_plan_paths_excluding_replayed_crossovers',source_path_evidence=path,junction_evidence=proof,
                    source_covered_drawing_length=sum(s['drawing_length']for s in segments),unverified_drawing_length=0,physical_length='unknown',original_user_circle_and_crossover_owners_replayed=True)],
        graph_mutated=False,physical_gap_lengths_assigned=0,human_accepted=False)
