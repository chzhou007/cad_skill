"""Resolve an already split pending junction from exact native three-ray evidence.

No endpoint snapping, new pipe geometry or circle-centre relocation is allowed.
The explicit marker contains the actual LINE intersection; its centre need not
coincide with that intersection. Preserve both coordinates as source evidence.
"""
import argparse
import copy
import math
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory import index_graph, native_tee
from edge_endpoint_semantics import reconcile
from source_readability import read_source

MODE = 'native_pending_three_ray_junction_resolution_v1'


def collect(doc, graph, selections, source_hash, graph_hash, tolerance=.05):
    from ezdxf import bbox
    from ezdxf.addons.drawing import RenderContext
    from cad_ceiling_native_rules import match_out_of_plane_symbol
    from source_circle_rim_tee_screen import LAYERS
    nodes, _, adjacent = index_graph(graph)
    if not selections or len({x['node_id'] for x in selections}) != len(selections):
        raise ValueError('Explicit unique pending junction scope required')
    context = RenderContext(doc)
    glyphs = [dict(handle=e.dxf.handle, a=(e.dxf.start.x, e.dxf.start.y), b=(e.dxf.end.x, e.dxf.end.y))
              for e in doc.modelspace().query('LINE') if e.dxf.layer == '空调立管、水平支管']
    query = copy.deepcopy(graph)
    qnodes = {n['node_id']: n for n in query['nodes']}
    result = []
    for selected in selections:
        nid = selected['node_id']
        node = nodes.get(nid, {})
        pending = node.get('source_main_continuation', {})
        incident = adjacent[nid]
        if (node.get('node_type') != 'virtual_equipment' or node.get('subtype') != 'pending_source_junction'
                or node.get('review_required') is not True or pending.get('branch_connectivity') != 'pending'
                or pending.get('source_sha256') != source_hash or len(incident) != 3):
            raise ValueError('Only explicitly pending, already split native junctions are supported')
        point = [node['x'], node['y']]
        if pending.get('source_point') != point or {e['system'] for e in incident} != {node['system']}:
            raise ValueError('Pending native intersection or system changed')
        if set(pending.get('main_edge_ids', [])) | {pending.get('branch_edge_id')} != {e['edge_id'] for e in incident}:
            raise ValueError('Pending main/branch edge ownership changed')
        if selected['circle_handle'] not in pending.get('circle_handles', []):
            raise ValueError('Selected marker is not the source pending marker')
        circle = doc.entitydb.get(selected['circle_handle'])
        if circle is None or not circle.is_alive or circle.dxftype() != 'CIRCLE' or circle.dxf.layer not in LAYERS:
            raise ValueError('Native pipe circle missing')
        normal = circle.dxf.get('extrusion', (0, 0, 1))
        if abs(normal[0]) > 1e-10 or abs(normal[1]) > 1e-10 or abs(abs(normal[2])-1) > 1e-10:
            raise ValueError('Unsupported marker plane')
        center = list(circle.ocs().to_wcs(circle.dxf.center))
        radius = circle.dxf.radius
        if not math.isfinite(radius) or radius <= 0 or math.dist(point, center[:2]) >= radius:
            raise ValueError('Exact native intersection is outside its marker')
        if match_out_of_plane_symbol(dict(center=center[:2], radius=radius), glyphs, tolerance):
            raise ValueError('Equipment or out-of-plane marker is not a native T')
        if any(selected['circle_handle'] in b.get('source_marker_handles', []) for b in graph.get('boundary_anchors', [])):
            raise ValueError('Reviewed boundary is protected')
        for e in doc.modelspace():
            if e.dxf.layer not in LAYERS or e.dxftype() == 'LINE':
                continue
            if e.dxftype() == 'CIRCLE':
                if e.dxf.handle != circle.dxf.handle and math.dist(list(e.ocs().to_wcs(e.dxf.center))[:2], point) < radius:
                    raise ValueError('Multiple nearby pipe markers need separate interpretation')
                continue
            box = bbox.extents([e])
            if not box.has_data or not (box.extmax.x < point[0]-radius or box.extmin.x > point[0]+radius
                                       or box.extmax.y < point[1]-radius or box.extmin.y > point[1]+radius):
                raise ValueError('Unsupported nearby pipe geometry')
        # The inherited collector requires the intended type in its query view.
        # Only this private query changes; the original pending node is retained.
        qnodes[nid]['node_type'] = 'tee'
        evidence = native_tee(doc, query, nid, source_hash, graph_hash)
        rays = evidence['junctions'][0]['source_rays']
        if any('source_line_handle' not in r for r in rays):
            raise ValueError('This rule requires exact modelspace LINE contacts')
        main = [r for r in rays if r['edge_id'] in pending['main_edge_ids']]
        branch = [r for r in rays if r['edge_id'] == pending['branch_edge_id']]
        if (len(main) != 2 or len(branch) != 1
                or any(r['source_line_handle'] != pending['main_source_handle'] for r in main)
                or branch[0]['source_line_handle'] != pending['branch_source_handle']):
            raise ValueError('Native main and branch source witnesses differ')
        dot = lambda a, b: sum(x*y for x, y in zip(a, b))
        if abs(dot(main[0]['direction'], main[1]['direction'])+1) > 1e-7 or abs(dot(main[0]['direction'], branch[0]['direction'])) > 1e-7:
            raise ValueError('Native T needs opposite through arms and an orthogonal branch')
        handles = {r['source_line_handle'] for r in rays}
        lines = [doc.entitydb[h] for h in handles]
        if len({context.resolve_all(e).color for e in lines}) != 1:
            raise ValueError('Native pipe colours disagree')
        if any(abs(p.z-center[2]) > tolerance for line in lines for p in (line.dxf.start, line.dxf.end)):
            raise ValueError('Native source Z disagreement')
        branch_line = doc.entitydb[pending['branch_source_handle']]
        if min(math.dist(point, list(p)[:2]) for p in (branch_line.dxf.start, branch_line.dxf.end)) > tolerance:
            raise ValueError('Branch is not an exact native endpoint contact')
        result.append(dict(node_id=nid, circle_handle=circle.dxf.handle, exact_native_intersection=point,
            circle_center_WCS=center, circle_offset=math.dist(point, center[:2]),
            source_ray_evidence=evidence, prior_node=copy.deepcopy(node),
            physical_geometry_changed=False, human_accepted=False))
    return result


