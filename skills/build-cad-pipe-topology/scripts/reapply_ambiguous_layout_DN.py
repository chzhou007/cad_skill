"""Feed ambiguous pending captions to the original independent layout owner."""
import argparse, copy, csv, importlib
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from axis_vertical_DN_batch import projection
from pipe_annotation_attributes import source_texts, direct_diameters, recognize_f_leaders
from native_paired_caption_geometry import collect as paired_captions
from native_repeated_branch_DN_layout import collect as repeated_reader
from axis_local_DN_segment_domains import locate
from axis_unbranched_vertical_DN import source_key, chain_evidence, annotation_index
from axis_omission_vertical_DN import owned_annotation_guard
from native_air_vent_attribute_items import collect as normalized_items
from reapply_modelspace_pair_main_DN import verify_output as parent_owner

MODE = 'inherited_ambiguous_native_layout_vertical_DN_v1'
DIRECT = 'original_repeated_layout_owner_for_ambiguous_caption'
BEND = 'original_repeated_layout_DN_and_source_two_arm_bends'


def discover(doc, graph, route, parent, source_hash):
    private, index, _, _ = projection(graph, route)
    texts = source_texts(doc, 'axis', source_hash)
    layers = {t['layer'] for t in texts}
    excluded = {t['handle'] for f in recognize_f_leaders(doc, texts, [], graph['edges'], layers) for t in f['texts']}
    excluded |= set(paired_captions(doc)['F_owned_texts'])
    _, ambiguous = direct_diameters(texts, private['edges'], {t['id'] for t in texts if t['handle'] in excluded}, layers)
    pending = {source_key(p) for p in parent['pending']
               if p['original_reason'] == 'ambiguous_native_text_projection_requires_ownership_rule'}
    rows = []
    for row in ambiguous:
        targets = sorted({source_key(index[e]) for e in row['candidate_edge_ids']
                          if source_key(index[e]) in pending})
        if targets and row['text']['handle'] not in excluded:
            rows.append(dict(text_handle=row['text']['handle'], pending_candidate_domains=targets,
                             original_ambiguous_projection=copy.deepcopy(row)))
    return dict(records=rows, F_owned_text_handles=sorted(excluded),
                complete_ambiguous_pending_domains=sorted(pending), thresholds_changed=False)


def compose(doc, graph, route, parent, items, sh, gh):
    before = encode(graph), encode(route), encode(parent)
    discovery = discover(doc, graph, route, parent, sh)
    handles = [r['text_handle'] for r in discovery['records']]
    if not handles or len(handles) != len(set(handles)):
        raise ValueError('nonempty complete ambiguous caption cohort required')
    # All targets are excluded together from controls; no per-target retry can
    # accidentally train on another unresolved target in this same cohort.
    owners = repeated_reader(doc, graph, handles, sh, gh)
    domains = locate(graph, owners, sh, gh)
    by_owner = {r['source_text']['handle']: r for r in owners['records']}
    pending = {source_key(p): p for p in parent['pending']}
    scopes = {source_key(s): s for s in route['records']}
    edges = {e['edge_id']: e for e in graph['edges']}
    if len(pending) != len(parent['pending']) or len(scopes) != len(route['records']):
        raise ValueError('duplicate current source domains')
    records = []
    for domain in domains['records']:
        segment = domain['segment']; k = (domain['edge_id'], segment['path_index'], segment['segment_index'])
        owner = by_owner[domain['text_handle']]
        s = scopes[k]; binding = owner['native_binding']
        if (k not in pending or pending[k]['original_reason'] != 'ambiguous_native_text_projection_requires_ownership_rule'
                or s['direction_class'] != 'vertical' or s['native_source_status'] != 'single_source_line_covers'
                or segment['scope_points'] != s['scope_points'] or len(s['native_witnesses']) != 1
                or s['native_witnesses'][0]['source_handle'] != binding['root_handle']
                or s['native_witnesses'][0]['layer'] != binding['layer']):
            raise ValueError('original ambiguous vertical domain or source owner differs')
        if (len(set(owner['independent_control_roots'])) < 4
                or binding['root_handle'] in owner['independent_control_roots']
                or set(handles) & set(owner['independent_control_text_handles'])):
            raise ValueError('original independent control exclusion was not preserved')
        records.append(dict(edge_id=k[0], path_index=k[1], segment_index=k[2],
            scope_points=copy.deepcopy(s['scope_points']), system=s['system'], floor_start=s['floor_start'], floor_end=s['floor_end'],
            nominal_mm=owner['nominal_mm_candidate'], observations=[dict(source_text=owner['source_text'],
                nominal_mm=owner['nominal_mm_candidate'], native_evidence=copy.deepcopy(owner))],
            connection_rule=DIRECT, physical_length_mm=None, whole_edge_DN_assigned=False, human_accepted=False))
    index = annotation_index(doc, graph, sh); direct = []; held_direct = []
    for record in records:
        k = source_key(record)
        try:
            record['annotation_guard'] = owned_annotation_guard(doc, [record], [scopes[k]], index,
                sh, edges[k[0]], edges, by_owner)
            direct.append(record)
        except ValueError as exc:
            held_direct.append(dict(edge_id=k[0], path_index=k[1], segment_index=k[2], reason=str(exc)))
    records = copy.deepcopy(direct)
    keys = {source_key(r) for r in direct}
    held = []
    for k, old in pending.items():
        if k in keys or old['original_reason'] != 'no_qualified_axis_annotation_on_this_vertical_segment':
            continue
        seeds = [r for r in direct if r['edge_id'] == k[0] and r['path_index'] == k[1]]
        if not seeds: continue
        try:
            if len({r['nominal_mm'] for r in seeds}) != 1:
                raise ValueError('source transition on current branch remains unresolved')
            target = scopes[k]; edge = edges[k[0]]
            if target['direction_class'] != 'vertical': raise ValueError('original vertical scope required')
            seed = min(seeds, key=lambda r: abs(r['segment_index'] - k[2]))
            lo, hi = sorted((seed['segment_index'], k[2]))
            corridor = [scopes[k[0], k[1], i] for i in range(lo, hi + 1)]
            continuity = chain_evidence(corridor, edge.get('source_insert_handle'), items)
            guard = owned_annotation_guard(doc, seeds, corridor, index, sh, edge, edges, by_owner)
            records.append(dict(edge_id=k[0], path_index=k[1], segment_index=k[2], system=target['system'],
                scope_points=copy.deepcopy(target['scope_points']), floor_start=target['floor_start'], floor_end=target['floor_end'],
                nominal_mm=seed['nominal_mm'], seed_record=seed, continuity_evidence=continuity,
                annotation_guard=guard, connection_rule=BEND, physical_length_mm=None,
                whole_edge_DN_assigned=False, human_accepted=False))
        except ValueError as exc:
            held.append(dict(edge_id=k[0], path_index=k[1], segment_index=k[2], reason=str(exc)))
    added = {source_key(r) for r in records}
    if len(added) != len(records) or not added <= pending.keys():
        raise ValueError('new layout domains duplicate or escape current unknown population')
    if before != (encode(graph), encode(route), encode(parent)):
        raise ValueError('old graph, routing or known values mutated')
    return dict(mode=MODE, records=records, pending=[copy.deepcopy(p) for k,p in pending.items() if k not in added],
        discovery=discovery, original_layout_qualification=owners, original_segment_domains=domains,
        direct_held=held_direct, continuity_held=held, counts=dict(previous_known=parent['counts']['current_known'], screened_pending=len(pending),
            new_direct=len(direct), new_continuity=len(records)-len(direct), new_known=len(records),
            current_known=parent['counts']['current_known']+len(records), remaining_unknown=len(pending)-len(records)),
        complete_ambiguous_pending_population_screened=True, original_readers_and_thresholds_unchanged=True,
        all_target_texts_excluded_from_controls=True, graph_mutated=False, components_reassigned=False,
        horizontal_values_assigned=0, physical_lengths_assigned=0, whole_edge_DN_assigned=0, human_accepted=False)


