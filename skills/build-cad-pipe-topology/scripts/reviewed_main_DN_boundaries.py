"""Source-replayed expert DN extent boundaries; keep native labels and topology."""
import argparse
import copy
import importlib
from pathlib import Path
import re

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from reviewed_source_question import bind_question
from fresh_reviewed_plan_inventory import verify_local_plan
from anchored_floor_main_plan_attributes import observe_annotations, frontier_annotation_domain
from crossview_equipment_branch_inventory import native_tee
from native_path_coverage_audit import audit as audit_paths
from through_source_DN_inheritance import infer

MODE = 'explicit_reviewed_plan_main_DN_extent_boundaries_v1'
KEYS = ('source', 'graph', 'current_graph', 'attributes', 'attribute_verification', 'F_origin', 'reply', 'receipt', 'definitions', 'pair', 'overview')


def verify_attribute_report(paths, evidence):
    """The reviewed question pins the verification report, which pins its payload."""
    report = load(paths['attribute_verification'])
    if (evidence['current_native_attribute_report_sha256'] != sha(paths['attribute_verification'])
            or report.get('attribute_sha256') != sha(paths['attributes'])
            or Path(report.get('attribute_run', '')).resolve() != Path(paths['attributes']).resolve().parent):
        raise ValueError('reviewed attribute verification report or its payload differs')
    return report


def resolve(graph, seeds, scope, junctions, source_hash, graph_hash, reviewed_values, question_id):
    before = infer(graph, seeds, scope, junctions, source_hash, graph_hash)
    old = {r['edge_id']: r for r in before['records']}
    edges = {e['edge_id']: e for e in graph['edges']}
    seeded = {r['edge_id'] for r in seeds}
    if not reviewed_values or not set(reviewed_values) <= set(scope):
        raise ValueError('explicit reviewed DN edge scope required')
    added = []
    for eid, value in reviewed_values.items():
        edge = edges[eid]
        if (eid in seeded or old[eid]['status'] != 'conflict'
                or value not in {r['nominal_mm'] for r in old[eid]['lineage']}
                or isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0
                or not {edge['start_node_id'], edge['end_node_id']} <= set(junctions)):
            raise ValueError('reviewed resolution must bound an inherited conflict between source-checked Ts')
        added.append(dict(edge_id=eid, nominal_mm=value, evidence_id='review:' + question_id + ':' + eid))
    after = infer(graph, seeds + added, scope, junctions, source_hash, graph_hash)
    for row in after['records']:
        eid = row['edge_id']
        if eid not in reviewed_values:
            if row != old[eid]:
                raise ValueError('reviewed DN boundary would change an unreviewed pipe scope')
            continue
        if row['nominal_mm'] != reviewed_values[eid] or row['status'] != 'direct_plan_DN':
            raise ValueError('reviewed DN was not independently resolved by the inheritance kernel')
        row['kernel_status'] = row['status']
        row['status'] = 'explicit_reviewed_plan_DN_extent'
        row['reviewed_DN_extent'] = dict(question_id=question_id, nominal_mm=reviewed_values[eid],
            previous_candidates=copy.deepcopy(old[eid]['lineage']),
            boundary_T_nodes=[edges[eid]['start_node_id'], edges[eid]['end_node_id']],
            source_paths=copy.deepcopy(edges[eid]['attribute_paths']),
            evidence_kind='explicit_original_CAD_Pair_extent_confirmation_not_a_new_native_TEXT',
            physical_reducer_position=None, hydraulic_flow_inferred=False, human_accepted=False)
    return before, after