def normalize(graph, records):
    out = copy.deepcopy(graph)
    nodes, edges, adjacent = index_graph(out)
    changed = set()
    for row in records:
        nid = row['node_id']
        if nodes.get(nid) != row['prior_node']:
            raise ValueError('Pending node changed after collection')
        node = nodes[nid]
        node.update(node_type='tee', subtype='physical_tee', review_required=False,
                    connection_status='native_source_three_ray_T', resolution_state='source_three_ray_junction_resolved')
        node.pop('boundary_type', None)
        node['source_main_continuation'].update(branch_connectivity='native_LINE_endpoint_to_main_verified',
                                                circle_semantics='drafting_marker_contains_exact_native_intersection')
        node['source_pending_junction_resolution'] = dict(circle_handle=row['circle_handle'], human_accepted=False)
        changed.update(e['edge_id'] for e in adjacent[nid])
    scoped, semantic_changes = reconcile(dict(nodes=out['nodes'], edges=[edges[eid] for eid in sorted(changed)],
                                               boundary_anchors=out.get('boundary_anchors', [])))
    rebuilt = {e['edge_id']: e for e in scoped['edges']}
    out['edges'] = [rebuilt.get(e['edge_id'], e) for e in out['edges']]
    out['sourcePendingNativeJunctionResolution'] = dict(mode=MODE, records=copy.deepcopy(records),
        rebuilt_edge_ids=sorted(changed), edge_semantic_changes=semantic_changes,
        added_nodes=0, added_edges=0, physical_lengths_assigned=0, human_accepted=False)
    out['derivedEvidenceInvalidation'] = dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='pending junctions resolved from native LINE contacts; incident edge types rebuilt',
        recompute=['source_comparison', 'T_and_port_audit', 'inventory', 'crossview_mapping', 'DN_scope', 'length_attributes', 'HIL'],
        historical_annotations_preserved=True)
    out.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False,
        review_status='native_pending_junctions_resolved_downstream_replay_pending')
    return out


def compute(paths, policy):
    from normalize_two_arm_circle_continuity import verify_output as verify_parent
    for key in ('source', 'graph', 'devices'):
        if sha(paths[key]) != policy.get(key + '_sha256'):
            raise ValueError('Pending junction input changed: ' + key)
    parent = verify_parent(Path(paths['graph']).parent)
    if parent['output_graph_sha256'] != sha(paths['graph']):
        raise ValueError('Complete native circle parent differs')
    parent_devices = Path(paths['graph']).parent/'assigned_edge_device_instances.csv'
    if sha(parent_devices) != sha(paths['devices']):
        raise ValueError('Component table is not the native parent inventory')
    doc, preflight = read_source(paths['source'])
    graph = load(paths['graph'])
    records = collect(doc, graph, policy['selections'], sha(paths['source']), sha(paths['graph']))
    return normalize(graph, records), dict(source_preflight=preflight, records=records, physical_lengths_assigned=0,
                                         nodes_added=0, edges_added=0, components_unchanged=True, human_accepted=False)


def implementation_hashes():
    names = ('resolve_pending_native_junctions.py', 'crossview_equipment_branch_inventory.py',
             'native_junction_ray_evidence.py', 'cad_ceiling_native_rules.py', 'edge_endpoint_semantics.py', 'source_readability.py')
    return {name: sha(Path(__file__).with_name(name)) for name in names}


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory/'pending-native-junction-audit.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Pending junction implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Pending junction dependency changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    out, proof = compute(paths, load(paths['policy']))
    if (encode(out) != (directory/'graph_with_edges.json').read_bytes() or receipt['proof'] != proof
            or receipt['output_graph_sha256'] != sha(directory/'graph_with_edges.json')
            or Path(paths['devices']).read_bytes() != (directory/'assigned_edge_device_instances.csv').read_bytes()):
        raise ValueError('Pending junction independent replay differs')
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for key in ('source', 'graph', 'devices', 'policy', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    paths = {k: getattr(args, k) for k in ('source', 'graph', 'devices', 'policy')}
    if args.output.exists():
        raise FileExistsError(args.output)
    out, proof = compute(paths, load(args.policy))
    args.output.mkdir(parents=True)
    target = args.output/'graph_with_edges.json'
    target.write_bytes(encode(out))
    (args.output/'assigned_edge_device_instances.csv').write_bytes(args.devices.read_bytes())
    (args.output/'pending-native-junction-audit.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), proof=proof, output_graph_sha256=sha(target),
        family_entry_integrated=False, downstream_inventory_and_mapping_invalidated=True, human_accepted=False)))
    print(dict(resolved_Ts=len(proof['records']), added_edges=0, component_table_unchanged=True), flush=True)


if __name__ == '__main__':
    main()
