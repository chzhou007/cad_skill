"""Inherit named boundary/riser scopes omitted from an attribute-context inventory.

The source graph and rendered ancestor already contain these correspondences.
This adapter replays their current native scopes and keeps typed partial domains;
it does not complete pipe attributes or turn an interface into an ordinary T.
"""
import argparse, collections, copy, hashlib, importlib, json, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from batch_native_path_coverage import collect as coverage
from native_path_coverage_audit import audit
from native_line_path_evidence import _on
from native_external_pipe_destination import collect as plan_destination
from native_external_port_destination import collect as axis_destination
from native_current_junction_reader import make_reader
from crossview_equipment_branch_inventory import native_tee, index_graph

MODE = 'complete_legacy_named_boundary_and_riser_provider_inventory_v1'
ROOTS = ('sourceExternalFeedPlanAttributes', 'sourceNamedRiserPlanAttributeFusion',
         'sourceUpperFloorPlanSegmentAttributes', 'sourceLowerFloorPlanSegmentAttributes',
         'sourceNetworkNamedLowerPlanAttributes')
CORE = ('edge_id', 'start_node_id', 'end_node_id', 'system', 'floor_start', 'floor_end',
        'attribute_paths', 'source_insert_handle', 'connection_mode', 'start_port_id', 'end_port_id')


def require(value, message):
    if not value:
        raise ValueError(message)


def extract(rendered):
    by = {e['edge_id']: e for e in rendered['edges']}
    require(len(by) == len(rendered['edges']), 'duplicate rendered edge')
    rows = []
    for root in ROOTS:
        stage = rendered.get(root)
        require(isinstance(stage, dict) and stage.get('human_accepted') is False,
                'missing qualified legacy provider: ' + root)
        for record in stage['records']:
            eid = record.get('axis_edge', record.get('edge_id', (record.get('iso_edges') or [None])[0]))
            require(eid in by, 'legacy axis edge missing')
            edge = by[eid]
            if root == 'sourceNamedRiserPlanAttributeFusion':
                detail = edge.get('cross_view_attributes', {})
                require(detail.get('mapping_id') == record['mapping_id']
                        and detail.get('mapping_basis') == 'native_named_riser_and_independent_equipment_service'
                        and detail.get('human_accepted') is False,
                        'legacy named interface mapping differs')
                paths = {p['edge_id']: p['scope_paths'] for p in detail['diameter']['plan_drawn_values']}
                axis_paths = edge['attribute_paths']
                source = detail['source_hashes']
                graph_hash = dict(plan=source['plan_graph'], iso=source['local_iso_graph'])
                sources = dict(plan=source['plan'], iso=source['isometric'])
                pairs = [(detail['named_riser_interface_context']['plan_equipment_main_T'],
                          detail['named_riser_interface_context']['iso_equipment_main_T'])]
                domain = 'named_riser_interface_path'
                extent = 'logical_named_interface_path_physical_connector_unknown'
            else:
                detail = record
                require(len(detail['plan_edges']) == 1, 'one native legacy plan interval required')
                paths = {detail['plan_edges'][0]: detail['diameter_evidence']['scope_paths']}
                axis_paths = detail.get('scope_paths') or [detail['scope_points']]
                sources, graph_hash = detail['source_sha256'], detail['local_graph_sha256']
                pairs = []
                if root == 'sourceExternalFeedPlanAttributes':
                    domain = 'separate_named_external_port'
                    extent = 'native_pipe_fragments_excluding_marker_and_inline_interiors'
                    require(detail.get('external_ports_connected_to_each_other') is False
                            and detail.get('whole_axis_edge_DN_selected') is False
                            and detail.get('physical_external_connection_verified') is False,
                            'external legacy domain claims a physical connection or scalar DN')
                    require(edge.get('external_feed_plan_attributes') == detail,
                            'external root and edge attributes differ')
                else:
                    domain = 'named_plan_horizontal_segment'
                    extent = 'whole_local_edge' if detail['whole_local_edge'] else 'partial_horizontal_extent'
                    pairs = [(detail['plan_network_T'], detail['axis_network_T'])]
                    if 'plan_equipment_T' in detail:
                        pairs.append((detail['plan_equipment_T'], detail['axis_equipment_T']))
                    network = edge.get('network_named_lower_plan_attributes', [])
                    require(detail in edge.get('plan_segment_attributes', [])
                            or (detail == network if isinstance(network, dict) else detail in network),
                            'legacy segment root and edge attributes differ')
            require(detail['system'] == edge['system'] and detail['system'] in ('supply', 'return'),
                    'legacy provider system changed')
            require(set(paths) == set(detail['plan_edges']), 'legacy path scope population differs')
            require(all(not p.startswith('MEMBER:') and not a.startswith('MEMBER:') for p, a in pairs),
                    'member identity cannot enter named ordinary anchors')
            rows.append(dict(provider=root, mapping_id=record['mapping_id'], axis_edge_id=eid,
                floor=detail['floor'], system=detail['system'], plan_paths=copy.deepcopy(paths),
                axis_scope_paths=copy.deepcopy(axis_paths), source_sha256=sources,
                historical_local_graph_sha256=graph_hash, ordinary_anchor_pairs=pairs,
                scope_domain=domain, attribute_extent=extent, source_record=copy.deepcopy(record)))
    require(len({r['mapping_id'] for r in rows}) == len(rows), 'duplicate legacy mapping identity')
    return rows


