"""Append reviewed plan metrics to the existing context and complete provider."""
import argparse, collections, copy, hashlib, json, shutil, sys, zipfile
from pathlib import Path
for name in ('build-cad-pipe-topology', 'orchestrate-cad-drawing-pipeline'):
    directory = str(Path(__file__).resolve().parents[2] / name / 'scripts')
    if directory not in sys.path: sys.path.insert(0, directory)
import refresh_attribute_templates as base
from refresh_plan_crossover_centrelines import effective
from refresh_anchored_native_plan_metrics import delta
from reviewed_source_detail_metrics import verify_output, MODE as NATIVE_MODE
from reapply_anchored_plan_metrics import inventory_from
sha, load, encode = base.sha, base.load, base.encoded
MODE = 'qualified_reviewed_source_detail_metric_viewer_v1'
AUDIT = 'reviewed-detail-metric-refresh.json'
EVIDENCE = 'reviewed-detail-metric-refresh'
TEMPLATE = 'public/anchored-native-plan-metrics.js'


def context_from(parent, proof, path):
    manifest = load(Path(parent) / 'public/data/manifest.json')
    prior = manifest['attributeValueContext']
    if (proof['mode'] != NATIVE_MODE or proof['reviewed_scope_native_T_paths_and_components_replayed'] is not True
            or proof['original_metric_readers_reused'] is not True or proof['source_graphs_mutated'] is not False
            or proof['component_owners_changed'] is not False or proof['human_accepted'] is not False
            or any(proof.get(k) != 0 for k in ('DN_values_assigned', 'vertical_values_assigned', 'installed_lengths_assigned'))):
        raise ValueError('scoped native reviewed metric proof required')
    graph_path = Path(parent) / 'public/data/graph.json'
    if sha(graph_path) != prior['current_rendered_graph_sha256']:
        raise ValueError('rendered graph changed')
    root = prior['anchored_plan_metrics']
    if 'reviewed_detail_extension' in root: raise ValueError('reviewed metric extension already exists')
    if root['source_bindings']['native_axis_graph'] != proof['inputs']['axis_graph']['sha256']:
        raise ValueError('reviewed metric uses another local axis graph')
    edges = {e['edge_id']: e for e in load(graph_path)['edges']}
    old_edges = {r['axis_edge_id'] for r in root['records']}
    for r in proof['records']:
        edge = edges[r['axis_edge_id']]
        if (r['axis_edge_id'] in old_edges or r['system'] != edge['system']
                or r['axis_nodes'] != [edge['start_node_id'], edge['end_node_id']]
                or r['axis_attribute_paths'] != edge['attribute_paths']
                or r['nominal_mm'] is not None or r['DN_evidence_changed'] is not False
                or r['physical_installed_length_mm'] is not None or r['net_pipe_cut_length_mm'] is not None):
            raise ValueError('reviewed metric overlaps prior values or changes native identity')
    result = copy.deepcopy(prior)
    target = result['anchored_plan_metrics']
    target['records'].extend(copy.deepcopy(proof['records']))
    target['count'] = len(target['records'])
    records = proof['records']
    target['reviewed_detail_extension'] = dict(mode='version_bound_reviewed_plan_omission_metric_extension_v1',
        native_metric_proof_sha256=sha(path), answer_receipt_sha256=proof['inputs']['answer_receipt']['sha256'],
        question_id=records[0]['source_detail_resolution']['question_id'],
        source_scope_ids=[r['source_scope_id'] for r in records], count=len(records), human_accepted=False)
    return json.loads(encode(result))


def provider_from(proof, actual):
    old = load(proof['inputs']['current_provider']['path'])
    result = inventory_from(old, proof, actual)
    result['history_before_reviewed_detail_metric_mode'] = old['mode']
    result['mode'] = MODE
    result['anchored_metric_attribute_observations'] = copy.deepcopy(old.get('anchored_metric_attribute_observations', [])) + copy.deepcopy(proof['records'])
    result['reviewed_source_detail_resolutions'] = [r['source_detail_resolution'] for r in proof['records']]
    ids = {r['axis_edge_id'] for r in proof['records']}
    for row in result['remaining_horizontal_attributes']:
        if row['edge_id'] in ids:
            row['next_scope'] = 'known_reviewed_detail_metric_plan_DN_scope_unresolved'
            row['source_detail_answer_applied'] = True
    counts = dict(collections.Counter(r['next_scope'] for r in result['remaining_horizontal_attributes']))
    frontier = result['current_horizontal_frontier']
    frontier['records'] = result['remaining_horizontal_attributes']
    frontier['remaining_by_next_scope'] = counts
    # Some prior publishers retained an older nested frontier summary while
    # updating the authoritative complete-provider counters. Do not decrement
    # real published coverage when composing a later attribute-only stage.
    frontier['pure_horizontal_complete_centerline'] = old['counts']['pure_horizontal_complete_centerline'] + len(ids)
    frontier['pure_horizontal_complete'] = old['counts']['pure_horizontal_complete_DN_and_centerline'] + len(result['new_attribute_complete_axis_edges'])
    result['counts'].update(horizontal_next_scopes=counts,
        pure_horizontal_complete_centerline=frontier['pure_horizontal_complete_centerline'])
    return result


