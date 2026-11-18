"""Preserve native main continuity at an explicitly confirmed corner-main T.

Two native arms touching the circle center continue the original main. A third
arm ending on the rim is its reviewed branch, even if it is geometrically
opposite one main arm. Preserve all raw directions and the original proof;
only DN main/branch roles use this independently replayed source contract.
"""
import copy,math,types
from crossview_equipment_branch_inventory import index_graph
from through_source_DN_inheritance import infer as geometric_infer
from full_plan_DN_inheritance import infer as original_infer

STATUS='original_user_circle_corner_main_and_current_native_T_replayed'
BASIS='original_native_center_arm_main_continuity_across_confirmed_circle'


def native_main_role(graph,nid,proof,geometric_role):
    nodes,edges,adj=index_graph(graph);node=nodes[nid];meta=node.get('user_confirmed_circle',{})
    roots=[];root=graph.get('userConfirmedCircleJunctionRepair');seen=set()
    while isinstance(root,dict):
        if id(root)in seen:raise ValueError('cyclic confirmed main-continuity repair')
        seen.add(id(root))
        if root.get('input_graph_sha256')==meta.get('source_graph_sha256'):
            for row in root.get('records',[]):
                if row.get('tee')==nid and row.get('circle_handle')==meta.get('circle_handle'):roots.append((root,row))
        root=root.get('previous_repair')
    if (len(roots)!=1 or not meta or proof.get('original_main_rays_replayed')is not True
        or proof.get('original_review',{}).get('original_graph_sha256')!=meta.get('source_graph_sha256')
        or proof.get('original_review',{}).get('native_screen_sha256')!=meta.get('screen_sha256')
        or proof.get('original_review',{}).get('circle_handle')!=meta.get('circle_handle')):
        raise ValueError('native main-continuity source contract missing or changed')
    root,record=roots[0]
    if root.get('confirmation')!=meta.get('confirmation')or root.get('source_sha256')!=proof['source_sha256']:
        raise ValueError('original confirmed main-continuity answer/source differs')
    rays=proof['junctions'][0]['source_rays'];by={r['edge_id']:r for r in rays}
    mains=[e for e in adj[nid]if e['edge_id']in record.get('main_child_edges',[])]
    branches=[e for e in adj[nid]if e['edge_id']==record.get('branch_edge')]
    if len(mains)!=2 or len(branches)!=1 or branches[0]in mains:
        raise ValueError('original main children and rim branch do not partition current T')
    branch=branches[0];point=[node['x'],node['y']];handles=[]
    for edge in mains:
        ray=by[edge['edge_id']];split=edge.get('split_source_edge',{})
        if (ray.get('scope')!='confirmed_native_circle_center_LINE_endpoint'
            or split.get('edge_id')!=record.get('main_source_edge')
            or split.get('source_graph_sha256')!=root.get('input_graph_sha256')
            or math.dist(ray['graph_segment'][0],point)>.05
            or ray.get('source_line_handle')not in edge.get('source_handles',[])):
            raise ValueError('native original main child/ray lineage differs')
        handles.append(ray['source_line_handle'])
    branch_ray=by[branch['edge_id']]
    if (len(set(handles))!=2 or branch_ray.get('scope')!='confirmed_native_circle_rim'
        or math.dist(branch_ray['graph_segment'][0],meta.get('source_rim',[]))>.05
        or branch.get('source_user_circle_connection')!=meta
        or branch_ray.get('source_line_handle')not in branch.get('source_handles',[])):
        raise ValueError('native center-arm main and circle-rim branch distinction differs')
    return dict(through=sorted(e['edge_id']for e in mains),branch=branch['edge_id'],source_T_proof=copy.deepcopy(proof),
        role_basis=BASIS,geometric_opposing_pair_preserved=copy.deepcopy(geometric_role['through']),
        original_main_source_edge=record['main_source_edge'],physical_flow_direction_inferred=False)


def roles(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    # Keep all original graph/source/ray/seed validation, including the native
    # T shape check. Its geometric candidate values are not used by the caller.
    geometric=geometric_infer(graph,seeds,verified_edges,junctions,source_hash,graph_hash)
    selected=copy.deepcopy(geometric['roles'])
    for nid,proof in junctions.items():
        if proof.get('status')==STATUS:
            selected[nid]=native_main_role(graph,nid,proof,selected[nid])
    return dict(roles=selected)


def infer(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    namespace=dict(original_infer.__globals__);namespace['through_infer']=roles
    reader=types.FunctionType(original_infer.__code__,namespace,original_infer.__name__)
    result=reader(graph,seeds,verified_edges,junctions,source_hash,graph_hash)
    result['native_main_continuity_nodes']=sorted(nid for nid,role in result['roles'].items()if role.get('role_basis')==BASIS)
    result['native_ray_directions_or_graph_geometry_changed']=False
    return result