def compute(paths, policy):
    question = bind_question(paths, policy)
    match = re.fullmatch(r'两段均为DN(\d+)', question['answer']['decision'])
    if not match:
        raise ValueError('explicit complete paired DN extent answer required; partial replies remain unresolved')
    value = int(match.group(1))
    source_hash, reviewed_hash, current_hash = sha(paths['source']), sha(paths['graph']), sha(paths['current_graph'])
    doc, readable = read_source(paths['source'])
    verify_local_plan(Path(paths['current_graph']), 'reviewed_interface_owners')
    original, graph, attributes = load(paths['graph']), load(paths['current_graph']), load(paths['attributes'])
    evidence = question['source_evidence']
    verify_attribute_report(paths, evidence)
    if (attributes['graph_sha256']['plan'] != reviewed_hash
            or attributes['source_sha256']['plan'] != source_hash
            or graph['metadata']['source_sha256'] != source_hash):
        raise ValueError('reviewed DN report and native local graphs differ')
    old_edges = {e['edge_id']: e for e in original['edges']}
    edges = {e['edge_id']: e for e in graph['edges']}
    scope = {r['edge_id'] for r in attributes['DN_inheritance']['records']}
    if not scope <= set(old_edges) or any(edges.get(eid) != old_edges[eid] for eid in scope):
        raise ValueError('native DN scope changed during reviewed/current graph migration')
    nodes = {n['node_id']: n for n in graph['nodes']}
    selected = evidence['plan_edges']
    if (len(selected) != 2 or len(set(selected)) != 2
            or len(evidence['southern_T_nodes']) != 2 or len(evidence['northern_T_nodes']) != 2
            or {edges[eid]['system'] for eid in selected} != {'supply', 'return'}):
        raise ValueError('complete original paired pipe scope required')
    for i, eid in enumerate(selected):
        expected = {evidence['southern_T_nodes'][i], evidence['northern_T_nodes'][i]}
        if {edges[eid]['start_node_id'], edges[eid]['end_node_id']} != expected or len({nodes[n]['floor'] for n in expected}) != 1:
            raise ValueError('reviewed A-B pipe boundaries differ')
    origin = load(paths['F_origin'])
    if origin['source_sha256'] != source_hash or origin['graph_sha256'] != reviewed_hash:
        raise ValueError('original native F controls belong to a different reviewed graph')
    frames = [frame for group in origin.get('groups', []) for frame in group.get('line_F_frames', [])]
    observations, annotations = observe_annotations(doc, graph, scope, frames, source_hash, current_hash)
    original_seeds = [{k: row[k] for k in ('edge_id', 'nominal_mm', 'evidence_id')} for row in attributes['direct_observations']]
    seeds = [{k: row[k] for k in ('edge_id', 'nominal_mm', 'evidence_id')} for row in observations]
    if sorted(seeds, key=lambda r: r['evidence_id']) != sorted(original_seeds, key=lambda r: r['evidence_id']):
        raise ValueError('fresh native annotation inventory differs; resolve extraction before applying review')
    visible = {o['source_evidence']['source_text']['handle'] for o in observations}
    if not set(evidence['native_DN_handles']) <= visible:
        raise ValueError('both original native DN200/DN450 label pairs must remain visible')
    reading_graph = copy.deepcopy(graph)
    Ts = set(attributes['DN_inheritance']['roles'])
    frontier_proofs = []
    for frontier in attributes['annotation_feed_domains']:
        reading_graph, boundary = frontier_annotation_domain(reading_graph, frontier['edge_id'], Ts, observations)
        frontier_proofs.append(boundary)
    reading_hash = __import__('hashlib').sha256(encode(reading_graph)).hexdigest()
    junctions = {nid: native_tee(doc, reading_graph, nid, source_hash, reading_hash) for nid in sorted(Ts)}
    coverage = audit_paths(doc, graph, dict(source_sha256=source_hash, graph_sha256=current_hash, edges=selected), source_hash, current_hash)
    if any(s['status'] != 'single_source_line_covers' for row in coverage['edges'] for s in row['segments']):
        raise ValueError('reviewed A-B DN scope lacks unique complete native pipe coverage')
    before, after = resolve(reading_graph, seeds, scope, junctions, source_hash, reading_hash,
        {eid: value for eid in selected}, question['id'])
    historical = {r['edge_id']: r for r in attributes['DN_inheritance']['records']}
    if any((r['nominal_mm'], r['status']) != (historical[r['edge_id']]['nominal_mm'], historical[r['edge_id']]['status'])
           for r in before['records']):
        raise ValueError('fresh current-source DN baseline no longer reproduces original conflicts')
    return dict(mode=MODE, status='reviewed_plan_main_DN_extents_source_replayed_not_axis_fusion',
        source_sha256=source_hash, reviewed_graph_sha256=reviewed_hash, current_graph_sha256=current_hash,
        source_preflight=readable, reading_projection_sha256=reading_hash, frontier_domains=frontier_proofs,
        native_annotations=annotations, native_observations=observations, native_coverage=coverage,
        original_kernel_result=before, reviewed_kernel_result=after,
        records=[r for r in after['records'] if r['edge_id'] in selected], explicit_answer=question['answer'],
        question_id=question['id'], review_context_axis_edges=evidence['axis_edges'],
        current_axis_mapping_confirmed=False, physical_lengths_assigned=0, reducer_positions_created=0,
        local_graphs_mutated=False, human_accepted=False, hil_ready=False)


def implementation_hashes():
    names = ('reviewed_source_question', 'fresh_reviewed_plan_inventory', 'anchored_floor_main_plan_attributes',
        'through_source_DN_inheritance', 'plan_pipe_diameter_scopes', 'source_direct_dn_evidence',
        'native_line_f_diameter_evidence', 'crossview_equipment_branch_inventory', 'native_path_coverage_audit', 'source_readability')
    return dict({n: sha(importlib.import_module(n).__file__) for n in names}, entry=sha(__file__))


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory / 'reviewed-DN-boundary-receipt.json')
    if receipt['mode'] != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('reviewed DN boundary implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('reviewed DN boundary input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items() if k != 'policy'}
    result = compute(paths, load(receipt['inputs']['policy']['path']))
    if encode(result) != (directory / 'reviewed-DN-boundaries.json').read_bytes():
        raise ValueError('reviewed DN boundary native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in KEYS + ('policy', 'output', 'verify-output'):
        parser.add_argument('--' + key.replace('_', '-'), type=Path)
    args = parser.parse_args()
    if args.verify_output:
        if any(getattr(args, k) for k in KEYS + ('policy', 'output')):
            parser.error('verification cannot override original inputs')
        verify_output(args.verify_output)
        print('reviewed DN boundaries independently replayed', flush=True)
        return
    if not all(getattr(args, k) for k in KEYS + ('policy', 'output')):
        parser.error('all fixed source/review/current inputs and fresh output required')
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = {k: getattr(args, k) for k in KEYS}
    result = compute(paths, load(args.policy))
    args.output.mkdir(parents=True)
    target = args.output / 'reviewed-DN-boundaries.json'
    target.write_bytes(encode(result))
    paths['policy'] = args.policy
    (args.output / 'reviewed-DN-boundary-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(Path(v).resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False, hil_ready=False)))
    print(dict(reviewed_pipe_scopes=len(result['records']), physical_lengths_assigned=0, axis_values_fused=0), flush=True)


if __name__ == '__main__':
    main()