def refresh(parent, output, templates, proof_path, port):
    parent, output, templates, proof_path = map(lambda p: Path(p).resolve(), (parent, output, templates, proof_path))
    if output.exists() or output.with_suffix('.zip').exists(): raise FileExistsError(output)
    before = base.artifact_inventory(parent)
    proof = verify_output(proof_path.parent)
    context = context_from(parent, proof, proof_path)
    old = effective(parent)
    manifest = load(parent / 'public/data/manifest.json')
    shutil.copytree(parent, output, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(templates / TEMPLATE, output / TEMPLATE)
    revised = copy.deepcopy(manifest)
    revised['attributeValueContext'] = context
    (output / 'public/data/manifest.json').write_bytes(encode(revised))
    actual = effective(output)
    change = delta(old, actual, proof['records'])
    digest = hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort'] = port
    revised['templateHashes'][TEMPLATE] = sha(templates / TEMPLATE)
    revised['sourceHashes']['reviewed_source_detail_plan_metrics'] = sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,
        attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['reviewedDetailMetricRefresh'] = dict(mode=MODE, parent_bundle_id=manifest['bundleId'],
        native_proof_sha256=sha(proof_path), implementation_sha256=sha(__file__), human_confirmation_inherited=False)
    revised['bundleId'] = hashlib.sha256(encode(dict(parent=manifest['bundleId'], proof=sha(proof_path),
        effective=digest, template=sha(templates / TEMPLATE), implementation=sha(__file__), port=port))).hexdigest()[:20]
    (output / 'public/data/manifest.json').write_bytes(encode(revised))
    index = output / 'public/index.html'
    index.write_text(index.read_text(encoding='utf-8').replace(manifest['bundleId'], revised['bundleId']), encoding='utf-8')
    folder = output / EVIDENCE
    folder.mkdir()
    for name, data in [('provider-inventory.json', provider_from(proof, actual)), ('current-effective.json', actual)]:
        (folder / name).write_bytes(encode(data))
    shutil.copy2(proof_path, folder / 'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source = proof['inputs']['axis_source']['path']
    doc, readable = read_source(source)
    schema = validate_bundle(output, native_doc=doc, native_source_sha256=sha(source))
    (output / 'validation-report.json').write_bytes(encode(schema))
    quality = check(output, source)
    if schema['status'] != 'passed' or quality['machine_status'] != 'PASS':
        raise ValueError('native reviewed metric viewer gate failed')
    for name, digest_before in before.items():
        if name.startswith(('public/data/', 'annotations/')) and name != 'public/data/manifest.json':
            if sha(output / name) != digest_before: raise ValueError('source payload or annotations changed')
    if base.artifact_inventory(parent) != before: raise ValueError('parent viewer changed')
    audit = dict(mode=MODE, status='native_source_and_actual_reader_passed_browser_pending',
        parent=str(parent), parent_file_hashes=before, proof_path=str(proof_path), proof_sha256=sha(proof_path),
        bundle_id=revised['bundleId'], template_sha256=sha(templates / TEMPLATE), delta=change,
        source_preflight=readable, old_annotations_preserved=True, human_accepted=False)
    audit['output_hashes'] = base.artifact_inventory(output)
    (output / AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'), 'x', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(base.inventory(output)): z.write(output / name, output.name + '/' + name)
    return audit


def verify(output):
    output = Path(output)
    audit = load(output / AUDIT)
    parent, path = Path(audit['parent']), Path(audit['proof_path'])
    proof = verify_output(path.parent)
    manifest = load(output / 'public/data/manifest.json')
    if (audit['mode'] != MODE or manifest['bundleId'] != audit['bundle_id']
            or manifest['reviewedDetailMetricRefresh']['implementation_sha256'] != sha(__file__)
            or audit['proof_sha256'] != sha(path) or audit['template_sha256'] != sha(output / TEMPLATE)
            or base.artifact_inventory(parent) != audit['parent_file_hashes']
            or {n: h for n, h in base.artifact_inventory(output).items() if n != AUDIT} != audit['output_hashes']
            or context_from(parent, proof, path) != manifest['attributeValueContext']):
        raise ValueError('reviewed viewer context, parent or source changed')
    actual = effective(output)
    if (delta(effective(parent), actual, proof['records']) != audit['delta']
            or encode(provider_from(proof, actual)) != (output / EVIDENCE / 'provider-inventory.json').read_bytes()):
        raise ValueError('reviewed actual attributes or provider adoption differs')
    return dict(status='pending', artifact_replay='passed', bundle_id=manifest['bundleId'],
        delta=audit['delta'], human_accepted=False)


def main():
    p = argparse.ArgumentParser()
    for k in ('parent', 'output', 'templates', 'proof', 'verify-output'):
        p.add_argument('--' + k, type=Path)
    p.add_argument('--port', type=int)
    a = p.parse_args()
    result = verify(a.verify_output) if a.verify_output else refresh(a.parent, a.output, a.templates, a.proof, a.port)
    print(json.dumps({k: v for k, v in result.items() if k in ('status', 'artifact_replay', 'bundle_id', 'delta')}, ensure_ascii=False))


if __name__ == '__main__': main()
