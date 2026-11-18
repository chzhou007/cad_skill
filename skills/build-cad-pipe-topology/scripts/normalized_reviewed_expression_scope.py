"""Re-run reviewed two-view ranges using inherited normalization at axis Ts."""
import argparse
import copy
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
import reviewed_expression_scope as original
import normalized_native_junction_evidence as normalized
from source_readability import read_source

MODE = 'reviewed_expression_scope_with_original_normalization_v1'


def compute(manifest):
    # The original owner still replays both views, source paths, independent
    # anchors and the actual expert reply. Its implementation remains unchanged.
    result = original.compute(manifest)
    inputs = manifest['inputs']
    doc, _ = read_source(inputs['iso_source']['path'])
    graph = load(inputs['iso_graph']['path'])
    context = normalized.prepare(doc, graph, inputs['iso_source']['sha256'],
                                 inputs['iso_graph']['sha256'], inputs['iso_normalization_audit'])
    for scope in result['records']:
        view = scope['views']['iso']
        previous = copy.deepcopy(view['junction_failures'])
        view['junctions'], view['junction_failures'] = {}, {}
        for nid in view['route']['nodes']:
            try:
                view['junctions'][nid] = normalized.collect(doc, graph, nid,
                    inputs['iso_source']['sha256'], inputs['iso_graph']['sha256'], context)
            except ValueError as exc:
                view['junction_failures'][nid] = str(exc)
        scope.update(original.qualify(scope['views'], scope['answer']))
        scope['prior_strict_axis_junction_failures'] = previous
        scope['normalized_axis_junctions'] = [nid for nid, proof in view['junctions'].items()
            if proof.get('status') == 'normalization_replayed_native_ray_evidence_unreviewed']
    result.update(mode=MODE, original_axis_normalization_replayed=True,
        accepted_scope_count=sum(r['status']=='native_bounded_range_correspondence' for r in result['records']),
        held_scope_count=sum(r['status']=='held_local_source_evidence' for r in result['records']))
    if any(sha(v['path']) != v['sha256'] for v in inputs.values()):
        raise ValueError('reviewed normalized expression input changed')
    return result


def implementations():
    return dict(entry=sha(__file__), original_scope=original.implementations(),
                normalization=normalized.implementations())


def produce(manifest, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    code = implementations(); result = compute(load(manifest))
    if implementations() != code:
        raise ValueError('normalized expression implementation changed')
    output.mkdir(parents=True)
    target = output/'reviewed-expression-scopes.json'; target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(target))))
    return result


def verify_output(output):
    output = Path(output); receipt = load(output/'receipt.json'); target = output/'reviewed-expression-scopes.json'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
            or sha(receipt['manifest']['path']) != receipt['manifest']['sha256']
            or sha(target) != receipt['output_sha256']):
        raise ValueError('normalized expression receipt changed')
    fresh = compute(load(receipt['manifest']['path']))
    if encode(fresh) != target.read_bytes():
        raise ValueError('normalized expression source replay differs')
    return fresh


def main():
    p = argparse.ArgumentParser()
    for name in ('manifest', 'output', 'verify-output'):
        p.add_argument('--'+name, type=Path)
    a = p.parse_args()
    if not a.verify_output and not (a.manifest and a.output):
        p.error('manifest and fresh output required')
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result = verify_output(a.verify_output) if a.verify_output else produce(a.manifest, a.output)
    print(encode(dict(mode=MODE, accepted_scopes=result['accepted_scope_count'],
        held_scopes=result['held_scope_count'], DN_values_assigned=0, length_values_assigned=0)).decode(), flush=True)


if __name__ == '__main__':
    main()
