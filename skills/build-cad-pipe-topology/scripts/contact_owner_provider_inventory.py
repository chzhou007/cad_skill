"""Inherit every prior provider and scoped qualification after native contacts."""
import argparse,collections,copy,importlib,sys
from pathlib import Path
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
MODE='qualified_native_contact_owner_complete_provider_inventory_v1'

def inherit(original,proof,effective,source_inventory):
    if any(proof.get(key)is not True for key in ('complete_current_parent_replayed','native_owner_inventory_replayed','all_affected_old_scopes_requalified','pipe_graph_restoration_exact'))or proof.get('human_accepted')is not False:raise ValueError('complete native contact application required')
    result=copy.deepcopy(original);rows={row['edge_id']:row for row in result['records']};values={row['edge_id']:row['values']for row in effective};attributes={row['axis_edge_id']:row for row in proof['attribute_records']}
    if rows.keys()!=values.keys()or len(attributes)!=len(proof['attribute_records']):raise ValueError('contact provider population differs')
    source={row['iso_edges'][0]:row for row in proof['source_batch']['records']}
    if source.keys()!=attributes.keys():raise ValueError('contact provider omitted a source path')
    for eid,application in attributes.items():
        row=rows[eid];native=source[eid]
        if row['has_existing_correspondence']or row['correspondence_observations']or native['mapping_id']!=application['mapping_id']or values[eid].get('contact_owner_mapping_id')!=application['mapping_id']:raise ValueError('contact path conflicts with an old provider or effective output')
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(dict(provider='native_contact_owner_requalified_paths',domain='ordinary_local_graph',mapping_id=application['mapping_id'],plan_edges=[application['plan_edge_id']],grouped_axis_edges=[eid],floor=application['floor']))
    mapping=result['ordinary_junction_mappings'][str(proof['floor'])];added=proof['source_batch']['native_bounded_batch']['new_junction_mapping']
    for p,a in added.items():
        if p in mapping or a in mapping.values():raise ValueError('contact source anchor competes with an old junction')
        mapping[p]=a
    oldfront={row['edge_id']:row for row in original['remaining_horizontal_attributes']};remaining=[];complete=[];lengths=0
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid]
        if v.get('contact_owner_mapping_id'):known=v.get('contact_owner_plan_DN_mm')
        elif v.get('cohort_member_mapping_id'):known=v.get('cohort_member_plan_DN_mm')
        elif v.get('riser_header_mapping_id'):known=v.get('riser_header_plan_DN_mm')
        else:known=v.get('diameter_nominal_mm')
        length=any(positive(v.get(key))for key in COMPLETE_FIELDS+('cycle_gate_complete_centerline_mm','riser_header_complete_centerline_mm','cohort_member_complete_centerline_mm','contact_owner_complete_centerline_mm'));lengths+=bool(length)
        if positive(known)and length:complete.append(eid);continue
        if eid not in oldfront:raise ValueError('contact application regressed an old completed horizontal edge')
        pending=copy.deepcopy(oldfront[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']),known_whole_DN=known if positive(known)else None,complete_centerline=length)
        if eid in attributes:
            application=attributes[eid];pending.update(existing_mapping_id=application['mapping_id'],existing_plan_edges=[application['plan_edge_id']],next_scope='known_contact_owner_plan_DN_conflict'if application['nominal_mm']is None else'known_contact_owner_plan_length_incomplete')
        remaining.append(pending)
    if result['member_domain_observations']!=original['member_domain_observations']:raise ValueError('contact application changed a member namespace')
    result['prior_component_inventory_before_contact']=copy.deepcopy(original['current_component_inventory'])
    unresolved=[copy.deepcopy(row)for row in source_inventory['records']if row['status']not in ('existing_native_owner_agrees','native_contact_owner_reapplied')]
    result.update(mode=MODE,remaining_horizontal_attributes=remaining,current_component_inventory=dict(native_inventory=copy.deepcopy(proof['inputs']['native_owner_proof']),native_axis_graph=copy.deepcopy(source_inventory['inputs']['graph']),rendered_graph_sha256=proof['rendered_graph_sha256'],rendered_components=proof['counts']['output_components'],newly_adopted_source_components=proof['counts']['added_components'],reassigned_component_owners=proof['counts']['reassigned_components'],requalified_old_edge_scopes=proof['existing_scope_requalification']['requalified_old_axis_edges'],unresolved_native_components=unresolved,unresolved_balancing_sources=0),new_contact_owner_axis_edges=sorted(attributes),new_contact_owner_ordinary_junctions=copy.deepcopy(added),all_prior_providers_and_member_namespaces_preserved=True,all_affected_old_scopes_requalified=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(row['has_existing_correspondence']for row in rows.values()),pure_horizontal_complete_DN_and_centerline=len(complete),pure_horizontal_complete_centerline=lengths,pure_horizontal_remaining_attributes=len(remaining),horizontal_next_scopes=dict(collections.Counter(row['next_scope']for row in remaining)),rendered_component_instances=proof['counts']['output_components'],newly_adopted_component_instances=proof['counts']['added_components'],native_component_ownership_unresolved=len(unresolved),reassigned_component_owners=proof['counts']['reassigned_components'])
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='all_prior_and_native_contact_owner_providers_inherited',pure_horizontal_complete=len(complete),pure_horizontal_complete_centerline=lengths,pure_horizontal_remaining_attributes=len(remaining),remaining_by_floor=dict(sorted(collections.Counter(str(row['floor'])for row in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining);result['current_horizontal_frontier']=frontier
    return result

def compute(manifest):
    from refresh_native_contact_application import verify,base
    inputs=manifest['inputs'];paths={key:Path(value['path'])for key,value in inputs.items()}
    def checked():
        if any(sha(paths[key])!=value['sha256']for key,value in inputs.items()):raise ValueError('contact provider input changed')
    checked();bundle=paths['viewer_manifest'].parents[2]
    if verify(bundle)['artifact_replay']!='passed':raise ValueError('contact viewer failed replay')
    proof=load(paths['native_proof'])
    if proof['inputs']['current_provider']!=inputs['original_inventory']:raise ValueError('contact complete provider ancestry differs')
    source=load(proof['inputs']['native_owner_proof']['path']);result=inherit(load(paths['original_inventory']),proof,base.effective_attributes(bundle),source)
    checked();return dict(result,inputs=inputs,current_viewer_and_complete_original_provider_replayed=True)

def implementation_hashes():return dict(entry=sha(__file__),**{name:sha(importlib.import_module(name).__file__)for name in ('refresh_native_contact_application','rebuild_native_contact_application','alias_aware_provider_inventory')})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest))
    if before!=implementation_hashes():raise ValueError('contact provider code changed')
    output.mkdir(parents=True);path=output/'provider-inventory.json';path.write_bytes(encode(result));(output/'horizontal-frontier.json').write_bytes(encode(result['current_horizontal_frontier']));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(path))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');manifest=receipt['manifest'];path=output/'provider-inventory.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(manifest['path'])!=manifest['sha256']or sha(path)!=receipt['output_sha256']:raise ValueError('contact provider receipt changed')
    result=compute(load(manifest['path']))
    if encode(result)!=path.read_bytes()or encode(result['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('contact provider replay differs')
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ('manifest','output','verify-output'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.verify_output:result=verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
        result=produce(args.manifest,args.output)
    print(result['counts'],flush=True)

if __name__=='__main__':main()
