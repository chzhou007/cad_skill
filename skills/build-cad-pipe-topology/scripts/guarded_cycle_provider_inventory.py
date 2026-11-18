"""Keep drawing candidates distinct from usable physical cycle mappings."""
import argparse,collections,copy,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
MODE='qualified_guarded_cycle_provider_inventory_v1'

def inherit(original,cycles,guards,effective):
    result=copy.deepcopy(original);rows={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective};held={r['axis_edge_id']:r for r in guards['records']}
    if rows.keys()!=values.keys()or len(rows)!=len(result['records'])or len(values)!=len(effective)or not held.keys()<=set(original['new_cycle_axis_edges']):raise ValueError('guarded provider inventory identity differs')
    held_anchors={}
    for f,group in cycles['floors'].items():
        touched={p for r in group['records']if r['iso_edges'][0]in held for p in(r['plan_start'],r['plan_end'])}
        kept={p:a for p,a in group['new_junction_mapping'].items()if p in touched}
        for p,a in kept.items():
            if result['ordinary_junction_mappings'][f].get(p)!=a:raise ValueError('held graphic anchor differs from original')
            del result['ordinary_junction_mappings'][f][p]
        if kept:held_anchors[f]=kept
    for eid,h in held.items():
        row=rows[eid];obs=row['correspondence_observations'];v=values[eid]
        if len(obs)!=1 or obs[0]['provider']!='cycle_gate_plan_runs'or obs[0]['mapping_id']!=h['mapping_id']or v.get('cycle_carrier_hold_status')!='physical_member_identity_unproved'or any(k.startswith('cycle_gate_')for k in v):raise ValueError('held cycle provider remains active or is another namespace')
        row.update(has_existing_correspondence=False,graphic_candidate_correspondence_observations=copy.deepcopy(obs),correspondence_observations=[],physical_member_identity_pending=True)
    remaining=copy.deepcopy(original['remaining_horizontal_attributes'])
    for row in remaining:
        eid=row['edge_id'];row['attributes']=copy.deepcopy(values[eid])
        if eid in held:row.update(next_scope='compound_carrier_member_identity_before_physical_mapping',complete_centerline=False,existing_mapping_id=None,correspondence_observations=[],graphic_candidate_correspondence_observations=copy.deepcopy(rows[eid]['graphic_candidate_correspondence_observations']))
    result.update(mode=MODE,records=list(rows.values()),remaining_horizontal_attributes=remaining,held_cycle_axis_edges=sorted(held),held_graphic_junction_mappings=held_anchors,new_cycle_axis_edges=sorted(set(original['new_cycle_axis_edges'])-held.keys()),
        newly_inherited_cycle_correspondences=len(set(original['new_cycle_axis_edges'])-held.keys()),historical_cycle_source_readings_retained=True,physical_member_identity_required_before_reapplication=True,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),held_graphic_cycle_candidates=len(held),held_graphic_junction_candidates=sum(len(x)for x in held_anchors.values()),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    frontier=copy.deepcopy(result['current_horizontal_frontier']);frontier.update(status='guarded_physical_mapping_frontier_graphic_candidates_separate',records=remaining,remaining_by_next_scope=result['counts']['horizontal_next_scopes'],held_graphic_cycle_candidates=len(held));result['current_horizontal_frontier']=frontier
    if result['member_domain_observations']!=original['member_domain_observations']:raise ValueError('old member observations changed')
    return result

def compute(manifest):
    from refresh_cycle_carrier_guards import verify,base
    from graph_first_provider_inventory import verify_output as verify_original
    from native_replay_session import verify_once
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('guarded inventory input changed')
    checked();bundle=paths['viewer_manifest'].parents[2];replay=verify(bundle)
    if replay['artifact_replay']!='passed':raise ValueError('corrected viewer not independently qualified')
    original=verify_once(paths['original_inventory'].parent,verify_original)
    if encode(original)!=paths['original_inventory'].read_bytes()or original['inputs']['cycle_proof']['sha256']!=sha(paths['cycle_proof']):raise ValueError('original provider/cycle source differs')
    context=load(paths['viewer_manifest'])['attributeValueContext']['cycle_carrier_guards']
    if context['source_proof_sha256']!=sha(paths['guard_proof']):raise ValueError('corrected viewer uses another carrier guard')
    result=inherit(original,load(paths['cycle_proof']),context,base.effective_attributes(bundle));checked()
    result.update(inputs=manifest['inputs'],corrected_viewer_and_all_original_providers_replayed=True)
    return result
def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('refresh_cycle_carrier_guards','cycle_carrier_guards','graph_first_provider_inventory')})
def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    r=compute(load(manifest_path));output.mkdir(parents=True);p=output/'provider-inventory.json';p.write_bytes(encode(r));(output/'horizontal-frontier.json').write_bytes(encode(r['current_horizontal_frontier']));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'provider-inventory.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('guarded provider receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('guarded provider replay differs')
    return r