def same_local_edge(current, old, eid):
    require(eid in current and eid in old, 'legacy scope lost a local edge')
    require({k: current[eid].get(k) for k in CORE} == {k: old[eid].get(k) for k in CORE},
            'legacy edge topology, ports or paths changed; requalify original mapping')


def current_plan_reader(config, source_hash, graph_hash):
    fallback = []
    def read(doc, graph, nid, sh, gh):
        require(sh == source_hash and gh == graph_hash, 'legacy T reader scope differs')
        try:
            return native_tee(doc, graph, nid, sh, gh)
        except ValueError:
            if not fallback:
                require(isinstance(config.get('plans'), list), 'exact current T configuration is unavailable')
                fallback.append(make_reader(config, source_hash, graph_hash))
            return fallback[0](doc, graph, nid, sh, gh)
    return read


def replay_floor(job):
    floor, specs, rows, config = job
    graphs = {v: load(specs[k]['path']) for v, k in [('plan', 'plan_graph'), ('iso', 'axis_graph')]}
    historical = {v: load(specs[k]['path']) for v, k in [('plan', 'historical_plan_graph'), ('iso', 'historical_axis_graph')]}
    docs, preflight = {}, {}
    for v, key in [('plan', 'plan_source'), ('iso', 'axis_source')]:
        docs[v], preflight[v] = read_source(specs[key]['path'])
        require(graphs[v]['metadata']['source_sha256'] == specs[key]['sha256'],
                'current legacy graph/source differs')
    by = {v: {e['edge_id']: e for e in g['edges']} for v, g in graphs.items()}
    old = {v: {e['edge_id']: e for e in g['edges']} for v, g in historical.items()}
    readers = dict(plan=current_plan_reader(config, specs['plan_source']['sha256'], specs['plan_graph']['sha256']),
                   iso=native_tee)
    junctions = {}
    for row in rows:
        for v, key in [('plan', 'plan_source'), ('iso', 'axis_source')]:
            require(row['source_sha256'][v] == specs[key]['sha256'], 'legacy source identity differs')
            historical_key = 'historical_plan_graph' if v == 'plan' else 'historical_axis_graph'
            require(row['historical_local_graph_sha256'][v] == specs[historical_key]['sha256'],
                    'wrong historical local graph for original provider')
            ids = list(row['plan_paths']) if v == 'plan' else [row['axis_edge_id']]
            for eid in ids:
                same_local_edge(by[v], old[v], eid)
        for p, a in row['ordinary_anchor_pairs']:
            for v, nid in [('plan', p), ('iso', a)]:
                key = (v, nid)
                if key not in junctions:
                    junctions[key] = readers[v](docs[v], graphs[v], nid,
                        specs['plan_source' if v == 'plan' else 'axis_source']['sha256'],
                        specs['plan_graph' if v == 'plan' else 'axis_graph']['sha256'])
    external = [r for r in rows if r['provider'] == 'sourceExternalFeedPlanAttributes']
    names = None
    if external:
        names = {}
        for v, owner, pk in [('plan', plan_destination, 'plan_destination_policy'),
                             ('iso', axis_destination, 'axis_destination_policy')]:
            policy = load(specs[pk]['path'])
            source, graph = specs['plan_source' if v == 'plan' else 'axis_source'], specs['plan_graph' if v == 'plan' else 'axis_graph']
            require(policy['source_sha256'] == source['sha256']
                    and policy['graph_sha256'] == specs['historical_plan_graph' if v == 'plan' else 'historical_axis_graph']['sha256'],
                    'external source policy does not belong to original native graph')
            policy = dict(policy, graph_sha256=graph['sha256'])
            names[v] = owner(docs[v], graphs[v], policy, source['sha256'], graph['sha256'])
        require(names['plan']['destination'] == names['iso']['destination'], 'named external destination differs')
    result = []
    for row in rows:
        proofs = {}
        for v in ('plan', 'iso'):
            selected = row['plan_paths'] if v == 'plan' else {row['axis_edge_id']: row['axis_scope_paths']}
            if v == 'iso' and row['provider'] == 'sourceExternalFeedPlanAttributes':
                detail, eid = row['source_record'], row['axis_edge_id']
                full = audit(docs[v], graphs[v], dict(source_sha256=specs['axis_source']['sha256'],
                    graph_sha256=specs['axis_graph']['sha256'], edges=[eid]), specs['axis_source']['sha256'], specs['axis_graph']['sha256'])
                edge = by[v][eid]
                excluded = {detail['display_only_segment_index'], *detail['inline_gap_segment_indices']}
                require([edge['attribute_paths'][detail['path_index']][i:i+2] for i in detail['segment_indices']] == detail['scope_paths'],
                        'external physical fragments changed')
                require(set(detail['segment_indices']).isdisjoint(excluded)
                        and set(detail['segment_indices']) | excluded == set(range(len(edge['attribute_paths'][0])-1)),
                        'external marker, gap and pipe coverage is incomplete')
                require(all(s['status'] == ('no_witness_in_scoped_search' if s['index'] in excluded else 'single_source_line_covers')
                            for s in full['edges'][0]['segments']), 'external native fragment coverage differs')
                gaps = {r['gap_segment_index']: r for r in edge['source_confirmed_gap_joints']}
                require(set(gaps) == set(detail['inline_gap_segment_indices'])
                        and all(r['status'] == 'user_confirmed_inline_joint_logical_continuity' for r in gaps.values()),
                        'external inline continuity lacks original confirmation')
                ports = [r for r in names['iso']['records'] if r['edge_id'] == eid]
                frontiers = [r for r in names['plan']['records'] if r['identifier'] == detail['identifier']]
                require(len(ports) == len(frontiers) == 1 and ports[0]['identifier'] == detail['identifier']
                        and ports[0]['port_id'] == detail['axis_port_id'] and frontiers[0]['edge_id'] == detail['plan_edges'][0],
                        'external named port mapping changed')
                proofs[v] = dict(native=full, named_port=ports[0], named_plan_frontier=frontiers[0],
                    excluded_display_and_inline_indices=sorted(excluded), physical_values_assigned=0)
                continue
            projected = []
            for eid, paths in selected.items():
                edge = by[v][eid]
                require(edge['system'] == row['system'], 'current legacy scope changes service')
                pieces = [(a, b) for path in edge['attribute_paths'] for a, b in zip(path, path[1:])]
                require(all(any(_on(a, x, y, .05) and _on(b, x, y, .05) for x, y in pieces)
                            for path in paths for a, b in zip(path, path[1:])), 'legacy fragments escape current native scope')
                projected.append(dict(edge, attribute_paths=copy.deepcopy(paths)))
            private = dict(graphs[v], edges=projected)
            gh = hashlib.sha256(encode(private)).hexdigest()
            source = specs['plan_source' if v == 'plan' else 'axis_source']['sha256']
            proof = coverage(docs[v], private, list(selected), source, gh)
            require(not proof['unresolved'] and proof['edges']
                    and all(e['segments'] and all(s['status'] == 'single_source_line_covers' for s in e['segments']) for e in proof['edges']),
                    'legacy native path requires requalification')
            proofs[v] = dict(native=proof, reading_projection_sha256=gh)
        result.append(dict(row, native_scope_proofs=proofs,
            current_local_core_paths_and_ports_unchanged=True, native_ordinary_anchors_replayed=True,
            native_ordinary_anchors=[dict(plan_node=p, axis_node=a, plan=junctions[('plan', p)], iso=junctions[('iso', a)]) for p, a in row['ordinary_anchor_pairs']],
            complete_physical_length_proved=False, human_accepted=False))
    return dict(floor=floor, records=result, inputs=specs, source_preflight=preflight,
                current_external_names=names, graph_mutated=False)


