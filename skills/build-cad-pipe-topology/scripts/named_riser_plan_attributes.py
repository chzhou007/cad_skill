"""Replay floor-plan DN and measured XY scope on named riser approaches.

The named riser DN is a separate vertical-domain observation. Its verified
leader must not seed the horizontal approach. No graph or physical port is
changed, and a circle's graphic radius is never an installed connector.
"""
import argparse
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from match_named_riser_floor_paths import MODE as MAPPING_MODE, verify_output as verify_mapping
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph, native_tee
from native_named_riser_evidence import collect as collect_names
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from source_checked_plan_path_coverage import audit as audit_paths
from native_plan_projection_lengths import unit_evidence, lengths

MODE = 'named_riser_floor_plan_attributes_v1'


def topology_contract(doc, graph, mapping, source_hash, graph_hash):
    if (mapping.get('mode') != MAPPING_MODE or mapping.get('local_graphs_mutated') is not False
            or mapping.get('human_accepted') is not False or mapping.get('physical_values_fused') is not False
            or mapping.get('source_sha256', {}).get('plan') != source_hash
            or mapping.get('graph_sha256', {}).get('plan') != graph_hash):
        raise ValueError('independent named floor mapping differs')
    nodes, edges, adj = index_graph(graph)
    mains, excluded, junctions, systems, owners = [], set(), {}, set(), set()
    if len(mapping['records']) != 2:
        raise ValueError('paired service approach scope required')
    for record in mapping['records']:
        system = record['system']; tee = record['plan_equipment_main_T']; rif = record['plan_riser_interface']
        if len(record['plan_edges']) != 1:
            raise ValueError('approach requires one already normalized local edge')
        eid = record['plan_edges'][0]; edge = edges[eid]
        if (system in systems or edge['system'] != system
                or {edge['start_node_id'], edge['end_node_id']} != {tee, rif}
                or nodes[tee].get('floor') != record['floor'] or nodes[rif].get('floor') != record['floor']
                or any(nodes[n].get('review_required') is True for n in (tee, rif))
                or len(adj[tee]) != 3 or len(adj[rif]) != 1
                or edge['attribute_paths'] != record['paths']['plan']['attribute_paths']):
            raise ValueError('named approach local identity, floor or incidence differs')
        independent = record['paths']['plan']['independent_equipment_service']
        trace = independent['trace']
        if (independent.get('ready_for_mapping_comparison') is not True
                or trace.get('status') != 'unique_graph_service_to_T' or trace['tee'] != tee
                or len(trace['edges']) != 1):
            raise ValueError('independent equipment service anchor differs')
        proof = native_tee(doc, graph, tee, source_hash, graph_hash)
        if [proof] != record['paths']['plan']['junctions']:
            raise ValueError('named approach native T changed')
        rows = proof.get('junctions', [])
        if len(rows) != 1 or len(rows[0]['source_rays']) != 3:
            raise ValueError('ordinary three-ray source T required')
        ray = [r for r in rows[0]['source_rays'] if r['edge_id'] == eid]
        if len(ray) != 1 or not ray[0].get('source_line_handle'):
            raise ValueError('approach has no native through-pipe identity')
        through = {r['edge_id'] for r in rows[0]['source_rays']
                   if r.get('source_line_handle') == ray[0]['source_line_handle']}
        off = {e['edge_id'] for e in adj[tee]} - through
        if len(through) != 2 or off != set(trace['edges']):
            raise ValueError('equipment branch cannot redefine the through main')
        branch = edges[next(iter(off))]
        if branch['system'] != system or {branch['start_node_id'], branch['end_node_id']} != {tee, record['equipment_id']}:
            raise ValueError('equipment branch ownership differs')
        mains.append(eid); excluded.update(off); junctions[tee] = proof
        systems.add(system); owners.add((record['equipment_id'], record['floor']))
    if systems != {'supply', 'return'} or len(owners) != 1 or len(set(mains)) != 2:
        raise ValueError('two independent services of one floor equipment required')
    return dict(main_edges=mains, branches=[], junctions=junctions,
                verified_taps=sorted(junctions), branch_frontier_edges=sorted(excluded))


def named_annotation_domain(doc, graph, mapping, source_hash, graph_hash):
    originals = [r['native_names']['plan'] for r in mapping['records']]
    specs = [dict(text_handle=r['source_text']['handle'], expected_text=r['source_text']['text'],
                  underline_handle=r['underline']['handle'], leader_handle=r['leader']['handle'],
                  target=dict(kind='plan_riser_circle', node_id=r['target']['node_id'],
                              circle_handle=r['target']['circle_handle'])) for r in originals]
    policy = dict(source_sha256=source_hash, graph_sha256=graph_hash,
                  text_layers=sorted({r['source_text']['layer'] for r in originals}),
                  leader_layers=sorted({r['leader']['layer'] for r in originals}), selections=specs)
    fresh = collect_names(doc, graph, policy, source_hash, graph_hash)
    if fresh['records'] != originals:
        raise ValueError('named riser annotation domain changed')
    return dict(records=fresh['records'],
                consumed_text_handles=[r['source_text']['handle'] for r in originals],
                consumed_stroke_handles=[r[k]['handle'] for r in originals for k in ('underline', 'leader')],
                rule='native_named_riser_circle_DN_is_not_horizontal_approach_DN',
                vertical_DN_selected=False)


