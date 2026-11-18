"""Source-qualified child metrics for existing intensive-DN path groups."""
import copy,math,re,sys
from pathlib import Path
for p in(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts',Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'):
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha
from ordered_group_plan_lengths import verify_output
from native_replay_session import verify_once
MODE='qualified_ordered_group_child_plan_metrics_v1'

def collect(graph,rendered,proof,context,hashes):
    if any(not isinstance(v,str)or re.fullmatch('[0-9a-f]{64}',v)is None for v in hashes.values()):raise ValueError('ordered child source bindings missing')
    if proof['axis_source_graph_sha256']!=hashes['axis_graph']or proof['local_graphs_mutated']is not False or proof['proportional_length_allocation']is not False:raise ValueError('ordered metric source graph/method differs')
    scopes={r['mapping_id']:r for r in graph['sourceFullPlanBatchAttributes']['records']};raw={e['edge_id']:e for e in graph['edges']};view={e['edge_id']:e for e in rendered['edges']};uniform={g['mapping_id']:g for g in context['groups']};records=[];used=set()
    for group in proof['groups']:
        mid=group['mapping_id'];scope=scopes[mid];intensive=uniform[mid]
        if (scope['kind']!='native_main_chain_between_independent_junctions'or scope['human_accepted']is not False or scope['group_scope_not_allocated_to_child_edges']is not True
            or group['plan_graph_sha256']!=scope['graph_sha256']['plan']or group['source_sha256']!=scope['source_sha256']):raise ValueError('ordered source scope differs from qualified parent')
        if len(group['records'])!=len(scope['iso_edges'])or len(scope['iso_edges'])!=len(scope['plan_edges']):raise ValueError('ordered child coverage is incomplete')
        indices=set()
        for row in group['records']:
            i=row['index_in_group'];eid=row['axis_edge_id'];edge=raw[eid]
            if type(i)is not int or not 0<=i<len(scope['iso_edges'])or i in indices:raise ValueError('ordered child index is not a unique native interval')
            indices.add(i)
            if (eid in used or scope['iso_edges'][i]!=eid or scope['plan_edges'][i]!=row['plan_edge_id']or row['floor']!=scope['floor']or row['system']!=scope['system']
                or row['physical_installed_length_mm']is not None or row['axis_drawn_lengths_or_ratios_used']is not False or row['net_pipe_cut_length_mm']is not None):raise ValueError('ordered child source identity or physical scope differs')
            if any(view[eid].get(k)!=edge.get(k)for k in('attribute_paths','start_node_id','end_node_id','system'))or row['axis_attribute_paths']!=edge['attribute_paths']:raise ValueError('rendered ordered child path changed')
            metric=row['source_projection'];value=row['known_plan_pipe_XY_mm'];pieces=metric['pieces'];complete=row['complete_horizontal_run_centerline_mm'];unknown=row['unknown_inline_joint_handles']
            if (type(value)not in(int,float)or not math.isfinite(value)or value<=0 or metric['value_mm']!=value or not pieces
                or any(p['plan_edge']!=row['plan_edge_id']or not p.get('source_line_handle')or p['length_mm']<=0 for p in pieces)
                or abs(sum(p['length_mm']for p in pieces)-value)>.0001 or len(set(unknown))!=len(unknown)
                or complete is not None and(complete!=value or unknown)
                or metric['installed_whole_edge_length_mm']is not None or metric.get('joint_graphic_spans_added',False)is not False
                or row['human_accepted']is not False or row['child_equipment_or_external_interface_identity_inferred']is not False):raise ValueError('ordered child metric source pieces or unknown inline extents differ')
            used.add(eid);r={k:copy.deepcopy(v)for k,v in row.items()if k!='inline_source_proof'}
            r.update(nominal_mm=intensive['nominal_mm'],axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],plan_graph_sha256=scope['graph_sha256']['plan'],source_sha256=copy.deepcopy(scope['source_sha256']),
                mapping_receipt_sha256=scope['mapping_receipt_sha256'],related_HIL_confirmation_inherited=False);records.append(r)
    return dict(mode=MODE,records=records,pending=copy.deepcopy(proof['pending']),source_bindings=hashes,axis_edges=len(records),
        complete_run_children=sum(r['complete_horizontal_run_centerline_mm']is not None for r in records),partial_pipe_XY_children=sum(r['complete_horizontal_run_centerline_mm']is None for r in records),
        child_allocation_method='native_T_order_with_independent_outer_anchors',group_totals_copied_to_children=False,unknown_inline_lengths_assigned=0,human_accepted=False)

def from_artifact(graph_path,rendered_path,length_proof,parent_manifest,expected_graph_hash,context):
    paths=[Path(p)for p in(graph_path,rendered_path,length_proof,parent_manifest)];before={str(p):sha(p)for p in paths}
    if sha(graph_path)!=expected_graph_hash:raise ValueError('ordered metric qualified graph changed')
    fresh=verify_once(Path(length_proof).parent,verify_output)
    if fresh['qualified_parent_manifest_sha256']!=sha(parent_manifest):raise ValueError('ordered source proof belongs to another qualified parent')
    result=collect(load(graph_path),load(rendered_path),fresh,context,dict(axis_graph=expected_graph_hash,rendered_graph=sha(rendered_path),length_proof=sha(length_proof)))
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('ordered source inputs changed during replay')
    return result

def retained_member_bindings(path,context):
    """Keep a previously qualified member context only on unchanged inputs.

    This checks the original producer's source/graph/policy/output and current
    implementation bindings. It is qualified-artifact retention, not a claim
    that this job freshly reconstructed every old member and mapping.
    """
    from confirmed_member_plan_paths import implementation_hashes
    path=Path(path);receipt=load(path.parent/'receipt.json');m=receipt['manifest']
    if sha(path)!=context['member_plan_runs']['source_bindings']['member_proof']or sha(path)!=receipt['output_sha256']or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']:raise ValueError('retained member proof changed')
    inputs=load(m['path'])['inputs']
    if any(sha(v['path'])!=v['sha256']for v in inputs.values()):raise ValueError('retained member native input changed; reconstruct instead')
    return dict(proof_path=str(path.resolve()),proof_sha256=sha(path),receipt_sha256=sha(path.parent/'receipt.json'),input_bindings=inputs,source_reconstruction_performed=False)
