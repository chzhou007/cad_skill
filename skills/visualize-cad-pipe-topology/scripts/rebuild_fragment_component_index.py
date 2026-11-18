"""Replay native fragment recovery and original named scopes before indexing."""
import argparse
import importlib
import sys
from pathlib import Path
for skill in ('build-cad-pipe-topology', 'orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/skill/'scripts'))
from confirm_crossview_paths import load, sha, encode
from rebuild_native_fragment_ball_contacts import verify_output as source_owner
from refresh_ambiguous_layout_DN import verify as parent_owner
from legacy_named_provider_inventory import extract, replay_floor
from source_readability import read_source
from fragment_component_index import classify, build, MODE


def implementations():
    names = ('fragment_component_index', 'rebuild_native_fragment_ball_contacts',
        'refresh_ambiguous_layout_DN', 'legacy_named_provider_inventory',
        'build_visualization', 'instance_geometry', 'source_evidence', 'anchor_bounded_main_paths')
    return dict(entry=sha(__file__), **{n: sha(importlib.import_module(n).__file__) for n in names})


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        if any(sha(v['path']) != v['sha256'] for v in inputs.values()):
            raise ValueError('fragment index input changed')
    checked()
    parent = Path(inputs['parent_manifest']['path']).parents[2]
    if parent_owner(parent)['artifact_replay'] != 'passed': raise ValueError('parent native replay failed')
    inventory = source_owner(Path(inputs['source_inventory']['path']).parent)
    if encode(inventory) != Path(inputs['source_inventory']['path']).read_bytes():
        raise ValueError('source inventory replay differs')
    provider = load(inputs['provider']['path']); graph = load(inputs['parent_graph']['path'])
    if provider['current_component_inventory']['rendered_graph_sha256'] != inputs['parent_graph']['sha256']:
        raise ValueError('complete current provider/rendered graph differs')
    for name, original in [('source', 'axis_source'), ('graph', 'axis_graph')]:
        if inventory['inputs'][name] != provider['inputs'][original]:
            raise ValueError('fragment and current provider native inputs differ')
    classifications = classify(provider, inventory)
    selected = {r['axis_edge_id'] for r in classifications}
    rows = [r for r in extract(graph) if r['axis_edge_id'] in selected]
    if len(rows) != len(selected) or any(r['provider'] != 'sourceExternalFeedPlanAttributes' for r in rows):
        raise ValueError('all affected named providers need their original scope owner')
    by_floor = {}
    for row in rows: by_floor.setdefault(row['floor'], []).append(row)
    replays = []
    for floor, scopes in sorted(by_floor.items()):
        original = provider['inputs']
        specs = {name: original[key] for name, key in [
            ('plan_graph', 'plan_graph_'+str(floor)), ('plan_source', 'plan_source_'+str(floor)),
            ('axis_graph', 'axis_graph'), ('axis_source', 'axis_source'),
            ('historical_plan_graph', 'historical_plan_graph_'+str(floor)),
            ('historical_axis_graph', 'historical_axis_graph'),
            ('plan_destination_policy', 'plan_destination_policy'),
            ('axis_destination_policy', 'axis_destination_policy')]}
        for spec in specs.values():
            if sha(spec['path']) != spec['sha256']: raise ValueError('named scope dependency changed')
        profile = provider['plan_exploded_component_reading_inventories'][str(floor)]['original_inventory']
        if sha(profile['path']) != profile['sha256']: raise ValueError('plan component source changed')
        replays.append(replay_floor((floor, specs, scopes, load(original['current_T_source_config']['path']))))
    doc, readability = read_source(inventory['inputs']['source']['path'])
    native = load(inventory['inputs']['graph']['path'])
    result, audit = build(graph, native, inventory, classifications, doc,
        inputs['parent_graph']['sha256'], inputs['source_inventory']['sha256'])
    checked()
    return result, dict(mode=MODE, inputs=inputs, audit=audit,
        classifications=classifications, native_named_scope_replays=replays,
        source_preflight=readability, all_original_component_rows_preserved=True,
        complete_current_parent_native_replayed=True, component_profile_conflicts_retained=True,
        pending_source_components=[r for r in classifications if not r['adopted']],
        new_correspondences_assigned=0, physical_values_assigned=0,
        human_accepted=False, whole_goal_complete=False)


def produce(manifest, output):
    output = Path(output)
    if output.exists(): raise FileExistsError(output)
    code = implementations(); graph, proof = compute(load(manifest))
    if code != implementations(): raise ValueError('fragment index implementation changed')
    output.mkdir(parents=True); target = output/'graph.json'; target.write_bytes(encode(graph))
    proof['rendered_graph_sha256'] = sha(target)
    record = output/'fragment-component-index.json'; record.write_bytes(encode(proof))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, proof_sha256=sha(record), graph_sha256=sha(target))))
    return proof


def verify_output(output):
    output = Path(output); receipt = load(output/'receipt.json')
    target = output/'graph.json'; record = output/'fragment-component-index.json'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
        or sha(receipt['manifest']['path']) != receipt['manifest']['sha256']
        or sha(target) != receipt['graph_sha256'] or sha(record) != receipt['proof_sha256']):
        raise ValueError('fragment index receipt differs')
    graph, proof = compute(load(receipt['manifest']['path'])); proof['rendered_graph_sha256'] = sha(target)
    if encode(graph) != target.read_bytes() or encode(proof) != record.read_bytes():
        raise ValueError('independent fragment index replay differs')
    return proof


def main():
    parser = argparse.ArgumentParser()
    for name in ('manifest', 'output', 'verify-output'): parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output: result = verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output: parser.error('manifest and fresh output required')
            result = produce(args.manifest, args.output)
    print(dict(adopted=result['audit']['added_count'], pending=len(result['pending_source_components'])), flush=True)


if __name__ == '__main__': main()
