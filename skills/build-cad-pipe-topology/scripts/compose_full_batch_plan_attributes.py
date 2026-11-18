"""Formal native whole-axis attribute composition with inherited readers."""
import argparse,collections,copy,csv,importlib,sys
from pathlib import Path
_PIPELINE=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_PIPELINE)not in sys.path:sys.path.insert(0,str(_PIPELINE))
from confirm_crossview_paths import load,sha,encode
from apply_crossview_rule_batch import checked
from extend_native_main_chain_batch import verify_output as verify_batch
from verify_inherited_plan_DN_semantics import verify_output as verify_DN
from historical_parent_native_replay import preflight as parent_preflight,verifier_for
from native_exploded_caption_identity import migrate_components
from native_plan_projection_lengths import unit_evidence
from native_replay_session import verify_once
from source_readability import read_source
from inherited_batch_plan_metrics import extend as extend_metrics
from full_batch_axis_attribute_composition import append,restore,ROOT,FIELD,MODE

AUDIT='full-batch-plan-attribute-fusion-audit.json'


def components(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as stream:
        reader=csv.DictReader(stream);return reader.fieldnames,list(reader)


def compute(policy,announce=lambda x:None):
    paths={k:checked(v)for k,v in policy['inputs'].items()}
    metric_paths={f:checked(v)for f,v in policy['metric_policies'].items()}
    parent_skills=paths['historical_parent_overlay'].parent
    parent_preflight(paths['parent_graph'].parent,parent_skills)
    template=load(paths['inline_template_origin'])
    if template.get('confirmation_basis')!='source_geometry_calibrated'or not template.get('expert_evidence'):raise ValueError('preserved native inline origin required')
    announce('Replaying all576 current source correspondences and native identity')
    batch=verify_once(paths['batch_receipt'].parent,verify_batch)
    announce('Replaying complete629 current plan DN, ordered F, calibration and local topology owners')
    DN=verify_once(paths['DN_receipt'].parent,verify_DN)
    announce('Replaying the complete prior axis parent and every retained attribute')
    parent_audit=verify_once(paths['parent_graph'].parent,verifier_for(str(parent_skills)))
    if parent_audit['output_graph_sha256']!=sha(paths['parent_graph']):raise ValueError('prior complete axis parent changed')
    axis=load(paths['identity_graph']);before=load(paths['native_before_graph']);parent=load(paths['parent_graph'])
    if batch['identity_graph_sha256']!=sha(paths['identity_graph']):raise ValueError('current axis identity and batch differ')
    identity=axis.get('sourceExplodedCaptionIdentity',{})
    if (identity.get('parent_graph_sha256')!=sha(paths['native_before_graph'])or identity.get('source_sha256')!=sha(paths['axis_source'])
        or identity.get('human_accepted')is not False):raise ValueError('native identity source or permutation differs')
    aliases=identity['aliases'];old_fields,old_rows=components(paths['parent_components']);new_fields,new_rows=components(paths['identity_components'])
    expected,changes=migrate_components(old_rows,aliases)
    if expected!=new_rows:raise ValueError('current canonical components do not preserve prior physical instances and pipe assignments')
    dn_manifest=load(checked(load(paths['DN_receipt'])['manifest']));plans={};metrics={};preflight={};locals_={}
    if set(metric_paths)!=set(DN['floors']):raise ValueError('complete local plan metric policies required')
    for item in dn_manifest['plans']:
        floor=str(item['floor']);local={k:checked(v)for k,v in item['inputs'].items()}
        graph=load(local['graph']);doc,preflight[floor]=read_source(local['source']);plans[floor]=graph;locals_[floor]=item['inputs']
        if DN['floors'][floor]['graph_sha256']!=sha(local['graph']):raise ValueError('plan DN topology scope differs from current mapping')
        units=unit_evidence(doc,load(metric_paths[floor]));_,instances=components(local['devices'])
        metrics[floor]=extend_metrics(doc,graph,instances,batch['floors'][floor]['records'],batch['metrics'][floor],units,
            dict(source_sha256=sha(local['source']),graph_sha256=sha(local['graph']),inventory_sha256=sha(local['devices'])),template)
        announce(f'{floor}F current metrics: {metrics[floor]["prior_metric_scopes_retained"]} retained, {metrics[floor]["additional_metric_scopes"]} inherited inline/crossover scopes recovered')
    recovered={r['mapping_id']:r for data in metrics.values()for r in data['records']if r['reader']in ('inherited_inline_pipe_XY','inherited_native_crossover_pipe_XY')}
    hashes=dict(identity_graph=sha(paths['identity_graph']),axis_source=sha(paths['axis_source']),mapping_receipt=sha(paths['batch_receipt']),DN_receipt=sha(paths['DN_receipt']),
        parent_graph=sha(paths['parent_graph']),plan_graphs={f:data['graph']['sha256']for f,data in locals_.items()},plan_sources={f:data['source']['sha256']for f,data in locals_.items()})
    result=append(parent,before,axis,aliases,batch,plans,DN,recovered,policy['isometric_horizontal_directions_degrees'],hashes)
    for spec in policy['inputs'].values():checked(spec)
    for spec in policy['metric_policies'].values():checked(spec)
    stage=result[ROOT];rows=stage['records']
    return result,dict(stage=stage,parent_graph=copy.deepcopy(policy['inputs']['parent_graph']),verified_complete_parent=parent_audit,
        native_local_graph=copy.deepcopy(policy['inputs']['native_before_graph']),current_native_identity_graph=copy.deepcopy(policy['inputs']['identity_graph']),
        source_preflight=preflight,metric_results=metrics,source_plan_inputs=locals_,component_identity_migration=changes,
        summary=dict(total_axis_edges=len(result['edges']),current_axis_scope_edges=stage['current_axis_edge_scopes'],
            current_plan_DN_scope_edges=sum(len(r['iso_edges'])for r in rows if r['plan_drawn_nominal_mm']is not None),
            current_plan_metric_scope_edges=sum(len(r['iso_edges'])for r in rows if r['horizontal_projection']),
            current_whole_horizontal_DN_and_centerline_edges=sum(len(r['iso_edges'])for r in rows if r['whole_axis_nominal_mm']is not None and r['complete_horizontal_centerline_route_mm']is not None),
            inherited_metric_groups=len(recovered)),old_attributes_exactly_restorable=True,human_accepted=False,hil_ready=False)


def implementation_hashes():
    names=('full_batch_axis_attribute_composition','inherited_batch_plan_metrics','extend_native_main_chain_batch','rebuild_inherited_full_plan_DN','verify_inherited_plan_DN_semantics','historical_parent_native_replay',
        'adopt_current_named_prefix_evidence','native_exploded_caption_identity','native_plan_projection_lengths','native_inline_joint_path_coverage',
        'anchored_floor_main_plan_attributes','inherited_circle_branch_inventory','source_readability')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))


