"""Inherit source-qualified ordinary intervals without flattening member graphs."""
import argparse, collections, copy, importlib, sys
from pathlib import Path
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    path=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if path not in sys.path:sys.path.insert(0,path)
from confirm_crossview_paths import load,sha,encode
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
MODE='qualified_equivalent_cohort_member_provider_inventory_v1'


def inherit(original,application,batch,effective):
    result=copy.deepcopy(original)
    rows={r['edge_id']:r for r in result['records']}
    values={r['edge_id']:r['values']for r in effective}
    targets={r['axis_edge_id']:r for r in application['records']}
    if rows.keys()!=values.keys()or len(rows)!=len(result['records'])or len(values)!=len(effective)or len(targets)!=len(application['records']):raise ValueError('cohort provider edge population differs')
    if batch['complete_parent_rechecked']is not True or application['complete_source_batch_replayed']is not True or application['human_accepted']is not False:raise ValueError('complete native cohort application required')
    source_rows={r['iso_edges'][0]:r for r in batch['records']}
    if targets.keys()!=source_rows.keys():raise ValueError('cohort provider omitted a native interval')
    additions=[]
    for eid,r in targets.items():
        row=rows[eid];v=values[eid];source=source_rows[eid]
        if row['classification']!='horizontal_only'or row['has_existing_correspondence']or row['correspondence_observations']:raise ValueError('cohort interval competes with an old provider or vertical scope')
        if source['mapping_id']!=r['mapping_id']or source['plan_edges']!=[r['plan_edge_id']]or v.get('cohort_member_mapping_id')!=r['mapping_id']or v.get('cohort_member_plan_DN_mm')!=(r['nominal_mm']if r['nominal_mm']is not None else'')or v.get('cohort_member_complete_centerline_mm')!=(r['complete_horizontal_centerline_mm']if r['complete_horizontal_centerline_mm']is not None else''):raise ValueError('cohort effective attributes differ from native source')
        observation=dict(provider='complete_native_equivalent_source_cohort',domain='ordinary_local_graph',mapping_id=r['mapping_id'],plan_edges=[r['plan_edge_id']],grouped_axis_edges=[eid],floor=r['floor'],source_member_observation_ids=copy.deepcopy(r['source_member_observation_ids']))
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(observation);additions.append(copy.deepcopy(observation))
    mapping=result['ordinary_junction_mappings'][str(batch['floor'])]
    for plan,axis in batch['native_bounded_batch']['new_junction_mapping'].items():
        if plan in mapping or axis in mapping.values():raise ValueError('new ordinary junction conflicts with an inherited identity')
        mapping[plan]=axis
    oldfront={r['edge_id']:r for r in original['remaining_horizontal_attributes']}
    remaining=[];complete=[];length_count=0
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid]
        if v.get('cohort_member_mapping_id'):known=v.get('cohort_member_plan_DN_mm')
        elif v.get('riser_header_mapping_id'):known=v.get('riser_header_plan_DN_mm')
        else:known=v.get('diameter_nominal_mm')
        length=any(positive(v.get(k))for k in COMPLETE_FIELDS+('cycle_gate_complete_centerline_mm','riser_header_complete_centerline_mm','cohort_member_complete_centerline_mm'))
        length_count+=bool(length)
        if positive(known)and length:complete.append(eid);continue
        if eid not in oldfront:raise ValueError('old horizontal completeness regressed')
        pending=copy.deepcopy(oldfront[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']),known_whole_DN=known if positive(known)else None,complete_centerline=length)
        if eid in targets:
            r=targets[eid]
            pending.update(existing_mapping_id=r['mapping_id'],existing_plan_edges=[r['plan_edge_id']],next_scope='known_cohort_plan_DN_conflict'if r['DN_status']=='native_plan_DN_conflict'else'known_cohort_plan_length_incomplete'if positive(known)else'known_cohort_native_DN_application_pending')
        remaining.append(pending)
    if result['member_domain_observations']!=original['member_domain_observations']:raise ValueError('ordinary cohort changed a reconstructed member namespace')
    result.update(mode=MODE,new_cohort_axis_edges=sorted(targets),new_cohort_ordinary_observations=additions,new_cohort_ordinary_junctions=copy.deepcopy(batch['native_bounded_batch']['new_junction_mapping']),remaining_horizontal_attributes=remaining,all_old_provider_observations_preserved=True,member_namespaces_preserved=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),pure_horizontal_complete_DN_and_centerline=len(complete),pure_horizontal_complete_centerline=length_count,pure_horizontal_remaining_attributes=len(remaining),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='all_published_equivalent_cohort_and_prior_providers_inherited',pure_horizontal_complete=len(complete),pure_horizontal_remaining_attributes=len(remaining),pure_horizontal_complete_centerline=length_count,remaining_by_floor=dict(sorted(collections.Counter(str(r['floor'])for r in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining);result['current_horizontal_frontier']=frontier
    return result


def compute(manifest):
    from refresh_cohort_member_attributes import verify,base
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in inputs.items()):raise ValueError('cohort inventory input changed')
    checked();bundle=paths['viewer_manifest'].parents[2]
    # The viewer verifier recomputes the new source owner, including the full
    # original provider with current transitive dependency checks.
    if verify(bundle)['artifact_replay']!='passed':raise ValueError('cohort viewer did not replay')
    application=load(paths['application_proof']);batch=load(paths['batch_proof'])
    if application['inputs']['batch_proof']!=inputs['batch_proof']or batch['inputs']['parent_inventory']!=inputs['original_inventory']:raise ValueError('cohort provider source ancestry differs')
    context=load(paths['viewer_manifest'])['attributeValueContext']['equivalent_member_application']
    if context['source_proof_sha256']!=inputs['application_proof']['sha256']or context['records']!=application['records']:raise ValueError('cohort inventory uses another viewer application')
    result=inherit(load(paths['original_inventory']),application,batch,base.effective_attributes(bundle));checked()
    result.update(inputs=inputs,current_viewer_and_complete_original_inventory_replayed=True)
    return result


def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('refresh_cohort_member_attributes','apply_equivalent_member_plan_attributes','rebuild_equivalent_member_bounded_batch','alias_aware_provider_inventory')})


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('cohort provider implementation changed')
    output.mkdir(parents=True);p=output/'provider-inventory.json';p.write_bytes(encode(r));(output/'horizontal-frontier.json').write_bytes(encode(r['current_horizontal_frontier']));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r


def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'provider-inventory.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('cohort provider receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes()or encode(r['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('cohort provider independent replay differs')
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
