"""Reuse the confirmed-circle native corner reader for current T evidence.

The historical producer already supports a main turning at a circle. The
straight-through radial reader cannot read that schema. Replaying the actual
original Pair/reply and both native main LINEs preserves that old capability.
"""
import math, json
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from reconstruct_batch_circle_junctions import prepare, DECISION
from repair_confirmed_circle_junctions import slice_path, segments_for_interval
from source_reviewed_circle_branch_evidence import repair_root, recorded_z
from native_line_path_evidence import LAYERS, _on


def original_review(doc, source_hash, parents, review_input):
    if not review_input or sha(review_input['path']) != review_input['sha256']:
        raise ValueError('original confirmed-circle policy missing or changed')
    policy = load(review_input['path'])
    if policy.get('source_sha256') != source_hash:
        raise ValueError('confirmed circle policy belongs to another source')
    for key in ('manifest', 'reply'):
        if sha(policy[key]) != policy[key + '_sha256']:
            raise ValueError('original confirmed-circle ' + key + ' changed')
    for image in policy['pair_images']:
        if sha(image['path']) != image['sha256']:
            raise ValueError('original confirmed-circle Pair changed')
    manifest, reply = load(policy['manifest']), load(policy['reply'])
    if {p['sha256'] for p in policy['pair_images']} != {g['sha256'] for g in manifest['groups']}:
        raise ValueError('original confirmed-circle Pair population differs')
    selected = [p for p in parents if p['sha256'] == policy['input_graph_sha256']]
    if len(selected) != 1 or sha(selected[0]['path']) != selected[0]['sha256']:
        raise ValueError('confirmed-circle original graph missing or changed')
    parent = load(selected[0]['path'])
    screen, answers = prepare(doc, parent, manifest, reply, policy, source_hash, selected[0]['sha256'])
    native_screen = review_input.get('screen', {})
    if not native_screen.get('path') or sha(native_screen['path']) != native_screen.get('sha256'):
        raise ValueError('original confirmed-circle native screen missing or changed')
    canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, allow_nan=False)
    if canonical(load(native_screen['path'])) != canonical(screen):
        raise ValueError('original confirmed-circle native screen replay differs')
    confirmation = dict(confirmed_by='user', question='Batch Pair circle connections', answer=DECISION,
        records=answers, reply_sha256=policy['reply_sha256'])
    return parent, policy, screen, confirmation