def compute(paths, policy):
    for key in ('source', 'graph', 'mapping', 'mapping_receipt'):
        if sha(paths[key]) != policy.get(key + '_sha256'):
            raise ValueError('named plan attribute dependency changed ' + key)
    folder = Path(paths['mapping']).resolve().parent
    if (Path(paths['mapping']).resolve() != folder / 'mapping.json'
            or Path(paths['mapping_receipt']).resolve() != folder / 'named-riser-mapping-receipt.json'):
        raise ValueError('noncanonical named mapping inputs')
    mapping = verify_mapping(folder)
    graph = load(paths['graph']); doc, preflight = read_source(paths['source'])
    sh, gh = sha(paths['source']), sha(paths['graph'])
    contract = topology_contract(doc, graph, mapping, sh, gh)
    domain = named_annotation_domain(doc, graph, mapping, sh, gh)
    texts, inventory = catalog(doc, graph, contract['main_edges'], sh, gh)
    consumed = set(domain['consumed_text_handles'])
    texts = [t for t in texts if t['handle'] not in consumed]
    group = dict(group_id='named_riser_floor_approaches', main_edges=contract['main_edges'], branches=[],
                 seeds=policy['seeds'], line_F_frames=policy.get('line_F_frames', []))
    dn = attribute_checked_scope(doc, graph, group, texts, sh, gh, set(inventory['F_text_handles']),
        junctions=contract['junctions'], verified_taps=contract['verified_taps'],
        branch_frontier_edges=contract['branch_frontier_edges'], path_auditor=audit_paths,
        verified_nonpipe_annotation_strokes=domain['consumed_stroke_handles'])
    by = {r['edge_id']: r for r in dn['records']}
    units = unit_evidence(doc, policy)
    coverage = audit_paths(doc, graph, dict(source_sha256=sh, graph_sha256=gh, edges=contract['main_edges']), sh, gh)
    records = []
    for record in mapping['records']:
        eid = record['plan_edges'][0]
        if by[eid]['nominal_mm'] is None:
            raise ValueError('named approach DN remains conflicted or unknown')
        projection = lengths(graph, coverage, record, units)
        records.append(dict(mapping_id=record['mapping_id'], floor=record['floor'], system=record['system'],
            plan_edges=record['plan_edges'], iso_edges=record['iso_edges'], plan_riser_interface=record['plan_riser_interface'],
            iso_riser_junction=record['iso_riser_junction'], diameter=by[eid], horizontal_projection=projection,
            plan_glyph_radius_added_to_length=False, physical_port_verified=False,
            installed_whole_edge_length_mm=None, human_accepted=False))
    return dict(mode=MODE, status='source_checked_named_floor_approach_DN_and_XY_projection_not_fused',
                source_sha256=sh, graph_sha256=gh, mapping_sha256=sha(paths['mapping']), records=records,
                source_preflight=preflight, source_annotation_inventory=inventory, named_riser_annotation_domain=domain,
                topology_contract=contract, diameter_scope=dn, metric_evidence=units, path_coverage=coverage,
                local_graphs_mutated=False, physical_ports_verified=False, physical_values_fused=False,
                installed_lengths_assigned=0, human_accepted=False)


def implementation_hashes():
    from match_named_riser_floor_paths import implementation_hashes as mapping_hashes
    from plan_pipe_diameter_scopes import implementation_hashes as inherited_hashes
    result = inherited_hashes(); result.update(mapping_hashes())
    for name in ('named_riser_plan_attributes.py', 'checked_plan_DN_scope_attributes.py',
                 'source_checked_plan_path_coverage.py', 'native_plan_projection_lengths.py'):
        result[name] = sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory = Path(directory); receipt = load(directory / 'named-riser-plan-attribute-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('named plan attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('named plan attribute input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    result = compute(paths, load(paths['policy']))
    target = directory / 'named-riser-plan-attributes.json'
    if encode(result) != target.read_bytes() or sha(target) != receipt['output_sha256']:
        raise ValueError('named plan attribute native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('source', 'graph', 'mapping-run', 'policy', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    a = parser.parse_args()
    paths = dict(source=a.source, graph=a.graph, mapping=a.mapping_run / 'mapping.json',
                 mapping_receipt=a.mapping_run / 'named-riser-mapping-receipt.json', policy=a.policy)
    if a.output.exists():
        raise FileExistsError(a.output)
    result = compute(paths, load(a.policy)); a.output.mkdir(parents=True)
    target = a.output / 'named-riser-plan-attributes.json'; target.write_bytes(encode(result))
    (a.output / 'named-riser-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(dict(named_plan_approaches=len(result['records']), physical_values_fused=False), flush=True)


if __name__ == '__main__':
    main()