def compute(manifest):
    ins = manifest['inputs']
    def checked():
        if any(sha(x['path']) != x['sha256'] for x in ins.values()): raise ValueError('fixed layout reapplication input changed')
    checked(); parent = parent_owner(Path(ins['parent_attribute_proof']['path']).parent)
    for k in ('axis_source','axis_graph','routing','canonical_components'):
        if ins[k] != parent['inputs'][k]: raise ValueError('original source ancestry differs')
    viewer = load(ins['parent_viewer_manifest']['path']); provider = load(ins['parent_provider']['path'])
    if (viewer['attributeValueContext']['axis_rule_vertical_DN']['all_current_vertical_domains'] != parent['counts']['current_known']
            or provider['counts']['all_current_vertical_DN_domains'] != parent['counts']['current_known']):
        raise ValueError('actual published parent and source counts differ')
    doc, preflight = read_source(ins['axis_source']['path']); graph = load(ins['axis_graph']['path']); route = load(ins['routing']['path'])
    with Path(ins['canonical_components']['path']).open(encoding='utf-8-sig', newline='') as f:
        components = list(csv.DictReader(f))
    items, normalization = normalized_items(doc, graph, components)
    result = compose(doc, graph, route, parent, items, ins['axis_source']['sha256'], ins['axis_graph']['sha256'])
    checked(); result.update(inputs=ins, source_preflight=preflight, inherited_air_vent_normalization=normalization, viewer_adoption_pending=True)
    return result


def implementations():
    names = ['native_repeated_branch_DN_layout','axis_local_DN_segment_domains','axis_vertical_DN_batch',
             'axis_unbranched_vertical_DN','axis_omission_vertical_DN','native_air_vent_attribute_items',
             'reapply_modelspace_pair_main_DN','pipe_annotation_attributes','source_readability']
    return dict(entry=sha(__file__), **{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest, output):
    output = Path(output)
    if output.exists(): raise FileExistsError(output)
    code = implementations(); result = compute(load(manifest))
    if code != implementations(): raise ValueError('source implementation changed')
    output.mkdir(parents=True); target = output/'ambiguous-layout-vertical-DN.json'; target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE, manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(target))))
    return result


def verify_output(output):
    output = Path(output); receipt = load(output/'receipt.json'); target = output/'ambiguous-layout-vertical-DN.json'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
            or sha(receipt['manifest']['path']) != receipt['manifest']['sha256'] or sha(target) != receipt['output_sha256']):
        raise ValueError('layout source receipt changed')
    fresh = compute(load(receipt['manifest']['path']))
    if encode(fresh) != target.read_bytes(): raise ValueError('independent layout replay differs')
    return fresh


def main():
    p = argparse.ArgumentParser()
    for k in ('manifest','output','verify-output'): p.add_argument('--'+k,type=Path)
    a = p.parse_args()
    if not a.verify_output and not (a.manifest and a.output): p.error('manifest and fresh output required')
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result = verify_output(a.verify_output) if a.verify_output else produce(a.manifest,a.output)
    print(encode(result['counts']).decode(),flush=True)


if __name__ == '__main__': main()
