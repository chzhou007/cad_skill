"""Reapply one verified source-detail owner without losing later viewer stages.

Receipt/Pair provenance may advance while the measured source semantics stay
identical. Such a replay retains review identity and all derived publications.
Changed existing semantics are deliberately rejected: their direction/frontier
owners must rebuild first. This module never imports a generated hil_server.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

MODE = 'current_viewer_reviewed_detail_feedback_reapplication_v1'
NATIVE_MODE = 'reviewed_native_source_detail_plan_metrics_v1'
EXTENSION_MODE = 'version_bound_reviewed_plan_omission_metric_extension_v1'
DECISION = '\u5e73\u9762\u7701\u7565\uff0c\u5b9e\u7269\u6309\u8f74\u6d4b\u4e24\u9600'
FIELDS = {'anchored_metric_mapping_id', 'anchored_metric_plan_edge',
          'anchored_metric_floor', 'anchored_metric_complete_centerline_mm',
          'anchored_metric_plan_source_sha256', 'anchored_metric_evidence_json'}
SKILLS = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def encode_manifest(value):
    # Existing JS readers expose JSON.stringify(record) as effective evidence
    # fields. Preserve every unrelated object's insertion order when rewriting
    # its containing manifest; canonical hash encoding must not rewrite that
    # reader-visible evidence. The strict field comparison remains unchanged.
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
            and not p.relative_to(root).as_posix().startswith('startup-logs/')}


def verified_native(proof_path):
    """Always rerun the native owner; a saved status or copied proof is insufficient."""
    proof_path = Path(proof_path).resolve()
    require(proof_path.name == 'reviewed-detail-plan-metrics.json',
            'canonical native output plus its receipt required')
    for skill in ('build-cad-pipe-topology', 'orchestrate-cad-drawing-pipeline'):
        path = str(SKILLS / skill / 'scripts')
        if path not in sys.path:
            sys.path.insert(0, path)
    from reviewed_source_detail_metrics import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(SKILLS):
        proof = verify_output(proof_path.parent)
    proof = json.loads(encode(proof))
    require(proof == load(proof_path), 'fresh native replay differs from requested proof')
    return proof


def semantic_record(record):
    """Only these explicitly version-bound receipt fields are non-semantic."""
    result = copy.deepcopy(record)
    resolution = result.get('source_detail_resolution', {})
    for key in ('answer_receipt_sha256', 'pair_sha256'):
        resolution.pop(key, None)
    for key in ('source_pair_sha256', 'updated_at'):
        resolution.get('answer', {}).pop(key, None)
    return result


def review_identity(manifest):
    # Same public identity contract as the shared server, without loading any
    # generated server module or executing viewer-specific Python.
    sources = manifest['sourceHashes']
    value = {'project': manifest['projectId'], 'sources': {
        k: sources.get(k) for k in ('graph', 'devices', 'ports', 'main_dxf', 'legend_dxf')}}
    if manifest.get('reviewContentHashes'):
        value['reviewContentHashes'] = manifest['reviewContentHashes']
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def actual_reader(bundle):
    """Run the facade actually imported by app.js and its current graph bridge."""
    bundle = Path(bundle).resolve()
    app = (bundle / 'public/app.js').read_text(encoding='utf-8')
    imports = re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]", app)
    require(len(imports) == 1, 'one actual local app attribute reader required')
    script = r"""import fs from 'node:fs';import path from 'node:path';
