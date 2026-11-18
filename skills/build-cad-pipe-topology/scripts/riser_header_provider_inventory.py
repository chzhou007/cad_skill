"""Inherit adopted members and cleared cycles before further discovery."""
import argparse,collections,copy,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
MODE='qualified_reanchored_riser_header_provider_inventory_v1'

def inherit(original,application,effective):
    result=copy.deepcopy(original);rows={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective}
    if rows.keys()!=values.keys()or len(rows)!=len(result['records'])or len(values)!=len(effective):raise ValueError('riser provider edge population differs')
    cleared={r['axis_edge_id']:r for r in application['cycle_clearances']};members={r['axis_edge_id']:r for r in application['member_records']}
    if set(cleared)&set(members):raise ValueError('competing member/cycle inventory writers')
    for eid,r in cleared.items():
        row=rows[eid];observations=row.get('graphic_candidate_correspondence_observations',[]);v=values[eid]
        if row['has_existing_correspondence']or row['correspondence_observations']or len(observations)!=1 or observations[0]['mapping_id']!=r['mapping_id']or v.get('cycle_gate_mapping_id')!=r['mapping_id']or v.get('cycle_gate_complete_centerline_mm')!=r['complete_horizontal_centerline_mm']or v.get('cycle_carrier_clearance_status')!='native_atom_origin_replayed_scope_cleared':raise ValueError('cleared cycle inventory differs from effective source')
        row.update(has_existing_correspondence=True,correspondence_observations=copy.deepcopy(observations),physical_member_identity_pending=False,prior_graphic_candidate_history_preserved=True)
    if set(cleared)!=set(original['held_cycle_axis_edges']):raise ValueError('partial clearance needs explicit remaining anchor ownership')
    for f,mapping in original['held_graphic_junction_mappings'].items():
        current=result['ordinary_junction_mappings'][f]
        for p,a in mapping.items():
            if p in current or a in current.values():raise ValueError('restored ordinary gate conflicts with existing identity')
            current[p]=a
    additions=[]
    for eid,r in members.items():
        row=rows[eid];v=values[eid]
        if row['has_existing_correspondence']or row['correspondence_observations']or v.get('riser_header_mapping_id')!=r['mapping_id']or v.get('riser_header_member_scope')!=r['member_scope_id']:raise ValueError('riser member competes with an old provider')
        observation=dict(provider='reanchored_riser_header_members',domain='reconstructed_member_graph',mapping_id=r['mapping_id'],member_scope_id=r['member_scope_id'],plan_edges=[r['plan_member_edge_id']],grouped_axis_edges=[eid],floor=r['floor'])
        row.update(has_existing_correspondence=True);row['correspondence_observations'].append(observation);additions.append(copy.deepcopy(observation))
    oldfront={r['edge_id']:r for r in original['remaining_horizontal_attributes']};remaining=[];complete=[];lengths=0
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid];known=v.get('riser_header_plan_DN_mm')if v.get('riser_header_mapping_id')else v.get('diameter_nominal_mm');length=any(positive(v.get(k))for k in COMPLETE_FIELDS+('cycle_gate_complete_centerline_mm','riser_header_complete_centerline_mm'));lengths+=bool(length)
        if positive(known)and length:complete.append(eid);continue
        if eid not in oldfront:raise ValueError('old horizontal completeness regressed')
        pending=copy.deepcopy(oldfront[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']),known_whole_DN=known if positive(known)else None,complete_centerline=length)
        if eid in members:pending.update(existing_mapping_id=members[eid]['mapping_id'],existing_plan_edges=[members[eid]['plan_member_edge_id']],next_scope='known_riser_member_connector_length_unproved'if positive(known)else'known_riser_member_DN_conflict')
        elif eid in cleared:pending.update(existing_mapping_id=cleared[eid]['mapping_id'],next_scope='known_cycle_correspondence_plan_DN_application_pending')
        remaining.append(pending)
    old_members=copy.deepcopy(original['member_domain_observations']);result.update(mode=MODE,member_domain_observations=old_members+additions,remaining_horizontal_attributes=remaining,held_cycle_axis_edges=[],held_graphic_junction_mappings={},new_cycle_axis_edges=sorted(set(original['new_cycle_axis_edges'])|set(cleared)),new_riser_member_axis_edges=sorted(members),newly_inherited_riser_members=len(members),restored_qualified_cycle_observations=len(cleared),member_namespaces_preserved=True,old_member_observations_prefix_unchanged=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),member_domain_observations=len(result['member_domain_observations']),pure_horizontal_complete_DN_and_centerline=len(complete),pure_horizontal_complete_centerline=lengths,pure_horizontal_remaining_attributes=len(remaining),held_graphic_cycle_candidates=0,held_graphic_junction_candidates=0,horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='all_published_riser_member_and_cleared_cycle_providers_inherited',pure_horizontal_complete=len(complete),pure_horizontal_remaining_attributes=len(remaining),pure_horizontal_complete_centerline=lengths,remaining_by_floor=dict(sorted(collections.Counter(str(r['floor'])for r in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining,held_graphic_cycle_candidates=0);result['current_horizontal_frontier']=frontier
    return result

def compute(manifest):
    from refresh_riser_header_attributes import verify,base
    from guarded_cycle_provider_inventory import verify_output as old_owner
    from native_replay_session import verify_once
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in inputs.items()):raise ValueError('riser inventory input changed')
    checked();bundle=paths['viewer_manifest'].parents[2]
    if verify(bundle)['artifact_replay']!='passed':raise ValueError('riser viewer did not replay')
    original=verify_once(paths['original_inventory'].parent,old_owner)
    if encode(original)!=paths['original_inventory'].read_bytes():raise ValueError('old complete provider inventory differs')
    m=load(paths['viewer_manifest']);ctx=m['attributeValueContext']['riser_header_application']
    if ctx['source_proof_sha256']!=sha(paths['application_proof']):raise ValueError('riser inventory uses another source proof')
    r=inherit(original,ctx,base.effective_attributes(bundle));checked();r.update(inputs=inputs,current_viewer_and_original_provider_inventory_replayed=True)
    return r
def implementation_hashes():return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('refresh_riser_header_attributes','guarded_cycle_provider_inventory','alias_aware_provider_inventory')})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('riser provider implementation changed')
    output.mkdir(parents=True);p=output/'provider-inventory.json';p.write_bytes(encode(r));(output/'horizontal-frontier.json').write_bytes(encode(r['current_horizontal_frontier']));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'provider-inventory.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('riser provider receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes()or encode(r['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('riser provider independent replay differs')
    return r
