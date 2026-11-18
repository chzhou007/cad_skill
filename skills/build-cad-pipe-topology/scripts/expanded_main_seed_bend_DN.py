"""Compose already-qualified source-LINE expansion with original bend reading."""
import argparse
import copy
import csv
import importlib
import sys
from pathlib import Path
for skill in ('orchestrate-cad-drawing-pipeline', 'visualize-cad-pipe-topology'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/skill/'scripts'))
from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from native_air_vent_attribute_items import collect as normalized_items
from axis_unbranched_vertical_DN import source_key, chain_evidence, annotation_index, annotation_guard
from native_line_path_evidence import LAYERS, _on

MODE = 'native_expanded_main_seed_two_arm_vertical_DN_v1'
RULE = 'original_source_LINE_expanded_main_seed_and_two_arm_bends'


def expanded_seed(doc, seed, scope):
    if (seed.get('direction_class') != 'horizontal'
        or seed.get('horizontal_final_value_assigned') is not False
        or seed['scope_points'] != scope['scope_points'] or seed['system'] != scope['system']):
        raise ValueError('original horizontal seed domain differs')
    expansion = seed['source_scope_expansion']; line = doc.entitydb.get(seed['source_line_handle'])
    if (line is None or line.dxftype() != 'LINE' or line not in doc.modelspace() or line.dxf.layer != LAYERS[scope['system']]
        or expansion['source_line_handle'] != line.dxf.handle
        or expansion['native_XYZ'] != [list(line.dxf.start), list(line.dxf.end)]
        or expansion.get('source') != 'same_original_LINE_through_current_native_Ts'
        or expansion.get('branch_DN_used_as_main_seed') is not False
        or expansion.get('physical_length_mm') is not None
        or not all(_on(p, *expansion['scope_points'], .05) for p in seed['scope_points'])):
        raise ValueError('independently replayed source-LINE expansion differs')


def compose(doc, graph, route, parent, seed_proof, items, source_hash):
    before = encode(graph), encode(route), encode(parent), encode(seed_proof)
    scopes = {source_key(s): s for s in route['records']}
    pending = {source_key(s): s for s in parent['pending']}
    edges = {e['edge_id']: e for e in graph['edges']}
    if len(scopes) != len(route['records']) or len(pending) != len(parent['pending']):
        raise ValueError('unique complete original domains required')
    expected = {(e['edge_id'], pi, si) for e in graph['edges']
        for pi,path in enumerate(e.get('attribute_paths', [])) for si in range(len(path)-1)}
    if set(scopes) != expected:
        raise ValueError('complete original route required')
    for key,s in scopes.items():
        edge = edges[key[0]]
        if s['system'] != edge['system'] or edge['attribute_paths'][key[1]][key[2]:key[2]+2] != s['scope_points']:
            raise ValueError('current graph and native route differ')
    if parent['counts']['current_known'] + len(pending) != sum(s['direction_class']=='vertical' for s in scopes.values()):
        raise ValueError('complete known/pending vertical population required')
    index = annotation_index(doc, graph, source_hash); records, diagnostics = [], []
    seeds = seed_proof['seeds']['records']
    for key, old in pending.items():
        target = scopes[key]
        try:
            if old['original_reason'] != 'no_qualified_axis_annotation_on_this_vertical_segment':
                raise ValueError('original source ambiguity retained')
            if target['direction_class'] != 'vertical': raise ValueError('original vertical target required')
            choices = [s for s in seeds if s.get('source_scope_expansion')
                and (s['edge_id'], s['path_index']) == key[:2]]
            if not choices: raise ValueError('no expanded native seed on the same original path')
            if len({s['nominal_mm'] for s in choices}) != 1:
                raise ValueError('conflicting expanded native seeds on the same original path')
            for seed in choices: expanded_seed(doc, seed, scopes[source_key(seed)])
            seed = min(choices, key=lambda s: (abs(s['segment_index']-key[2]), s['segment_index']))
            lo, hi = sorted((seed['segment_index'], key[2]))
            corridor = [scopes[key[0], key[1], n] for n in range(lo, hi+1)]
            edge = edges[key[0]]
            continuity = chain_evidence(corridor, edge.get('source_insert_handle'), items)
            guard = annotation_guard(doc, choices, corridor, index, source_hash, edge.get('source_insert_handle'))
            records.append(dict(edge_id=key[0], path_index=key[1], segment_index=key[2],
                system=target['system'], scope_points=copy.deepcopy(target['scope_points']),
                floor_start=target['floor_start'], floor_end=target['floor_end'], nominal_mm=seed['nominal_mm'],
                seed_record=copy.deepcopy(seed), all_qualified_same_path_seeds=copy.deepcopy(choices),
                continuity_evidence=continuity, annotation_guard=guard, connection_rule=RULE,
                native_witnesses=copy.deepcopy(target['native_witnesses']),
                physical_length_mm=None, whole_edge_DN_assigned=False, human_accepted=False))
        except ValueError as exc:
            diagnostics.append(dict(edge_id=key[0], path_index=key[1], segment_index=key[2], reason=str(exc)))
    added = {source_key(r) for r in records}
    if len(added) != len(records) or not added <= pending.keys(): raise ValueError('new domains escape pending cohort')
    if before != (encode(graph), encode(route), encode(parent), encode(seed_proof)):
        raise ValueError('inherited source evidence mutated')
    known = parent['counts']['current_known']
    return dict(mode=MODE, records=records,
        pending=[copy.deepcopy(s) for key,s in pending.items() if key not in added], diagnostics=diagnostics,
        counts=dict(previous_known=known, screened_pending=len(pending), new_known=len(records),
            current_known=known+len(records), remaining_unknown=len(pending)-len(records)),
        source_LINE_expansion_owner_replayed=True, original_two_arm_and_annotation_owners_reused=True,
        graph_mutated=False, components_reassigned=False, horizontal_values_assigned=0,
        whole_edge_DN_assigned=0, physical_lengths_assigned=0, human_accepted=False)


