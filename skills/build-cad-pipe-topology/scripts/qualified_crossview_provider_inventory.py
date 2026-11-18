"""Inherit every published correspondence domain before discovering more paths.

This inventory assigns no new connection or value. Ordinary local Ts and
member-graph Ts retain separate namespaces. Ancestor observations may overlap;
they are retained as observations, never installed as competing graph writers.
"""
import argparse, collections, copy, importlib, sys
from pathlib import Path
from confirm_crossview_paths import load, sha, encode

MODE = 'qualified_crossview_provider_inventory_v1'
ROOTS = {
    'anchor_bounded_mains', 'ordered_group_plan_runs', 'ordered_anchor_branches',
    'noncompound_main_extents', 'member_plan_runs', 'compound_member_mains',
    'compound_member_interfaces', 'compound_member_bridges',
    'ordered_owner_plan_runs', 'qualified_plan_scope_runs',
}


def inventory(axis, context, batch, plans, routing, frontier, extension):
    ae = {e['edge_id']: e for e in axis['edges']}
    if len(ae) != len(axis['edges']):
        raise ValueError('duplicate axis edge identity')
    if {r['edge_id'] for r in routing['edges']} != ae.keys():
        raise ValueError('routing and current axis inventories differ')
    paths = {(e['edge_id'], pi, si): [a, b] for e in axis['edges']
             for pi, path in enumerate(e['attribute_paths'])
             for si, (a, b) in enumerate(zip(path, path[1:]))}
    if len(paths) != len(routing['records']) or any(
        paths.get((r['edge_id'], r['path_index'], r['segment_index'])) != r['scope_points']
        for r in routing['records']):
        raise ValueError('current axis segment scope changed')
    if any(r['DN_source_route'] != ('axis_11_native_vertical' if r['direction_class'] == 'vertical'
           else 'corresponding_floor_plan_horizontal' if r['direction_class'] == 'horizontal'
           else 'original_source_direction_review') for r in routing['records']):
        raise ValueError('attribute-source direction policy changed')
    pn = {f: {n['node_id']: n for n in g['nodes']} for f, g in plans.items()}
    pe = {f: {e['edge_id']: e for e in g['edges']} for f, g in plans.items()}
    an = {n['node_id']: n for n in axis['nodes']}
    def service(graph, nid):
        values = {e['system'] for e in graph['edges'] if nid in (e['start_node_id'], e['end_node_id'])}
        if len(values) != 1 or not values <= {'supply', 'return'}:
            raise ValueError('anchor needs independent same-system incidence')
        return next(iter(values))
    mappings = {f: copy.deepcopy(v['junction_mapping']) for f, v in batch['floors'].items()}
    observations = collections.defaultdict(list)
    added = []

    def anchor(f, p, a, provider):
        f = str(f)
        if p.startswith('MEMBER:') or a.startswith('MEMBER:'):
            raise ValueError('member node cannot enter ordinary anchor namespace')
        if p not in pn[f] or a not in an:
            raise ValueError('provider anchor missing from current local graph')
        if pn[f][p].get('floor') != int(f) or an[a].get('floor') != int(f):
            raise ValueError('provider anchor floor differs')
        if service(plans[f], p) != service(axis, a):
            raise ValueError('provider anchor changes system')
        m = mappings[f]
        if p in m and m[p] != a or a in m.values() and m.get(p) != a:
            raise ValueError('qualified ordinary anchor identity conflicts')
        if p not in m:
            added.append(dict(floor=int(f), plan_node=p, axis_node=a, provider=provider))
        m[p] = a

    for f, mapping in mappings.items():
        if len(mapping) != len(set(mapping.values())):
            raise ValueError('early anchor identity collapses')
        for p, a in list(mapping.items()):
            anchor(f, p, a, 'early_batch')
        for row in batch['floors'][f]['records']:
            for eid in row['iso_edges']:
                if eid not in ae:
                    raise ValueError('early batch axis path missing')
                observations[eid].append(dict(provider='early_batch', domain='ordinary_local_graph',
                    mapping_id=row['mapping_id'], plan_edges=row['plan_edges'],
                    grouped_axis_edges=row['iso_edges']))
    for p, a in extension['current_junction_mapping'].items():
        anchor(extension['floor'], p, a, 'ordered_owner_native_extension')
    for row in extension['new_records']:
        for eid in row['iso_edges']:
            observations[eid].append(dict(provider='ordered_owner_native_extension',
                domain='ordinary_local_graph', mapping_id=row['mapping_id'],
                plan_edges=row['plan_edges'], grouped_axis_edges=row['iso_edges']))

    member_observations = []
    for root, value in context.items():
        if not isinstance(value, dict) or 'records' not in value:
            continue
        if root == 'axis_vertical_segment_DN':
            continue
        if root not in ROOTS:
            raise ValueError('new correspondence provider needs an explicit domain adapter: ' + root)
        if value.get('human_accepted') is not False or not value.get('source_bindings'):
            raise ValueError('provider qualification or evidence bindings missing')
        for row in value['records']:
            eid = row['axis_edge_id']
            if eid not in ae or row['axis_attribute_paths'] != ae[eid]['attribute_paths']:
                raise ValueError('provider axis geometry changed')
            if row['system'] != ae[eid]['system']:
                raise ValueError('provider axis service differs')
            domain = 'physical_member_graph' if root.startswith('compound_member_') else 'ordinary_local_graph'
            observations[eid].append(dict(provider=root, domain=domain,
                mapping_id=row.get('mapping_id', row.get('axis_mapping_id')),
                plan_edges=row.get('plan_edges', [row['plan_edge_id']] if 'plan_edge_id' in row else []),
                member_edge_id=row.get('plan_member_edge_id', row.get('member_edge_id'))))
            if domain == 'physical_member_graph':
                member_observations.append(dict(provider=root, axis_edge_id=eid,
                    member_edge_id=row.get('plan_member_edge_id', row.get('member_edge_id')),
                    anchors=copy.deepcopy(row.get('anchors', row.get('endpoint_relations', {})))))
                continue
            pairs = []
            if root in ('anchor_bounded_mains', 'ordered_group_plan_runs'):
                pids, aids = row['plan_Ts'], row['axis_Ts']
                ids = row.get('plan_edges', [row['plan_edge_id']] if 'plan_edge_id' in row else [])
                if len(pids) != 2 or len(aids) != 2 or len(ids) != 1:
                    raise ValueError('one interval with ordered native endpoint pairs required')
                plan_edge = pe[str(row['floor'])][ids[0]]
                if set(pids) != {plan_edge['start_node_id'], plan_edge['end_node_id']} or set(aids) != {ae[eid]['start_node_id'], ae[eid]['end_node_id']}:
                    raise ValueError('provider endpoint incidence changed')
                pairs = list(zip(pids, aids))
            elif root == 'noncompound_main_extents':
                pairs = list(zip(row['plan_nodes'], row['axis_nodes']))
            elif root == 'ordered_anchor_branches':
                pairs = [(row['main_anchor']['plan_node'], row['main_anchor']['axis_node'])]
            elif root in ('ordered_owner_plan_runs', 'qualified_plan_scope_runs'):
                m = row.get('mapping', row.get('current_mapping'))
                pairs = [(m['plan_start'], m['iso_start']), (m['plan_end'], m['iso_end'])]
            # member_plan_runs uses a detail/plan alias coordinate domain. Its
            # canonical_Ts are observations, not an ordered local-node pairing.
            for p, a in pairs:
                anchor(row['floor'], p, a, root)
    rows = []
    for edge in routing['edges']:
        eid = edge['edge_id']
        rows.append(dict(edge_id=eid, classification=edge['classification'],
            horizontal_segments=edge['horizontal_segments'], vertical_segments=edge['vertical_segments'],
            correspondence_observations=observations[eid],
            has_existing_correspondence=bool(observations[eid]),
            unmapped_horizontal_extent_count=None,
            whole_edge_attribute_unknown_is_mapping_backlog=False))
    remaining = []
    fixes = []
    for prior in frontier['records']:
        eid = prior['edge_id']
        if next(e for e in routing['edges'] if e['edge_id'] == eid)['classification'] != 'horizontal_only':
            raise ValueError('vertical or mixed edge in pure horizontal frontier')
        row = copy.deepcopy(prior)
        row['correspondence_observations'] = observations[eid]
        old = row['next_scope']
        if old == 'apply_existing_native_crossview_discovery_to_unmatched_horizontal_path' and observations[eid]:
            row['next_scope'] = ('known_member_correspondence_incomplete_metric' if any(
                o['domain'] == 'physical_member_graph' for o in observations[eid])
                else 'known_local_correspondence_incomplete_attributes')
            fixes.append(dict(edge_id=eid, old_scope=old, current_scope=row['next_scope'],
                              providers=sorted({o['provider'] for o in observations[eid]})))
        remaining.append(row)
    return dict(mode=MODE, status='inherited_correspondence_inventory_not_new_mapping_or_attribute_qualification',
        records=rows, ordinary_junction_mappings=mappings, added_ordinary_anchors=added,
        member_domain_observations=member_observations, remaining_horizontal_attributes=remaining,
        corrected_prior_unmapped_classifications=fixes,
        counts=dict(axis_edges=len(rows), existing_correspondence_edges=sum(bool(observations[e]) for e in ae),
            newly_inherited_ordinary_anchors=len(added), member_domain_observations=len(member_observations),
            corrected_false_unmapped_edges=len(fixes),
            pure_horizontal_remaining_attributes=len(remaining),
            horizontal_next_scopes=dict(collections.Counter(r['next_scope'] for r in remaining))),
        vertical_segments_routed_to_plan=0, mixed_unmapped_horizontal_extent_count=None,
        local_graphs_mutated=False, new_correspondences_assigned=0, DN_or_length_values_assigned=0,
        human_accepted=False, whole_goal_complete=False)


