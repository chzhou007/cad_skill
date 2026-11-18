"""Requalify current native endpoint mappings after candidate ring partitions."""
import argparse,copy,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require
from reviewed_ring_partition_candidates import verify_output as verify_partition
from reapply_reviewed_ring_crossview_DN import select_scopes
from source_readability import read_source
from source_stable_junction_reapplication import prepare
from batch_native_path_coverage import collect as coverage
from crossview_equipment_branch_inventory import native_tee

MODE='native_reviewed_candidate_ring_existing_crossview_DN_v1'


def qualified_basis(inputs):
    """Use the owner which actually produced the current junction identities.

    The complete complementary owner already replays its predecessor in the
    predecessor's frozen runtime. A stale metadata parent is not this basis.
    """
    from rebuild_complementary_anchor_chains import verify_output as original_owner
    _,provider=original_owner(Path(inputs['mapping_basis_provider']['path']).parent)
    require(encode(provider)==Path(inputs['mapping_basis_provider']['path']).read_bytes(),
        'original complete mapping basis differs')
    return provider


def endpoint_identity(plan_edge,axis_edge,mapping):
    expected=[mapping.get(plan_edge[k]) for k in ('start_node_id','end_node_id')]
    actual=[axis_edge[k] for k in ('start_node_id','end_node_id')]
    require(None not in expected and len(set(expected))==2 and set(expected)==set(actual),
            'existing independent endpoint identities do not match')
    return dict(plan_nodes=[plan_edge[k] for k in ('start_node_id','end_node_id')],
                mapped_axis_nodes=expected,actual_axis_nodes=actual,orientation_reversed=expected!=actual)


def attribute_graph_binding(rendered,viewer_manifest,inputs):
    """Inherit the old exact-restoration component overlay, not a hash rebase."""
    context=viewer_manifest['attributeValueContext'];spec=inputs['attribute_context_graph']
    require(context['current_rendered_graph_sha256']==spec['sha256'],
        'attribute context graph source binding differs')
    prior=load(spec['path'])
    if inputs['rendered_graph']['sha256']==spec['sha256']:
        require(rendered==prior,'direct attribute graph payload differs')
        return dict(actual_viewer_graph=inputs['rendered_graph'],attribute_context_graph=spec,component_overlay=None)
    from fragment_component_index import restore,MODE as COMPONENT_MODE,AUDIT as COMPONENT_AUDIT
    from refresh_fragment_component_index import overlay
    proof_spec=inputs['component_overlay_proof'];proof=load(proof_spec['path'])
    require(proof['mode']==COMPONENT_MODE and proof['complete_current_parent_native_replayed'] is True
        and proof['new_correspondences_assigned']==0 and proof['physical_values_assigned']==0
        and proof['human_accepted'] is False and proof['audit']['pipe_graph_restoration_exact'] is True,
        'qualified original component overlay required')
    require(proof['inputs']['parent_graph']['sha256']==spec['sha256']
        and proof['rendered_graph_sha256']==inputs['rendered_graph']['sha256']
        and overlay(proof,proof_spec['path'])==viewer_manifest.get('componentFragmentOverlay')
        and rendered.get(COMPONENT_AUDIT)==proof['audit'] and restore(rendered)==prior,
        'component overlay does not restore the exact attribute graph')
    return dict(actual_viewer_graph=inputs['rendered_graph'],attribute_context_graph=spec,
                component_overlay=proof_spec,pipe_graph_restoration_exact=True)


