"""Requalify existing two-view scopes after a reviewed native main partition.

The original namespace, source graphs and mappings remain. Both local source
paths, T rays and equipment services are freshly read; DN never selects a match.
"""
import argparse, copy, csv, importlib
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from legacy_named_provider_inventory import require
from reviewed_ring_main_partition import verify_output as verify_partition
from match_source_checked_crossview_paths import selected_snapshot
from anchored_cycle_gate_matching import discover
from crossview_equipment_branch_inventory import native_tee
from batch_native_path_coverage import collect as coverage
from fresh_reviewed_plan_inventory import inspect_view
from source_readability import read_source
from extend_native_main_chain_batch import implementation_hashes as early_hashes
from rebuild_anchored_cycle_gate_batch import implementation_hashes as cycle_hashes

MODE = 'native_reviewed_ring_existing_crossview_DN_v1'


def select_scopes(provider, axis, source_rows, floor):
    """Local edge IDs repeat across drawings; a bare E0054 is never an anchor."""
    edges = {e['edge_id']: e for e in axis['edges']}
    candidates=[]; excluded=[]
    for r in provider['records']:
        edge = edges[r['edge_id']]
        for observation in r['correspondence_observations']:
            if not set(observation.get('plan_edges', [])) & set(source_rows): continue
            if (observation.get('floor', edge.get('floor_start')) != floor
                    or edge.get('floor_start') != floor or edge.get('floor_end') != floor):
                excluded.append(dict(axis_edge_id=r['edge_id'], observation=copy.deepcopy(observation),
                    reason='same_local_edge_ID_in_another_drawing_not_this_source_scope'))
                continue
            require(len(observation['plan_edges']) == 1
                    and observation.get('grouped_axis_edges') == [r['edge_id']],
                    'reviewed DN needs the original one-to-one path owner')
            pe = observation['plan_edges'][0]
            require(source_rows[pe]['system'] == edge['system'], 'existing mapping crosses source systems')
            candidates.append(dict(axis_edge_id=r['edge_id'], plan_edge_id=pe,
                classification=r['classification'], original_observation=copy.deepcopy(observation)))
    require(len({r['axis_edge_id'] for r in candidates}) == len(candidates), 'competing existing DN scope writers')
    return candidates, excluded