def compute(manifest):
    paths = {k: Path(v['path']) for k, v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k]) != v['sha256'] for k, v in manifest['inputs'].items()):
            raise ValueError('provider inventory pinned input changed')
    checked()
    pipeline = Path(__file__).resolve().parents[2] / 'orchestrate-cad-drawing-pipeline/scripts'
    viewer = Path(__file__).resolve().parents[2] / 'visualize-cad-pipe-topology/scripts'
    for p in (pipeline, viewer):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from native_replay_session import verify_once
    from refresh_qualified_plan_scope_attributes import verify
    from rebuild_ordered_owner_crossview import verify_output
    from axis_attribute_source_routing import verify_output as verify_routing
    bundle = paths['viewer_manifest'].parents[2]
    q = verify_once(bundle, verify)
    if q.get('artifact_replay') != 'passed':
        raise ValueError('current provider bundle did not replay')
    extension = verify_once(paths['owner_extension'].parent, verify_output)
    routing = verify_once(paths['routing'].parent, verify_routing)
    axis = load(paths['axis_graph'])
    m = load(paths['viewer_manifest'])
    if m['attributeValueContext']['source_graph_sha256'] != sha(paths['raw_axis_graph']):
        raise ValueError('provider bundle belongs to another raw graph')
    raw = load(paths['raw_axis_graph'])
    if {e['edge_id']:e['attribute_paths'] for e in raw['edges']} != {e['edge_id']:e['attribute_paths'] for e in axis['edges']}:
        raise ValueError('current axis paths differ from provider bundle')
    result = inventory(axis, m['attributeValueContext'], load(paths['batch']),
        {str(f): load(paths['plan_graph_' + str(f)]) for f in (1, 2, 3)},
        routing, load(paths['frontier']), extension)
    result.update(inputs=manifest['inputs'], current_provider_artifact_replayed=True,
                  ordered_owner_native_replayed=True, original_CAD_direction_replayed=True)
    checked()
    return result