def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        require(all(sha(v['path'])==v['sha256'] for v in inputs.values()),'candidate ring crossview input changed')
    checked();partition=verify_partition(Path(inputs['partition']['path']).parent);floor=manifest['floor']
    require(partition['floor']==floor and partition['inputs']['source']==inputs['plan_source']
        and partition['inputs']['graph']==inputs['plan_graph'],'partition source namespace differs')
    provider=load(inputs['provider']['path'])
    require(provider['inputs']['parent_provider']==inputs['provider_parent'],'original current provider parent differs')
    parent=qualified_basis(inputs)
    require(parent['ordinary_junction_mappings']==provider['ordinary_junction_mappings'],
        'DN-only provider stage changed original endpoint mappings')
    old={r['edge_id']:r for r in parent['records']}
    for key,ours in [('plan_source_'+str(floor),'plan_source'),('plan_graph_'+str(floor),'plan_graph'),
                     ('axis_source','axis_source'),('axis_graph','axis_graph')]:
        require(provider['inputs'][key]==inputs[ours],'provider uses another local source/graph namespace')
    plan,axis=load(inputs['plan_graph']['path']),load(inputs['axis_graph']['path'])
    rendered=load(inputs['rendered_graph']['path']);vm=load(inputs['viewer_manifest']['path'])
    attribute_binding=attribute_graph_binding(rendered,vm,inputs)
    mapping=provider['ordinary_junction_mappings'][str(floor)]
    source_rows={r['edge_id']:r for r in partition['records']}
    candidates,excluded=select_scopes(provider,axis,source_rows,floor)
    for candidate in candidates:
        require(candidate['original_observation'] in old[candidate['axis_edge_id']]['correspondence_observations'],
            'target correspondence lacks its original qualified owner')
    pe={e['edge_id']:e for e in plan['edges']};ae={e['edge_id']:e for e in axis['edges']};re={e['edge_id']:e for e in rendered['edges']}
    docs={};preflight={}
    for v in ('plan','axis'):docs[v],preflight[v]=read_source(inputs[v+'_source']['path'])
    reader=prepare(load(inputs['current_T_configuration']['path']),inputs['plan_source'],inputs['plan_graph'],plan)
    records=[]
    for candidate in candidates:
        eid,pid=candidate['axis_edge_id'],candidate['plan_edge_id'];edge=ae[eid];source=pe[pid]
        identity=endpoint_identity(source,edge,mapping)
        require(all(edge.get(k)==re[eid].get(k) for k in ('system','start_node_id','end_node_id','attribute_paths','floor_start','floor_end')),
            'rendered axis geometry differs from native local graph')
        native={}
        for v,graph,ids in [('plan',plan,[pid]),('axis',axis,[eid])]:
            sh,gh=inputs[v+'_source']['sha256'],inputs[v+'_graph']['sha256']
            cov=coverage(docs[v],graph,ids,sh,gh)
            require(not cov['unresolved'] and all(s['status']=='single_source_line_covers' for e in cov['edges'] for s in e['segments']),
                'mapped partition lacks unique source LINE coverage')
            target=source if v=='plan' else edge
            ts={n:(reader if v=='plan' else native_tee)(docs[v],graph,n,sh,gh)
                for n in (target['start_node_id'],target['end_node_id'])}
            native[v]=dict(native_path=cov,native_T=ts)
        require(candidate['classification']=='horizontal_only','candidate main adoption supports proven pure horizontal edges only')
        observation=candidate['original_observation'];value=source_rows[pid]['nominal_mm']
        records.append(dict(candidate,mapping_id=observation['mapping_id'],floor=floor,system=edge['system'],
            axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
            current_mapping=dict(mapping_id=observation['mapping_id'],floor=floor,system=edge['system'],plan_edges=[pid],iso_edges=[eid],
                kind='native_endpoint_bounded_existing_interval',native_endpoint_identity=identity),
            plan_DN_record=copy.deepcopy(source_rows[pid]),nominal_mm=value,whole_axis_nominal_mm=value,mixed_plan_value_scope=None,
            native_mapping_evidence=native,source_sha256=dict(plan=inputs['plan_source']['sha256'],iso=inputs['axis_source']['sha256']),
            graph_sha256=dict(plan=inputs['plan_graph']['sha256'],iso=inputs['axis_graph']['sha256']),
            DN_used_for_mapping=False,physical_length_mm=None,installed_whole_edge_length_mm=None,
            per_axis_horizontal_subsegment_allocation_inferred=False,vertical_DN_assigned=False,
            related_HIL_confirmation_inherited=False,human_accepted=False))
    mapped={r['plan_edge_id'] for r in records}
    require(set(partition['selected_main_scopes'])<=mapped,'a reviewed main arm lacks a qualified existing axis mapping')
    unmapped=[copy.deepcopy(r) for eid,r in source_rows.items() if eid not in mapped]
    checked()
    return dict(mode=MODE,inputs=inputs,records=records,unmapped_plan_DN_records=unmapped,
        excluded_other_drawing_ID_collisions=excluded,source_preflight=preflight,
        original_provider_owner_reexecuted=True,original_mapping_basis=inputs['mapping_basis_provider'],
        inherited_attribute_graph_binding=attribute_binding,existing_mappings_source_requalified=True,
        old_native_mapping_IDs_preserved=True,new_correspondences_assigned=0,source_graphs_mutated=False,
        DN_used_for_mapping=False,physical_lengths_assigned=0,vertical_values_assigned=0,
        counts=dict(source_DN_scopes=len(source_rows),qualified_axis_scopes=len(records),
            whole_horizontal_DN=len(records),unmapped_plan_branches=len(unmapped),other_drawing_ID_collisions_excluded=len(excluded)),
        human_accepted=False,whole_goal_complete=False)


def implementations():
    names=('reviewed_ring_partition_candidates','reapply_reviewed_ring_crossview_DN','rebuild_complementary_anchor_chains',
           'source_stable_junction_reapplication','batch_native_path_coverage','crossview_equipment_branch_inventory','source_readability',
           'fragment_component_index','refresh_fragment_component_index')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh candidate crossview output required');code=implementations();result=compute(load(manifest))
    require(code==implementations(),'candidate crossview code changed');output.mkdir(parents=True)
    p=output/'reviewed-candidate-ring-crossview-DN.json';p.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(p))))
    return result


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');p=output/'reviewed-candidate-ring-crossview-DN.json'
    require(r['mode']==MODE and r['implementation_sha256']==implementations() and sha(r['manifest']['path'])==r['manifest']['sha256']
        and sha(p)==r['output_sha256'],'candidate crossview receipt changed');fresh=compute(load(r['manifest']['path']))
    require(encode(fresh)==p.read_bytes(),'candidate crossview native replay differs');return fresh


def main():
    p=argparse.ArgumentParser()
    for k in ('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if not a.verify_output and not(a.manifest and a.output):p.error('manifest and fresh output required')
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify_output(a.verify_output) if a.verify_output else produce(a.manifest,a.output)
    print(encode(dict(mode=MODE,counts=result['counts'],length_values_assigned=0)).decode(),flush=True)


if __name__=='__main__':main()