def verify_output(directory):
    directory=Path(directory);audit=load(directory/AUDIT)
    if audit['mode']!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('complete batch fusion implementation changed')
    policy=load(checked(audit['policy']));graph,proof=compute(policy)
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes()or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256']or any(audit.get(k)!=v for k,v in proof.items()):
        raise ValueError('complete batch attribute independent native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=checked(policy['inputs']['identity_components']).read_bytes():raise ValueError('composed canonical component inventory changed')
    return audit


def produce(policy_path,output,announce=lambda x:None):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    policy=load(policy_path);graph,proof=compute(policy,announce);output.mkdir(parents=True)
    target=output/'graph_with_edges.json';target.write_bytes(encode(graph))
    (output/'edge_device_instances.csv').write_bytes(checked(policy['inputs']['identity_components']).read_bytes())
    parent=checked(policy['inputs']['parent_graph']).parent/'source-comparison-gate.json'
    (output/'source-comparison-gate.json').write_bytes(parent.read_bytes())
    (output/AUDIT).write_bytes(encode(dict(proof,mode=MODE,policy=dict(path=str(Path(policy_path).resolve()),sha256=sha(policy_path)),
        implementation_sha256=implementation_hashes(),output_graph_sha256=sha(target))))
    return proof


def main():
    p=argparse.ArgumentParser();p.add_argument('--policy',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.policy or a.output:p.error('verification cannot replace dependencies')
        print(verify_output(a.verify_output)['summary']);return
    if not a.policy or not a.output:p.error('fixed policy and new output required')
    print(produce(a.policy,a.output,lambda s:print(s,flush=True))['summary'],flush=True)


if __name__=='__main__':main()