def implementation_hashes():
    names = ('axis_attribute_source_routing', 'rebuild_ordered_owner_crossview')
    return dict({n: sha(importlib.import_module(n).__file__) for n in names}, entry=sha(__file__))


def produce(manifest, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    result = compute(load(manifest))
    output.mkdir(parents=True)
    p = output / 'provider-inventory.json'
    p.write_bytes(encode(result))
    (output / 'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=implementation_hashes(), output_sha256=sha(p))))
    return result


def verify_output(output):
    output = Path(output)
    receipt = load(output / 'receipt.json')
    m = receipt['manifest']
    if receipt['mode'] != MODE or sha(m['path']) != m['sha256'] or receipt['implementation_sha256'] != implementation_hashes() or sha(output / 'provider-inventory.json') != receipt['output_sha256']:
        raise ValueError('provider inventory code, input or output changed')
    result = compute(load(m['path']))
    if encode(result) != (output / 'provider-inventory.json').read_bytes():
        raise ValueError('independently replayed provider inventory differs')
    return result


def main():
    p = argparse.ArgumentParser()
    for n in ('manifest', 'output', 'verify-output'):
        p.add_argument('--' + n, type=Path)
    a = p.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'orchestrate-cad-drawing-pipeline/scripts'))
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            result = verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:
                p.error('pinned manifest and new output required')
            result = produce(a.manifest, a.output)
    print(result['counts'], flush=True)


if __name__ == '__main__':
    main()