def collect(doc, graph, node_id, source_hash, graph_hash, parents, review_input):
    nodes = {n['node_id']: n for n in graph['nodes']}
    node = nodes[node_id]
    incident = [e for e in graph['edges'] if node_id in (e.get('start_node_id'), e.get('end_node_id'))]
    if (graph.get('metadata', {}).get('source_sha256') != source_hash
            or node.get('node_type') not in ('tee', 'physical_junction') or node.get('review_required') is True
            or len(incident) != 3 or len({e['edge_id'] for e in incident}) != 3
            or node.get('system') not in LAYERS or {e.get('system') for e in incident} != {node['system']}):
        raise ValueError('confirmed endpoint T incidence/source differs')
    meta = node.get('user_confirmed_circle', {})
    parent, policy, screen, confirmation = original_review(doc, source_hash, parents, review_input)
    root = repair_root(graph, 'userConfirmedCircleJunctionRepair', node_id, meta.get('circle_handle'),
        'confirmation', confirmation, source_hash)
    candidates = [r for r in screen['candidates'] if r['circle_handle'] == meta.get('circle_handle')]
    records = [r for r in root['records'] if r['tee'] == node_id and r['circle_handle'] == meta.get('circle_handle')]
    if len(candidates) != 1 or len(records) != 1 or meta.get('confirmation') != confirmation:
        raise ValueError('original confirmed circle answer/record differs')
    candidate, record = candidates[0], records[0]
    circle = doc.entitydb.get(meta.get('circle_handle'))
    if (circle is None or circle.dxftype() != 'CIRCLE' or circle not in doc.modelspace()
            or tuple(circle.dxf.extrusion) != (0., 0., 1.) or circle.dxf.layer != meta.get('circle_layer')
            or circle.dxf.layer != candidate['circle_layer'] or meta.get('line_system') != node['system']
            or meta.get('source_graph_sha256') != policy['input_graph_sha256']
            or root.get('input_graph_sha256') != policy['input_graph_sha256']
            or meta.get('screen_sha256') != root.get('screen_sha256')
            or meta.get('screen_sha256') != review_input['screen']['sha256']
            or meta.get('graphic_radius_is_physical_length') is not False or meta.get('physical_length') != 'unknown'):
        raise ValueError('confirmed circle current native/provenance differs')
    point = [node['x'], node['y']]
    rim = candidate['branch_rim']
    if (math.dist(point, candidate['center']) > .05 or math.dist(point, meta.get('center', [])) > .05
            or math.dist(rim, meta.get('source_rim', [])) > .05):
        raise ValueError('confirmed circle current center/rim moved')
    branch = next((e for e in incident if e['edge_id'] == record['branch_edge']), None)
    if branch is None or branch.get('source_user_circle_connection') != meta:
        raise ValueError('confirmed circle branch binding differs')
    main_handles = [r['source_handle'] for r in candidate['native_main_rays']]
    if len(set(main_handles)) != 2:
        raise ValueError('endpoint reader requires two independently witnessed native main LINEs')
    rays = []
    for edge in incident:
        anchor = rim if edge is branch else point
        touch = []
        for path in edge.get('attribute_paths', []):
            for a, b in zip(path, path[1:]):
                if math.dist(a, anchor) <= .05 and math.dist(b, anchor) > .05: touch.append((a, b))
                elif math.dist(b, anchor) <= .05 and math.dist(a, anchor) > .05: touch.append((b, a))
        if len(touch) != 1:
            raise ValueError('current circle endpoint graph ray not unique')
        a, b = touch[0]
        hits = [line.dxf.handle for line in doc.modelspace().query('LINE') if line.dxf.layer == LAYERS[node['system']]
            and _on(a, list(line.dxf.start)[:2], list(line.dxf.end)[:2], .05)
            and _on(b, list(line.dxf.start)[:2], list(line.dxf.end)[:2], .05)]
        if len(hits) != 1 or hits[0] not in edge.get('source_handles', []):
            raise ValueError('current circle endpoint ray source ambiguous or changed')
        if edge is branch:
            if hits[0] != candidate['branch_handle']:
                raise ValueError('current circle native rim branch differs')
        else:
            split = edge.get('split_source_edge', {})
            original = next((e for e in parent['edges'] if e['edge_id'] == record['main_source_edge']), None)
            interval = split.get('interval_native_units')
            if (edge['edge_id'] not in record['main_child_edges'] or hits[0] not in main_handles
                    or original is None or split.get('edge_id') != original['edge_id']
                    or split.get('source_graph_sha256') != policy['input_graph_sha256']
                    or not isinstance(interval, list) or len(interval) != 2
                    or edge.get('path') != slice_path(original['path'], *interval)
                    or edge.get('attribute_paths') != segments_for_interval(original['path'], original['attribute_paths'], *interval)):
                raise ValueError('current endpoint main differs from its original split interval')
        length = math.dist(a, b)
        rays.append(dict(edge_id=edge['edge_id'], source_line_handle=hits[0], graph_segment=[a, b],
            direction=[(b[i] - a[i]) / length for i in (0, 1)],
            scope='confirmed_native_circle_rim' if edge is branch else 'confirmed_native_circle_center_LINE_endpoint'))
    center_contacts = [line.dxf.handle for line in doc.modelspace().query('LINE')
        if line.dxf.layer == LAYERS[node['system']]
        and _on(point, list(line.dxf.start)[:2], list(line.dxf.end)[:2], .05)]
    if set(center_contacts) != set(main_handles):
        raise ValueError('unaccounted same-system LINE contacts at confirmed endpoint circle')
    if len({r['source_line_handle'] for r in rays}) != 3:
        raise ValueError('confirmed circle native ray identities collapse')
    directions = [r['direction'] for r in rays]
    pairs = [(i, j) for i, a in enumerate(directions) for j, b in enumerate(directions) if i < j
        and sum(x*y for x, y in zip(a, b)) <= -math.cos(math.radians(1))]
    if len(pairs) != 1 or any(sum(x*y for x, y in zip(a,b)) > math.cos(math.radians(.1))
            for i,a in enumerate(directions) for b in directions[i+1:]):
        raise ValueError('confirmed endpoint T has no unique opposing ray pair')
    z = [recorded_z(doc, meta, circle, dict(handle=h), dict(handle=candidate['branch_handle']), rim) for h in main_handles]
    if any(max(abs(row['circle_z']-row[k]) for k in ('main_z_at_center','branch_z_at_rim')) > .05 for row in z):
        raise ValueError('confirmed endpoint native Z needs a separate reviewed scope')
    return dict(status='original_user_circle_corner_main_and_current_native_T_replayed',
        source_sha256=source_hash, graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id, system=node['system'], position=point, source_rays=rays)],
        original_review=dict(policy=review_input, reply_sha256=policy['reply_sha256'], manifest_sha256=policy['manifest_sha256'],
            original_graph_sha256=policy['input_graph_sha256'], native_screen_sha256=review_input['screen']['sha256'],circle_handle=circle.dxf.handle),
        native_Z=z, original_main_rays_replayed=True, circle_layer_rewritten=False,
        through_pair_recomputed_from_native_rays=True, physical_values_assigned=0,
        graph_mutated=False, physical_ports_verified=False, human_accepted=False, hil_ready=False)


def implementation_hashes():
    return {name: sha(Path(__file__).with_name(name)) for name in (
        Path(__file__).name, 'reconstruct_batch_circle_junctions.py',
        'repair_confirmed_circle_junctions.py', 'source_reviewed_circle_branch_evidence.py', 'native_line_path_evidence.py')}