def inherit(original, source):
    result = copy.deepcopy(original)
    records = {r['edge_id']: r for r in result['records']}
    require(len(records) == len(result['records']), 'duplicate complete provider edge')
    scopes = source['records']
    require(len({r['mapping_id'] for r in scopes}) == len(scopes), 'duplicate legacy provider scope')
    new_edges, new_anchors = [], []
    for scope in scopes:
        require(scope['provider'] in ROOTS and scope.get('current_local_core_paths_and_ports_unchanged') is True
                and scope.get('native_ordinary_anchors_replayed') is True and scope.get('human_accepted') is False,
                'legacy inheritance requires current native and topology evidence')
        row = records[scope['axis_edge_id']]
        require(not any(o['mapping_id'] == scope['mapping_id'] for o in row['correspondence_observations']),
                'legacy provider already inherited; do not double-count')
        if not row['has_existing_correspondence']:
            new_edges.append(row['edge_id'])
        row['has_existing_correspondence'] = True
        row['correspondence_observations'].append(dict(provider=scope['provider'],
            domain=scope['scope_domain'], mapping_id=scope['mapping_id'], floor=scope['floor'],
            plan_edges=list(scope['plan_paths']), grouped_axis_edges=[scope['axis_edge_id']],
            attribute_extent=scope['attribute_extent'], whole_edge_values_assigned=False))
        mapping = result['ordinary_junction_mappings'][str(scope['floor'])]
        require(len(mapping) == len(set(mapping.values())), 'prior ordinary anchors collapse')
        for p, a in scope['ordinary_anchor_pairs']:
            require(not p.startswith('MEMBER:') and not a.startswith('MEMBER:'), 'member/ordinary anchor namespace conflict')
            require(not(p in mapping and mapping[p] != a or a in mapping.values() and mapping.get(p) != a),
                    'legacy ordinary anchor competes with a prior mapping')
            if p not in mapping:
                new_anchors.append(dict(floor=scope['floor'], plan_node=p, axis_node=a, provider=scope['provider']))
            mapping[p] = a
    pending = []
    corrected = []
    for old in original['remaining_horizontal_attributes']:
        row = copy.deepcopy(old)
        row['correspondence_observations'] = copy.deepcopy(records[row['edge_id']]['correspondence_observations'])
        if row['next_scope'] == 'apply_existing_native_crossview_discovery_to_unmatched_horizontal_path' and row['edge_id'] in new_edges:
            row['next_scope'] = 'known_legacy_named_scope_incomplete_whole_attributes'
            corrected.append(row['edge_id'])
        pending.append(row)
    result.update(mode=MODE, remaining_horizontal_attributes=pending,
        inherited_legacy_named_scopes=copy.deepcopy(scopes), newly_inherited_legacy_edges=sorted(new_edges),
        newly_inherited_legacy_ordinary_anchors=new_anchors, corrected_legacy_false_unpaired_horizontal=sorted(corrected),
        all_old_provider_observations_preserved=True, all_old_pipe_attributes_and_components_preserved=True,
        all_legacy_interfaces_and_member_namespaces_separate=True,
        new_correspondences_assigned=0, DN_or_length_values_assigned=0, human_accepted=False, whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence'] for r in records.values()),
        mixed_edges_without_any_correspondence=sum(r['classification'] == 'mixed_horizontal_vertical' and not r['has_existing_correspondence'] for r in records.values()),
        inherited_legacy_scope_observations=len(scopes), inherited_legacy_previously_omitted_edges=len(new_edges),
        corrected_legacy_false_unpaired_horizontal=len(corrected), new_legacy_ordinary_anchors=len(new_anchors),
        horizontal_next_scopes=dict(collections.Counter(r['next_scope'] for r in pending)))
    frontier = copy.deepcopy(result['current_horizontal_frontier'])
    frontier.update(status='all_current_and_legacy_named_scope_providers_inherited', records=pending,
        remaining_by_next_scope=result['counts']['horizontal_next_scopes'])
    result['current_horizontal_frontier'] = frontier
    require(result['member_domain_observations'] == original['member_domain_observations']
            and result['current_component_inventory'] == original['current_component_inventory'],
            'legacy inventory changed component or member evidence')
    return result