import {pathToFileURL} from 'node:url';import {createHash,webcrypto} from 'node:crypto';
globalThis.crypto??=webcrypto;
const p=process.argv[1],file=process.argv[2],read=x=>fs.readFileSync(path.join(p,'public',x),'utf8');
const m=JSON.parse(read('data/manifest.json')),raw=read('data/graph.json'),g=JSON.parse(raw),
hash=createHash('sha256').update(raw).digest('hex'),ctx=m.attributeValueContext;
if(m.reviewContentHashes?.viewer_graph!==hash)throw Error('current rendered graph binding differs');
let valid=ctx.current_rendered_graph_sha256===hash;
if(!valid&&fs.existsSync(path.join(p,'public/component-inventory-attribute-bridge.js'))){
 const b=await import(pathToFileURL(path.join(p,'public/component-inventory-attribute-bridge.js')));
 valid=b.componentInventoryGraphContext(ctx,hash,g.edges);
}
if(!valid&&fs.existsSync(path.join(p,'public/fragment-component-overlay.js'))){
 const b=await import(pathToFileURL(path.join(p,'public/fragment-component-overlay.js')));
 valid=await b.fragmentOverlayGraphContext(m,hash,g,async name=>{
  if(name!=='data/fragment-component-parent-graph.json')throw Error('unexpected bridge resource');
  return {ok:true,text:async()=>read(name)};
 });
}
if(!valid)throw Error('current app graph/context bridge rejected');
const a=await import(pathToFileURL(path.join(p,'public',file)));
console.log(JSON.stringify({facade:file,graph_context_verified:true,
 records:g.edges.map(e=>({edge_id:e.edge_id,values:a.crossViewAttributeCsvValues(e,ctx)}))}));"""
    run = subprocess.run(['node', '--input-type=module', '-e', script, str(bundle), imports[0]],
                         capture_output=True, text=True, encoding='utf-8',
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(run.returncode == 0, 'actual current attribute reader failed: ' + run.stderr)
    return json.loads(run.stdout)


def context_from(parent, proof, proof_path):
    """Validate the selected owner, replace in place, and conserve every other key."""
    parent = Path(parent)
    manifest = load(parent / 'public/data/manifest.json')
    context = manifest['attributeValueContext']
    root = context['anchored_plan_metrics']
    inputs, records = proof['inputs'], proof['records']
    require(proof['mode'] == NATIVE_MODE
            and all(proof.get(k) is True for k in (
                'reviewed_scope_native_T_paths_and_components_replayed', 'original_metric_readers_reused'))
            and all(proof.get(k) is False for k in (
                'source_graphs_mutated', 'component_owners_changed', 'human_accepted'))
            and all(proof.get(k) == 0 for k in (
                'DN_values_assigned', 'vertical_values_assigned', 'installed_lengths_assigned')),
            'scoped native reviewed metric proof required')
    require(all(sha(v['path']) == v['sha256'] for v in inputs.values()),
            'native proof input/source/reply changed')
    require(root['source_bindings']['native_axis_graph'] == inputs['axis_graph']['sha256']
            and manifest['sourceHashes']['main_dxf'] == inputs['axis_source']['sha256'],
            'reviewed metric belongs to another axis source or native graph')
    require(manifest['reviewContentHashes']['viewer_graph'] == sha(parent / 'public/data/graph.json'),
            'current rendered graph changed')
    require(records and len({r['source_scope_id'] for r in records}) == len(records)
            and len({r['axis_edge_id'] for r in records}) == len(records),
            'unique nonempty source scope/edge cohort required')
    question_ids = {r['source_detail_resolution']['question_id'] for r in records}
    require(len(question_ids) == 1, 'one source-detail question owner required')
    question = next(iter(question_ids))
    receipt = load(inputs['answer_receipt']['path'])
    answers = [r for r in receipt['records'] if r['question_id'] == question]
    require(receipt['mode'] == 'version_bound_current_review_answer_intake_v1' and len(answers) == 1,
            'one replayed, version-bound answer for this owner required')
    answer = answers[0]
    ev = answer['source_evidence']
    require(set(ev['related_current_axis_edges']) == {r['axis_edge_id'] for r in records}
            and set(ev['source_plan_edges']) == {r['plan_edge_id'] for r in records},
            'answer belongs to another source cohort')
    edges = {e['edge_id']: e for e in load(parent / 'public/data/graph.json')['edges']}
    for row in records:
        edge = edges.get(row['axis_edge_id'])
        resolution = row['source_detail_resolution']
        value = row['complete_horizontal_centerline_mm']
        require(edge is not None and row['system'] == edge['system']
                and row['axis_nodes'] == [edge['start_node_id'], edge['end_node_id']]
                and row['axis_attribute_paths'] == edge['attribute_paths']
                and all(row['floor'] == edge[k] for k in ('floor_start', 'floor_end')),
                'changed connectivity, source path, floor or system requires upstream rebuild')
        require(row['source_scope_id'] == 'REVIEWED-DETAIL-METRIC:' + row['mapping_id']
                and isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value > 0 and row['projection']['value_mm'] == value
                and row['nominal_mm'] is None and row['DN_evidence_changed'] is False
                and row['physical_installed_length_mm'] is None and row['net_pipe_cut_length_mm'] is None
                and row['related_HIL_confirmation_inherited'] is False,
                'invalid reviewed metric scope, value or unsupported DN/installed length')
        for field, name in (('axis_source_sha256', 'axis_source'),
                            ('native_axis_graph_sha256', 'axis_graph'),
                            ('plan_source_sha256', 'plan_source'), ('plan_graph_sha256', 'plan_graph')):
            require(row[field] == inputs[name]['sha256'], 'record source binding changed: ' + field)
        require(resolution['answer'] == answer['explicit_answer']
                and resolution['answer']['decision'] == DECISION
                and resolution['pair_sha256'] == answer['pair_sha256']
                and resolution['answer']['source_pair_sha256'] == answer['pair_sha256']
                and resolution['answer_receipt_sha256'] == inputs['answer_receipt']['sha256']
                and resolution['policy'] == 'plan_omits_axis_component_detail'
                and resolution['physical_ball_valve_count'] == 2
                and resolution['source_instances_retained'] is True
                and resolution['crossview_components_merged'] is False
                and resolution['plan_valve_positions_invented'] is False
                and row['component_profiles'] == {'plan': {'ball_valve': 1}, 'iso': {'ball_valve': 2}},
                'unsupported or mismatched source-detail answer')
    old = root['records']
    require(root['count'] == len(old)
            and len({r['source_scope_id'] for r in old}) == len(old)
            and len({r['axis_edge_id'] for r in old}) == len(old), 'existing metric inventory duplicated')
    extension = root.get('reviewed_detail_extension')
    targets = {r['source_scope_id']: r for r in records}
    old_selected = []
    if extension:
        require(extension['mode'] == EXTENSION_MODE and extension['question_id'] == question
                and set(extension['source_scope_ids']) == set(targets)
                and extension['count'] == len(targets)
                and len(extension['source_scope_ids']) == len(targets),
                'existing owner question or exact source scope differs')
        old_selected = [r for r in old if r['source_scope_id'] in targets]
        require(len(old_selected) == len(records), 'existing owner scope record missing')
        for row in old_selected:
            fresh = targets[row['source_scope_id']]
            require(row['axis_edge_id'] == fresh['axis_edge_id']
                    and row['source_detail_resolution']['question_id'] == question
                    and row['source_detail_resolution']['answer_receipt_sha256'] == extension['answer_receipt_sha256'],
                    'existing owner scope/edge/answer binding differs')
            require(semantic_record(row) == semantic_record(fresh),
                    'changed existing metric semantics requires directional/frontier rebuild')
    else:
        require(not any(r['axis_edge_id'] in {n['axis_edge_id'] for n in records}
                        or r['source_scope_id'] in targets for r in old),
                'new owner overlaps another metric owner')
        # No guessing at already frozen directional values or question queues.
        require(not manifest.get('directionalPipeAttributes')
                and not (parent / 'public/data/edge-review-queue.json').exists()
                and not (parent / 'public/data/directional-pipe-attributes.json').exists()
                and not (parent / 'public/data/graph-with-directional-attributes.json').exists()
                and not list((parent / 'public/data').glob('*frontier*.json')),
                'initial metric changes require directional/frontier rebuild in this viewer')
    result = copy.deepcopy(context)
    destination = result['anchored_plan_metrics']
    destination['records'] = [copy.deepcopy(targets.get(r['source_scope_id'], r)) for r in old]
    if not extension:
        destination['records'].extend(copy.deepcopy(records))
    destination['count'] = len(destination['records'])
    fresh_extension = copy.deepcopy(extension) if extension else dict(
        mode=EXTENSION_MODE, question_id=question, source_scope_ids=list(targets),
        count=len(records), human_accepted=False)
    fresh_extension.update(native_metric_proof_sha256=sha(proof_path),
                           answer_receipt_sha256=inputs['answer_receipt']['sha256'])
    destination['reviewed_detail_extension'] = fresh_extension
    return result, bool(extension), old_selected


def compare_readers(before, after, records, existing):
    require(before['facade'] == after['facade'], 'current app facade changed')
    old = {r['edge_id']: r['values'] for r in before['records']}
    new = {r['edge_id']: r['values'] for r in after['records']}
    targets = {r['axis_edge_id']: r for r in records}
    require(old.keys() == new.keys() and len(old) == len(before['records'])
            and len(new) == len(after['records']), 'actual reader edge population changed')
    changed = []
    for eid, values in old.items():
        current = new[eid]
        if eid not in targets:
            require(current == values, 'unrelated effective attribute changed: ' + eid)
            continue
        row = targets[eid]
        expected = dict(anchored_metric_mapping_id=row['source_scope_id'],
                        anchored_metric_plan_edge=row['plan_edge_id'], anchored_metric_floor=row['floor'],
                        anchored_metric_complete_centerline_mm=row['complete_horizontal_centerline_mm'],
                        anchored_metric_plan_source_sha256=row['plan_source_sha256'])
        require(all(current.get(k) == v for k, v in expected.items())
                and json.loads(current.get('anchored_metric_evidence_json', 'null')) == row,
                'actual current reader did not consume fresh source record: ' + eid)
        allowed = {'anchored_metric_evidence_json'} if existing else FIELDS
        require({k: v for k, v in values.items() if k not in allowed}
                == {k: v for k, v in current.items() if k not in allowed},
                'undeclared effective field change: ' + eid)
        if existing:
            require(semantic_record(json.loads(values['anchored_metric_evidence_json']))
                    == semantic_record(row), 'published prior source evidence differs')
        else:
            require(not (set(values) & FIELDS), 'initial metric would overwrite published attributes')
        if values != current:
            changed.append(eid)
    return dict(changed_evidence_edges=changed, checked_edges=len(old),
                owned_metric_records=len(records), new_complete_centerlines=0 if existing else len(records),
                effective_values_unchanged=existing, unrelated_fields_exact=True,
                new_DN_values=0, new_vertical_values=0, new_installed_lengths=0)


def refresh(parent, output, proof_path, port=10565):
    parent, output, proof_path = map(lambda p: Path(p).resolve(), (parent, output, proof_path))
    require(not output.exists() and output != parent and parent not in output.parents,
            'fresh external viewer output required')
    require(isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535,
            'valid local viewer port required')
    before_files = inventory(parent)
    proof = verified_native(proof_path)
    context, existing, old_selected = context_from(parent, proof, proof_path)
    original = load(parent / 'public/data/manifest.json')
    previous = actual_reader(parent)
    implementation = sha(__file__)
    token = digest({'parent_manifest': before_files['public/data/manifest.json'],
                    'proof': sha(proof_path), 'implementation': implementation})[:20]
    evidence = 'reviewed-detail-feedback/' + token
    require(not (parent / evidence).exists(), 'feedback evidence path already exists')
    shutil.copytree(parent, output, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    revised = copy.deepcopy(original)
    revised['attributeValueContext'] = context
    (output / 'public/data/manifest.json').write_bytes(encode_manifest(revised))
    current = actual_reader(output)
    change = compare_readers(previous, current, proof['records'], existing)
    revised['preferredPort'] = port
    if not existing:
        revised['reviewContentHashes'].update(attribute_value_context=digest(context),
                                             effective_edge_attributes=digest(current['records']))
    # Keep old semantic hash anchors on provenance-only replay; current exact
    # artifact hashes live in this independent, append-only publication lineage.
    lineage = dict(mode=MODE, receipt_path=evidence + '/receipt.json',
                   parent_bundle_id=original['bundleId'], native_proof_sha256=sha(proof_path),
                   answer_receipt_sha256=proof['inputs']['answer_receipt']['sha256'],
                   current_context_sha256=digest(context), effective_reader_sha256=digest(current),
                   review_identity_preserved=existing, human_accepted=False)
    if original.get('reviewedDetailFeedback'):
        lineage['previous'] = copy.deepcopy(original['reviewedDetailFeedback'])
    revised['reviewedDetailFeedback'] = lineage
    revised['bundleId'] = digest({'parent': original['bundleId'], 'lineage': lineage,
                                  'implementation': implementation, 'port': port})[:20]
    require((review_identity(revised) == review_identity(original)) == existing,
            'review identity invalidation boundary differs')
    (output / 'public/data/manifest.json').write_bytes(encode_manifest(revised))
    index = output / 'public/index.html'
    index.write_text(index.read_text(encoding='utf-8').replace(original['bundleId'], revised['bundleId']),
                     encoding='utf-8')
    folder = output / evidence
    folder.mkdir(parents=True)
    shutil.copy2(parent / 'public/data/manifest.json', folder / 'parent-manifest.json')
    shutil.copy2(proof_path, folder / 'native-proof.json')
    for filename, data in (('previous-owner-records.json', old_selected),
                           ('current-owner-records.json', proof['records']),
                           ('parent-effective.json', previous), ('current-effective.json', current)):
        (folder / filename).write_bytes(encode(data))
    require(inventory(parent) == before_files, 'parent viewer changed during publication')
    for name, old_hash in before_files.items():
        if name not in ('public/data/manifest.json', 'public/index.html'):
            require(sha(output / name) == old_hash, 'historical file or annotation changed: ' + name)
    audit = dict(mode=MODE, status='fresh_native_and_current_reader_verified_browser_pending',
                 parent=str(parent), parent_file_hashes=before_files, proof_path=str(proof_path),
                 proof_sha256=sha(proof_path), implementation_sha256=implementation,
                 parent_bundle_id=original['bundleId'], bundle_id=revised['bundleId'],
                 existing_owner=existing, delta=change, reader_facade=current['facade'],
                 review_identity=review_identity(revised),
                 review_identity_preserved=existing, all_annotation_history_preserved=True,
                 all_historical_files_preserved_except_manifest_and_index=True,
                 source_graphs_mutated=False, component_owners_changed=False,
                 human_accepted=False, complete_parent_pipeline_rerun_claimed=False,
                 output_hashes=inventory(output))
    (folder / 'receipt.json').write_bytes(encode(audit))
    return audit


def verify(output):
    output = Path(output).resolve()
    manifest = load(output / 'public/data/manifest.json')
    relative = manifest['reviewedDetailFeedback']['receipt_path']
    receipt_path = (output / relative).resolve()
    require(receipt_path.is_relative_to(output / 'reviewed-detail-feedback'), 'receipt outside owned lineage')
    audit = load(receipt_path)
    require(audit['mode'] == MODE and audit['implementation_sha256'] == sha(__file__)
            and audit['bundle_id'] == manifest['bundleId'], 'publication owner or identity changed')
    parent, proof_path = Path(audit['parent']), Path(audit['proof_path'])
    require(inventory(parent) == audit['parent_file_hashes'], 'parent history changed')
    require({k: v for k, v in inventory(output).items() if k != relative} == audit['output_hashes'],
            'published file or annotation history changed')
    proof = verified_native(proof_path)
    require(sha(proof_path) == audit['proof_sha256'], 'native proof changed')
    context, existing, old_selected = context_from(parent, proof, proof_path)
    require(context == manifest['attributeValueContext'] and existing == audit['existing_owner'],
            'current owner context differs from fresh native replay')
    before, after = actual_reader(parent), actual_reader(output)
    require(compare_readers(before, after, proof['records'], existing) == audit['delta'],
            'actual current reader replay differs')
    require(review_identity(manifest) == audit['review_identity']
            and (review_identity(manifest) == review_identity(load(parent / 'public/data/manifest.json'))) == existing,
            'review identity invalidation boundary changed')
    folder = receipt_path.parent
    for name, value in (('previous-owner-records.json', old_selected),
                        ('current-owner-records.json', proof['records']),
                        ('parent-effective.json', before), ('current-effective.json', after)):
        require(load(folder / name) == value, 'publication lineage evidence differs: ' + name)
    return dict(mode=MODE, status='fresh_native_and_current_reader_verified_browser_pending',
                artifact_replay='passed', bundle_id=manifest['bundleId'], delta=audit['delta'],
                proof_sha256=sha(proof_path), publication=dict(path=str(receipt_path), sha256=sha(receipt_path)),
                review_identity_preserved=existing, all_annotation_history_preserved=True,
                human_accepted=False, complete_parent_pipeline_rerun_claimed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'output', 'proof', 'verify-output', 'verification-output'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--port', type=int, default=10565)
    args = parser.parse_args()
    if args.verify_output:
        result = verify(args.verify_output)
        if args.verification_output:
            destination = args.verification_output.resolve()
            viewer = args.verify_output.resolve()
            require(not destination.exists() and not destination.is_relative_to(viewer),
                    'fresh external verification output required')
            destination.mkdir(parents=True)
            result = dict(result, status='passed', viewer=str(viewer),
                          verification_scope='fresh_native_replay_and_actual_current_JS_reader',
                          browser_review_performed=False)
            (destination / 'verification.json').write_bytes(encode(result))
    else:
        if args.verification_output:
            parser.error('--verification-output requires --verify-output')
        if not all((args.parent, args.output, args.proof)):
            parser.error('--parent, --output and --proof are required')
        result = refresh(args.parent, args.output, args.proof, args.port)
    print(json.dumps({k: v for k, v in result.items() if k not in ('parent_file_hashes', 'output_hashes')},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
