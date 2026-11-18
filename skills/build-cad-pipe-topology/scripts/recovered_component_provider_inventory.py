"""Keep all pipe providers while adopting a native rendered component bridge."""
import argparse,copy,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
MODE='qualified_native_component_index_complete_provider_inventory_v1'


def inherit(original,proof,graph):
    if proof.get('complete_parent_and_native_inventory_replayed')is not True or proof.get('pipe_graph_restoration_exact')is not True or proof.get('new_correspondences_assigned')!=0 or proof.get('physical_parameters_assigned')!=0 or proof.get('human_accepted')is not False:raise ValueError('native recovered component index must replay without invented values')
    if len(graph['instances'])!=proof['audit']['output_instances']or graph['sourceRecoveredNativeComponentIndex']!=proof['audit']:raise ValueError('current rendered index differs from native component audit')
    for row in proof['affected_component_profiles']:
        if row['status']not in('current_native_component_profiles_agree','previous_unmatched_scope_retained')or row['new_correspondence']is not False:raise ValueError('changed component has an unresolved mapping conflict')
    result=copy.deepcopy(original);result.update(mode=MODE,current_component_inventory=dict(native_inventory=copy.deepcopy(proof['inputs']['native_inventory']),native_axis_graph=copy.deepcopy(proof['inputs']['native_axis_graph']),rendered_graph_sha256=proof['rendered_graph_sha256'],recovered_components_adopted=proof['component_rows_added'],unresolved_native_components=copy.deepcopy(proof['unresolved_native_components'])),all_prior_provider_observations_exact=True,all_prior_member_and_ordinary_junction_namespaces_exact=True,all_prior_attribute_frontiers_exact=True,current_rendered_component_profiles_requalified=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(rendered_component_instances=len(graph['instances']),newly_adopted_component_instances=proof['component_rows_added'],native_component_ownership_unresolved=len(proof['unresolved_native_components']))
    return result


def compute(manifest):
    from refresh_recovered_component_index import verify
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in inputs.items()):raise ValueError('recovered component provider input changed')
    checked();bundle=paths['viewer_manifest'].parents[2]
    if verify(bundle)['artifact_replay']!='passed':raise ValueError('current recovered index viewer did not replay')
    proof=load(paths['native_proof']);original=load(paths['original_inventory']);manifest_data=load(paths['viewer_manifest'])
    if proof['inputs']['parent_provider']!=inputs['original_inventory']or manifest_data['componentIndexRefresh']['native_proof_sha256']!=inputs['native_proof']['sha256']or sha(bundle/'public/data/graph.json')!=proof['rendered_graph_sha256']:raise ValueError('component provider native/viewer ancestry differs')
    result=inherit(original,proof,load(bundle/'public/data/graph.json'));checked();result.update(inputs=inputs,current_viewer_and_complete_original_inventory_replayed=True)
    return result


def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('refresh_recovered_component_index','rebuild_recovered_component_index','recovered_component_graph_bridge')})


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('component provider implementation changed')
    output.mkdir(parents=True);p=output/'provider-inventory.json';p.write_bytes(encode(r));(output/'horizontal-frontier.json').write_bytes(encode(r['current_horizontal_frontier']));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r


def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'provider-inventory.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('recovered component provider receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes()or encode(r['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('component provider independent replay differs')
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
