"""Fresh original-inventory and native-routing replay before fragment recovery."""
import argparse
import csv
import importlib
import sys
from pathlib import Path

for skill in ('orchestrate-cad-drawing-pipeline', 'visualize-cad-pipe-topology'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/skill/'scripts'))
from confirm_crossview_paths import load, sha, encode
from rebuild_native_ball_contact_owners import verify_output as inventory_owner
from axis_attribute_source_routing import verify_output as routing_owner
from source_readability import read_source
from native_fragment_ball_contacts import collect, MODE


def implementations():
    names = ('native_fragment_ball_contacts', 'native_ball_contact_reapplication',
        'native_flange_contact_ownership', 'native_line_path_evidence',
        'rebuild_native_ball_contact_owners', 'axis_attribute_source_routing', 'source_readability')
    return dict(entry=sha(__file__), **{n: sha(importlib.import_module(n).__file__) for n in names})


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        if any(sha(v['path']) != v['sha256'] for v in inputs.values()):
            raise ValueError('fragment contact input changed')
    checked()
    inventory = inventory_owner(Path(inputs['original_inventory']['path']).parent)
    routing = routing_owner(Path(inputs['routing']['path']).parent)
    if encode(inventory) != Path(inputs['original_inventory']['path']).read_bytes() or encode(routing) != Path(inputs['routing']['path']).read_bytes():
        raise ValueError('original inventory or complete routing replay differs')
    for name in ('source', 'graph'):
        if inputs[name] != inventory['inputs'][name] or inputs[name] != routing['inputs'][name]:
            raise ValueError('source/graph ancestry differs')
    doc, preflight = read_source(inputs['source']['path'])
    graph = load(inputs['graph']['path'])
    if graph['metadata']['source_sha256'] != inputs['source']['sha256']:
        raise ValueError('graph/source differs')
    result = collect(doc, graph, inventory['components'], routing)
    checked()
    return dict(result, inputs=inputs, original_complete_inventory_native_replayed=True,
        original_complete_routing_native_replayed=True, source_preflight=preflight,
        component_aware_correspondences_requalified=False, whole_goal_complete=False)


def produce(manifest, output):
    output = Path(output)
    if output.exists(): raise FileExistsError(output)
    code = implementations(); result = compute(load(manifest))
    if code != implementations(): raise ValueError('fragment owner changed during replay')
    output.mkdir(parents=True)
    target = output/'native-fragment-ball-contacts.json'; target.write_bytes(encode(result))
    table = output/'edge_device_instances.csv'
    with table.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['components'][0]))
        writer.writeheader(); writer.writerows(result['components'])
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(target), components_sha256=sha(table))))
    return result


def verify_output(output):
    output = Path(output); receipt = load(output/'receipt.json')
    target = output/'native-fragment-ball-contacts.json'; table = output/'edge_device_instances.csv'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
        or sha(receipt['manifest']['path']) != receipt['manifest']['sha256']
        or sha(target) != receipt['output_sha256'] or sha(table) != receipt['components_sha256']):
        raise ValueError('fragment contact receipt differs')
    fresh = compute(load(receipt['manifest']['path']))
    if encode(fresh) != target.read_bytes(): raise ValueError('native fragment reconstruction differs')
    with table.open(encoding='utf-8-sig', newline='') as stream:
        if list(csv.DictReader(stream)) != fresh['components']:
            raise ValueError('fragment component CSV differs')
    return fresh


def main():
    parser = argparse.ArgumentParser()
    for name in ('manifest', 'output', 'verify-output'): parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output: result = verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output: parser.error('fixed manifest and new output required')
            result = produce(args.manifest, args.output)
    print(encode(result['counts']).decode(), flush=True)


if __name__ == '__main__': main()