def compute(manifest):
    ins = manifest['inputs']
    def checked():
        if any(sha(s['path']) != s['sha256'] for s in ins.values()): raise ValueError('expanded seed inputs changed')
    checked()
    from refresh_fragment_component_index import verify as verify_parent_viewer
    parent_viewer = Path(ins['parent_viewer_manifest']['path']).parents[2]
    if verify_parent_viewer(parent_viewer)['artifact_replay'] != 'passed':
        raise ValueError('complete current parent native replay failed')
    # The complete viewer replay above re-executes the layout owner, which
    # re-executes and byte-compares the entire main seed owner. Read those exact
    # pinned bytes once instead of repeating the same expensive native subtree.
    parent = load(ins['known_vertical_proof']['path']); seeds = load(ins['expanded_seed_proof']['path'])
    if parent['inputs']['parent_attribute_proof'] != ins['expanded_seed_proof']:
        raise ValueError('expanded seeds differ from current native parent lineage')
    for name in ('axis_source','axis_graph','routing','canonical_components'):
        if ins[name] != parent['inputs'][name] or ins[name] != seeds['inputs'][name]:
            raise ValueError('native source ancestry differs')
    viewer = load(ins['parent_viewer_manifest']['path']); provider = load(ins['parent_provider']['path'])
    root = viewer['attributeValueContext']['axis_rule_vertical_DN']
    if (root['all_current_vertical_domains'] != parent['counts']['current_known']
        or root['source_bindings']['native_proof'] != ins['known_vertical_proof']['sha256']
        or provider['counts']['all_current_vertical_DN_domains'] != parent['counts']['current_known']):
        raise ValueError('published DN parent differs')
    doc, preflight = read_source(ins['axis_source']['path'])
    graph, route = load(ins['axis_graph']['path']), load(ins['routing']['path'])
    with Path(ins['canonical_components']['path']).open(encoding='utf-8-sig', newline='') as stream:
        components = list(csv.DictReader(stream))
    items, normalization = normalized_items(doc, graph, components)
    result = compose(doc, graph, route, parent, seeds, items, ins['axis_source']['sha256'])
    checked()
    return dict(result, inputs=ins, source_preflight=preflight,
        inherited_air_vent_normalization=normalization, complete_current_viewer_replayed=True,
        known_parent_and_seed_bytes_requalified_in_parent_replay=True, viewer_adoption_pending=True,
        whole_goal_complete=False)


def implementations():
    names=('axis_unbranched_vertical_DN','native_air_vent_attribute_items','reapply_modelspace_pair_main_DN',
        'refresh_fragment_component_index','pipe_annotation_attributes','source_readability')
    return dict(entry=sha(__file__), **{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest, output):
    output=Path(output)
    if output.exists(): raise FileExistsError(output)
    code=implementations();result=compute(load(manifest))
    if code!=implementations(): raise ValueError('source owner changed during replay')
    output.mkdir(parents=True);target=output/'expanded-main-seed-bend-DN.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(target))))
    return result


def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');target=output/'expanded-main-seed-bend-DN.json'
    if (rc['mode']!=MODE or rc['implementation_sha256']!=implementations()
        or sha(rc['manifest']['path'])!=rc['manifest']['sha256'] or sha(target)!=rc['output_sha256']):
        raise ValueError('expanded main/bend receipt differs')
    fresh=compute(load(rc['manifest']['path']))
    if encode(fresh)!=target.read_bytes(): raise ValueError('expanded main/bend native replay differs')
    return fresh


def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(encode(r['counts']).decode(),flush=True)


if __name__=='__main__':main()