def fixed_parent(manifest):
    root = Path(__file__).resolve().parents[2]
    inputs = manifest['inputs']
    snapshot, provider = inputs['parent_snapshot'], inputs['parent_provider']
    skills = Path(snapshot['path']).parent / 'skills'
    with tempfile.TemporaryDirectory(prefix='cad-legacy-provider-') as temporary:
        output = Path(temporary) / 'checked'
        command = [sys.executable, '-X', 'utf8', '-B', str(root / 'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_native_contact_provider.py'),
            '--skills-root', str(skills), '--snapshot', snapshot['path'], '--native-run', str(Path(provider['path']).parent),
            '--expected-sha256', provider['sha256'], '--output', str(output)]
        run = subprocess.run(command, cwd=manifest['parent_replay_cwd'], capture_output=True, text=True, encoding='utf8')
        require(run.returncode == 0, 'complete fixed legacy parent failed: ' + run.stderr[-5000:])
        raw = (output / 'proof.json').read_bytes()
        execution = load(output / 'execution.json')
        require(raw == Path(provider['path']).read_bytes() and execution['owner'] == 'contact_owner_provider_inventory'
                and execution['proof_sha256'] == provider['sha256'], 'fixed legacy parent differs')
        return json.loads(raw)


def compute(manifest, announce=lambda message: None):
    inputs = manifest['inputs']
    def checked():
        require(all(sha(s['path']) == s['sha256'] for s in inputs.values()), 'legacy provider pinned input changed')
    checked()
    announce('Replaying the complete original contact provider in its immutable runtime')
    original = fixed_parent(manifest)
    rendered = load(inputs['rendered_graph']['path'])
    require(original['current_component_inventory']['rendered_graph_sha256'] == inputs['rendered_graph']['sha256'],
            'legacy adapter uses another rendered contact graph')
    rows = extract(rendered)
    jobs = []
    config = load(inputs['current_T_source_config']['path'])
    for floor in (1, 2, 3):
        spec = {key: inputs[key] for key in ('axis_graph', 'axis_source', 'historical_axis_graph')}
        for key in ('plan_graph', 'plan_source', 'historical_plan_graph'):
            spec[key] = inputs[key + '_' + str(floor)]
        require(original['original_provider_inventory_inputs']['plan_graph_' + str(floor)] == spec['plan_graph']
                and original['original_provider_inventory_inputs']['axis_graph'] == spec['axis_graph'],
                'legacy local parents differ from current complete provider')
        if any(r['floor'] == floor and r['provider'] == 'sourceExternalFeedPlanAttributes' for r in rows):
            spec.update(plan_destination_policy=inputs['plan_destination_policy'], axis_destination_policy=inputs['axis_destination_policy'])
        jobs.append((floor, spec, [r for r in rows if r['floor'] == floor], config))
    announce('Replaying all legacy native paths, ordinary Ts and independent named boundary ports')
    with ProcessPoolExecutor(max_workers=min(3, manifest.get('workers', 3))) as executor:
        floors = list(executor.map(replay_floor, jobs))
    scopes = dict(records=[row for floor in floors for row in floor['records']], floors=floors)
    result = inherit(original, scopes)
    checked()
    return dict(result, inputs=inputs, native_legacy_scope_replay=scopes,
                complete_original_contact_provider_replayed=True, current_native_legacy_scopes_replayed=True)