def csvrows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        require(all(sha(v['path']) == v['sha256'] for v in inputs.values()), 'reviewed crossview input changed')
    checked(); partition = verify_partition(Path(inputs['partition']['path']).parent)
    floor = manifest['floor']; source_rows = {r['edge_id']: r for r in partition['records']}
    require(partition['inputs']['current_graph'] == inputs['plan_graph']
            and partition['inputs']['source'] == inputs['plan_source'], 'crossview uses another reviewed source')
    plan, axis = load(inputs['plan_graph']['path']), load(inputs['axis_graph']['path'])
    rendered = load(inputs['rendered_graph']['path']); parent_manifest = load(inputs['viewer_manifest']['path'])
    require(parent_manifest['attributeValueContext']['current_rendered_graph_sha256'] == inputs['rendered_graph']['sha256'],
            'current viewer source binding differs')
    by_axis={e['edge_id']:e for e in axis['edges']}; by_rendered={e['edge_id']:e for e in rendered['edges']}
    candidates, excluded = select_scopes(load(inputs['provider']['path']), axis, source_rows, floor)
    early, cycle = load(inputs['early_mapping']['path']), load(inputs['cycle_mapping']['path'])
    er, cr = load(inputs['early_receipt']['path']), load(inputs['cycle_receipt']['path'])
    require(er['output_sha256'] == inputs['early_mapping']['sha256'] and er['implementation_sha256'] == early_hashes(),
            'original early source mapping artifact or owner changed')
    require(cr['output_sha256'] == inputs['cycle_mapping']['sha256'] and cr['implementation_sha256'] == cycle_hashes(),
            'original cycle source mapping artifact or owner changed')
    require(early['identity_graph_sha256'] == inputs['axis_graph']['sha256'], 'early local axis graph changed')
    require(cycle['inputs']['plan_graph_'+str(floor)] == inputs['plan_graph']
            and cycle['inputs']['axis_graph'] == inputs['axis_graph'], 'cycle local source scope changed')
    require(sha(cycle['inputs']['inventory']['path']) == cycle['inputs']['inventory']['sha256'],
            'original independent cycle anchors changed')
    anchors = load(cycle['inputs']['inventory']['path'])['ordinary_junction_mappings'][str(floor)]
    discovery = discover(dict(plan=plan,iso=axis), anchors, floor)
    require(discovery['new_junction_mapping'] == cycle['floors'][str(floor)]['discovery']['new_junction_mapping'],
            'fresh original cycle-gate discovery differs')
    extended = dict(anchors, **discovery['new_junction_mapping'])
    docs={}; readable={}
    for view,prefix in [('plan','plan'),('iso','axis')]:
        docs[view], readable[view] = read_source(inputs[prefix+'_source']['path'])
    old_rows = {r['mapping_id']:r for r in early['floors'][str(floor)]['records']}
    old_rows.update({r['mapping_id']:r for r in cycle['floors'][str(floor)]['records']})
    branches={}; records=[]; ai=csvrows(inputs['axis_components']['path'])
    for candidate in candidates:
        eid,pe = candidate['axis_edge_id'],candidate['plan_edge_id']; observation=candidate['original_observation']
        row=old_rows.get(observation['mapping_id']); require(row is not None, 'existing mapping lacks its original owner')
        require(row['floor']==floor and row['plan_edges']==[pe] and row['iso_edges']==[eid]
                and row['system']==source_rows[pe]['system'], 'old mapping scope differs')
        edge=by_axis[eid]
        require(all(edge.get(k)==by_rendered[eid].get(k) for k in
            ('system','start_node_id','end_node_id','attribute_paths','floor_start','floor_end')), 'rendered local axis geometry changed')
        if 'plan_snapshot' in row:
            require(selected_snapshot(plan,[pe])==row['plan_snapshot'] and selected_snapshot(axis,[eid])==row['iso_snapshot'],
                    'original matched endpoint or path snapshots changed')
        else:
            require(extended.get(row['plan_start'])==row['iso_start'] and extended.get(row['plan_end'])==row['iso_end'],
                    'cycle interval does not belong to freshly discovered independent gates')
        source = {}
        for view,prefix,graph,ids in [('plan','plan',plan,[pe]),('iso','axis',axis,[eid])]:
            sh,gh=inputs[prefix+'_source']['sha256'],inputs[prefix+'_graph']['sha256']
            cov=coverage(docs[view],graph,ids,sh,gh)
            require(not cov['unresolved'] and all(s['status']=='single_source_line_covers'
                    for e in cov['edges'] for s in e['segments']), 'mapped interval lacks complete unique native LINE coverage')
            tees={}; selected=next(e for e in graph['edges'] if e['edge_id']==ids[0])
            for nid in (selected['start_node_id'],selected['end_node_id']):
                node=next(n for n in graph['nodes'] if n['node_id']==nid)
                if node.get('node_type')in ('tee','physical_junction'):
                    if view=='plan':
                        # The partition producer replayed the original/current
                        # source-stable reader on this exact scope already.
                        tees[nid]=source_rows[pe]['current_native_T'][nid]
                    else:tees[nid]=native_tee(docs[view],graph,nid,sh,gh)
            source[view]=dict(native_path=cov,native_T=tees)
        if row['kind']=='equipment_branch':
            did=row['equipment_id']
            if did not in branches:
                branches[did]={v:inspect_view(docs[v],g,did,floor,
                    dict(source_sha256=inputs[p+'_source']['sha256'],graph_sha256=inputs[p+'_graph']['sha256']),v,ai)
                    for v,p,g in [('plan','plan',plan),('iso','axis',axis)]}
            for view in ('plan','iso'):
                service=branches[did][view]['services'][row['system']]
                require(service.get('ready_for_mapping_comparison')is True and service['trace']['edges']==row[view+'_edges']
                        and service['trace']['tee']==row[view+'_start'], 'fresh native equipment branch does not reproduce original endpoints')
        value=source_rows[pe]['nominal_mm']; whole=candidate['classification']=='horizontal_only'
        require(whole or candidate['classification']=='mixed_horizontal_vertical', 'unsupported reviewed axis direction domain')
        records.append(dict(candidate, mapping_id=row['mapping_id'], floor=floor, system=row['system'],
            axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
            current_mapping=copy.deepcopy(row), plan_DN_record=copy.deepcopy(source_rows[pe]), nominal_mm=value,
            whole_axis_nominal_mm=value if whole else None,
            mixed_plan_value_scope=None if whole else 'corresponding_drawn_plan_branch_not_individual_axis_horizontal_subsegments',
            native_mapping_evidence=source, source_sha256=dict(plan=inputs['plan_source']['sha256'],iso=inputs['axis_source']['sha256']),
            graph_sha256=dict(plan=inputs['plan_graph']['sha256'],iso=inputs['axis_graph']['sha256']),
            DN_used_for_mapping=False, physical_length_mm=None, installed_whole_edge_length_mm=None,
            per_axis_horizontal_subsegment_allocation_inferred=False, vertical_DN_assigned=False,
            related_HIL_confirmation_inherited=False, human_accepted=False))
    require({r['plan_edge_id'] for r in records}==set(source_rows), 'some reviewed source scopes lack qualified current mapping')
    checked()
    return dict(mode=MODE, inputs=inputs, records=records, excluded_other_drawing_ID_collisions=excluded,
        native_cycle_gate_discovery=discovery, native_equipment_services=branches, source_preflight=readable,
        inherited_complete_parent_artifacts_not_claimed_as_new_full_rebuild=True,
        existing_mappings_source_requalified=True, new_correspondences_assigned=0, source_graphs_mutated=False,
        old_native_mapping_IDs_preserved=True, DN_used_for_mapping=False, physical_lengths_assigned=0,
        vertical_values_assigned=0, counts=dict(source_scopes=len(source_rows),qualified_axis_scopes=len(records),
            whole_horizontal_DN=sum(r['whole_axis_nominal_mm']is not None for r in records),
            mixed_plan_branch_DN=sum(r['whole_axis_nominal_mm']is None for r in records),
            other_drawing_ID_collisions_excluded=len(excluded)), human_accepted=False, whole_goal_complete=False)


def implementations():
    names=('reviewed_ring_main_partition','anchored_cycle_gate_matching','match_source_checked_crossview_paths',
           'fresh_reviewed_plan_inventory','crossview_equipment_branch_inventory','batch_native_path_coverage','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})


def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh reviewed mapping output required')
    code=implementations();proof=compute(load(manifest));require(code==implementations(),'reviewed mapping implementation changed')
    output.mkdir(parents=True);p=output/'reviewed-ring-crossview-DN.json';p.write_bytes(encode(proof))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(p))))
    return proof


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');p=output/'reviewed-ring-crossview-DN.json'
    require(r['mode']==MODE and r['implementation_sha256']==implementations()
        and sha(r['manifest']['path'])==r['manifest']['sha256']and sha(p)==r['output_sha256'],'reviewed mapping receipt changed')
    proof=compute(load(r['manifest']['path']));require(encode(proof)==p.read_bytes(),'independent reviewed source/mapping replay differs')
    return proof


def main():
    p=argparse.ArgumentParser()
    for k in ('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        proof=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(proof['counts'],flush=True)


if __name__=='__main__':main()
