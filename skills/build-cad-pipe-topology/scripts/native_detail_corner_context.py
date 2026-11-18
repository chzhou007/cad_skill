"""Read four-corner annotation context with unequal vertical frame clearance.

An independent mode: it neither relaxes exact-translation correspondence nor
assigns an interface, connection, pipe diameter, scale or physical length.
"""
import argparse
import math
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from native_line_path_evidence import LAYERS

MODE = 'native_detail_annotation_corner_context_v1'
TOL = .05


def rectangle(points):
    # Group coordinates by the declared native tolerance without rounding a
    # line into a new geometry. Every retained point is still the source WCS.
    axes = []
    for index in (0, 1):
        values = []
        for value in sorted(p[index] for p in points):
            if not values or abs(value - values[-1]) > TOL:
                values.append(value)
        if len(values) != 2 or values[1] - values[0] <= TOL:
            raise ValueError('Frame endpoints are not a nondegenerate rectangle')
        axes.append(values)
    corners = []
    for point in points:
        label = tuple(min(range(2), key=lambda i: abs(point[axis] - axes[axis][i])) for axis in (0, 1))
        if any(abs(point[axis] - axes[axis][label[axis]]) > TOL for axis in (0, 1)):
            raise ValueError('Source endpoint is outside a frame corner')
        corners.append(label)
    if set(corners) != {(0, 0), (0, 1), (1, 0), (1, 1)}:
        raise ValueError('Frame corners repeat or are incomplete')
    return [axes[0][0], axes[1][0], axes[0][1], axes[1][1]], corners


def collect(doc, graph, policy, source_hash, graph_hash):
    if (policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash
            or graph.get('metadata', {}).get('source_sha256') != source_hash):
        raise ValueError('Native frame source or graph binding changed')
    layer = policy.get('annotation_layer')
    allowed = policy.get('allowed_linetypes')
    if not isinstance(layer, str) or not layer or layer in LAYERS.values():
        raise ValueError('Annotation layer cannot be a hydraulic pipe layer')
    if not isinstance(allowed, list) or not allowed or any(not isinstance(t, str) or t != t.upper() for t in allowed):
        raise ValueError('Explicit native annotation linetypes required')
    specs = policy.get('frames')
    if not isinstance(specs, list) or not specs:
        raise ValueError('Explicit source frame scopes required')
    seen_ids, seen_handles, frames = set(), set(), []
    for spec in specs:
        identity, handles = spec.get('frame_id'), spec.get('line_handles')
        if not isinstance(identity, str) or not identity or identity in seen_ids:
            raise ValueError('Missing or repeated frame identity')
        seen_ids.add(identity)
        if not isinstance(handles, list) or len(handles) != 4 or len(set(handles)) != 4 or seen_handles.intersection(handles):
            raise ValueError('Four distinct unshared native corner lines required')
        seen_handles.update(handles)
        upper, lower, lines = [], [], []
        for handle in handles:
            line = doc.entitydb.get(handle)
            if (line is None or line not in doc.modelspace() or line.dxftype() != 'LINE'
                    or line.dxf.layer != layer or line.dxf.get('linetype', 'BYLAYER').upper() not in allowed):
                raise ValueError('Selected native annotation LINE or layer/linetype differs')
            a, b = list(line.dxf.start), list(line.dxf.end)
            if not all(math.isfinite(v) for p in (a, b) for v in p) or max(abs(a[2]), abs(b[2])) > TOL or abs(a[1] - b[1]) <= TOL:
                raise ValueError('Annotation corner needs distinct planar source endpoints')
            u, l = (a, b) if a[1] > b[1] else (b, a)
            upper.append(u)
            lower.append(l)
            lines.append(dict(handle=handle, native_start=a, native_end=b,
                upper_point=u, detail_point=l, offset=[u[i] - l[i] for i in (0, 1)]))
        ub, uc = rectangle(upper)
        lb, lc = rectangle(lower)
        if uc != lc or ub[1] <= lb[3] + TOL:
            raise ValueError('Crossed corners or overlapping drawing regions')
        dx = lines[0]['offset'][0]
        if any(abs(row['offset'][0] - dx) > TOL for row in lines):
            raise ValueError('Horizontal frame translation is not shared')
        offsets = [row['offset'][1] for row in lines]
        frames.append(dict(frame_id=identity, upper_bounds=ub, detail_bounds=lb,
            source_corner_lines=lines, horizontal_annotation_offset=dx,
            minimum_vertical_corner_offset=min(offsets), maximum_vertical_corner_offset=max(offsets),
            exact_vertical_translation=max(offsets) - min(offsets) <= TOL,
            annotation_clearance_difference=(lb[3] - lb[1]) - (ub[3] - ub[1]),
            interpretation='native_annotation_regions_only_not_pipe_correspondence_or_metric'))
    return dict(mode=MODE, status='native_corner_annotation_context_not_individual_mapping',
        source_sha256=source_hash, graph_sha256=graph_hash, frames=frames,
        graph_mutated=False, mapping_ready=False, connections_added=0, pipe_values_assigned=0,
        coordinate_offsets_are_physical_lengths=False, human_accepted=False, hil_ready=False)


def implementation_hashes():
    import inspect
    import confirm_crossview_paths
    import native_line_path_evidence
    return {str(Path(path).name): sha(path) for path in (
        __file__, inspect.getfile(read_source), confirm_crossview_paths.__file__, native_line_path_evidence.__file__)}


def compute(paths):
    doc, preflight = read_source(paths['source'])
    graph = load(paths['graph'])
    result = collect(doc, graph, load(paths['policy']), sha(paths['source']), sha(paths['graph']))
    result['source_preflight'] = preflight
    return result


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory / 'corner-context-receipt.json')
    if receipt.get('mode') != MODE or receipt.get('implementation_sha256') != implementation_hashes():
        raise ValueError('Native corner context implementation changed')
    if set(receipt['inputs']) != {'source', 'graph', 'policy'}:
        raise ValueError('Unsupported native corner context input scope')
    for record in receipt['inputs'].values():
        if sha(record['path']) != record['sha256']:
            raise ValueError('Native corner context input changed')
    paths = {key: record['path'] for key, record in receipt['inputs'].items()}
    result = compute(paths)
    if (encode(result) != (directory / 'corner-context.json').read_bytes()
            or sha(directory / 'corner-context.json') != receipt['output_sha256']):
        raise ValueError('Native corner context replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'graph', 'policy', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = {key: getattr(args, key).resolve() for key in ('source', 'graph', 'policy')}
    hashes = {key: sha(path) for key, path in paths.items()}
    result = compute(paths)
    if any(sha(path) != hashes[key] for key, path in paths.items()):
        raise ValueError('Inputs changed during native corner reading')
    args.output.mkdir(parents=True)
    (args.output / 'corner-context.json').write_bytes(encode(result))
    (args.output / 'corner-context-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={key: dict(path=str(path), sha256=hashes[key]) for key, path in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(args.output / 'corner-context.json'))))
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
