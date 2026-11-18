"""Extend the inherited DN reader with source-identified projected T roles."""
from main_continuity_plan_DN import bind
from local_detail_plan_DN import collect as previous_collect
from full_plan_DN_source import collect as source_collect,_has_through
from crossview_equipment_branch_inventory import native_tee
from source_main_DN_continuity import roles as previous_roles,BASIS as OLD_BASIS
from full_plan_DN_inheritance import infer as original_infer
from native_projected_circle_main_role import collect as projected_collect,role as projected_role,STATUS,BASIS

def roles(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    ordinary={n:p for n,p in junctions.items()if p.get('status')!=STATUS}
    result=previous_roles(graph,seeds,verified_edges,ordinary,source_hash,graph_hash)['roles']if ordinary else {}
    for nid,proof in junctions.items():
        if proof.get('status')==STATUS:result[nid]=projected_role(graph,nid,proof,source_hash,graph_hash)
    return dict(roles=result)

def infer(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    reader=bind(original_infer,through_infer=roles);result=reader(graph,seeds,verified_edges,junctions,source_hash,graph_hash)
    result['native_main_continuity_nodes']=sorted(n for n,r in result['roles'].items()if r.get('role_basis')==OLD_BASIS)
    result['native_projected_circle_main_identity_nodes']=sorted(n for n,r in result['roles'].items()if r.get('role_basis')==BASIS)
    result['native_ray_directions_or_graph_geometry_changed']=False
    return result

def make_reader(authorities):
    evidence={}
    def supported(proof):return proof.get('status')==STATUS or _has_through(proof)
    def tee(doc,graph,nid,sh,gh):
        try:return native_tee(doc,graph,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!='missing or ambiguous graph T ray':raise
            node=next(n for n in graph['nodes']if n['node_id']==nid)
            if not node.get('expert_circle_evidence'):raise
            proof=projected_collect(doc,graph,nid,sh,gh,authorities);evidence[nid]=proof;return proof
    reader=bind(previous_collect,source_collect=bind(source_collect,_has_through=supported),infer=infer,native_tee=tee)
    def collect(*args,**kwargs):
        evidence.clear();result=reader(*args,**kwargs);result['native_projected_circle_evidence']=dict(evidence);result['native_projected_circle_nodes']=sorted(evidence);return result
    return collect