def implementation_hashes():
    root = Path(__file__).resolve().parents[2]
    names = ('native_current_junction_reader', 'batch_native_path_coverage', 'native_path_coverage_audit',
             'native_external_pipe_destination', 'native_external_port_destination', 'crossview_equipment_branch_inventory')
    return dict(entry=sha(__file__), fixed_parent_worker=sha(root / 'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_native_contact_provider.py'),
                **{name: sha(importlib.import_module(name).__file__) for name in names})


def produce(manifest, output):
    output = Path(output)
    require(not output.exists(), 'choose a fresh legacy provider output')
    before = implementation_hashes()
    result = compute(load(manifest), lambda text: print(text, flush=True))
    require(before == implementation_hashes(), 'legacy provider code changed during reconstruction')
    output.mkdir(parents=True)
    target = output / 'provider-inventory.json'
    target.write_bytes(encode(result))
    (output / 'horizontal-frontier.json').write_bytes(encode(result['current_horizontal_frontier']))
    (output / 'receipt.json').write_bytes(encode(dict(mode=MODE, manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=before, output_sha256=sha(target), human_accepted=False)))
    return result


def verify_output(output):
    output = Path(output)
    receipt = load(output / 'receipt.json')
    require(receipt['mode'] == MODE and receipt['implementation_sha256'] == implementation_hashes()
            and sha(receipt['manifest']['path']) == receipt['manifest']['sha256']
            and sha(output / 'provider-inventory.json') == receipt['output_sha256'], 'legacy provider receipt changed')
    result = compute(load(receipt['manifest']['path']))
    require(encode(result) == (output / 'provider-inventory.json').read_bytes()
            and encode(result['current_horizontal_frontier']) == (output / 'horizontal-frontier.json').read_bytes(),
            'legacy provider independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('manifest', 'output', 'verify-output'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args()
    if args.verify_output:
        result = verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:
            parser.error('fixed manifest and fresh output required')
        result = produce(args.manifest, args.output)
    print(result['counts'], flush=True)


if __name__ == '__main__':
    main()
