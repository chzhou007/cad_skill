"""Inherit every current provider, including separately qualified alias bridges."""
import argparse,collections,copy,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
MODE='qualified_alias_bridge_aware_provider_inventory_v1'

def inventory(original,proof,context,effective,baseline,bindings):
    from alias_aware_provider_inventory import MODE as PRIOR_MODE
    from alias_member_inline_bridges import MODE as SOURCE_MODE
    from alias_member_bridge_context import MODE as CONTEXT_MODE
    if original.get('mode')!=PRIOR_MODE or proof.get('mode')!=SOURCE_MODE or context.get('mode')!=CONTEXT_MODE or context['source_bindings']['native_proof']!=bindings['native_proof']or proof['source_hashes']['member_interfaces']!=original['source_bindings']['native_proof']:raise ValueError('bridge inventory native ancestry differs')
    if original.get('new_correspondences_assigned')!=0 or proof.get('human_accepted')is not False or context.get('human_accepted')is not False:raise ValueError('unqualified bridge inventory ancestry')
    result=copy.deepcopy(original);rows={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective};old_front={r['edge_id']:r for r in baseline['records']}
    if len(rows)!=len(result['records'])or len(values)!=len(effective)or rows.keys()!=values.keys():raise ValueError('actual current bridge edge inventory differs')
    targets={r['axis_edge_id']:r for r in proof['records']};current={r['axis_edge_id']:r for r in context['records']};members={e['edge_id']for e in proof['member_local_graph']['edges']}
    if targets.keys()!=current.keys()or len(targets)!=len(proof['records'])or len(current)!=len(context['records']):raise ValueError('bridge source and current provider populations differ')
    added=[]
    for eid,p in targets.items():
        c=current[eid];member=p['plan_member_edge_id'];row=rows[eid]
        if not member.startswith('MEMBER-BRIDGE:')or member not in members or c['mapping_id']!=p['mapping_id']or c['plan_member_edge_id']!=member:raise ValueError('bridge member identity differs')
        if row['has_existing_correspondence']or row['correspondence_observations']:raise ValueError('bridge competes with an original provider')
        observation=dict(provider='alias_member_bridges',domain='physical_member_graph',mapping_id=p['mapping_id'],plan_edges=[],member_edge_id=member)
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(observation)
        result['member_domain_observations'].append(dict(observation,axis_edge_id=eid,anchors=dict(axis_nodes=p['axis_nodes'])))
        added.append(eid)
    remaining=[];complete=[]
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid]
        if positive(v.get('diameter_nominal_mm'))and any(positive(v.get(k))for k in COMPLETE_FIELDS):complete.append(eid);continue
        if eid not in old_front:raise ValueError('previously complete horizontal edge regressed: '+eid)
        pending=copy.deepcopy(old_front[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']))
        if eid in targets:pending.update(known_whole_DN=v.get('diameter_nominal_mm')if positive(v.get('diameter_nominal_mm'))else None,existing_mapping_id=targets[eid]['mapping_id'])
        if pending['next_scope']=='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path'and row['has_existing_correspondence']:
            pending['next_scope']='known_member_correspondence_incomplete_metric'if any(o['domain']=='physical_member_graph'for o in row['correspondence_observations'])else'known_local_correspondence_incomplete_attributes'
        remaining.append(pending)
    result.update(mode=MODE,original_alias_inventory_inputs=copy.deepcopy(original['inputs']),source_bindings=bindings,
        remaining_horizontal_attributes=remaining,new_alias_bridge_axis_edges=sorted(added),actual_effective_values_read=True,
        new_correspondences_assigned=0,previously_qualified_alias_bridge_correspondences_inherited=len(added),ordinary_junction_mappings_unchanged=True,
        DN_or_length_values_assigned=0,vertical_segments_routed_to_plan=0,mixed_unmapped_horizontal_extent_count=None,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),member_domain_observations=len(result['member_domain_observations']),
        pure_horizontal_remaining_attributes=len(remaining),pure_horizontal_complete_DN_and_centerline=len(complete),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    result['current_horizontal_frontier']=dict(status='actual_current_viewer_frontier_including_all_alias_bridge_providers',axis_edges=len(rows),
        pure_horizontal_edges=sum(r['classification']=='horizontal_only'for r in rows.values()),pure_horizontal_complete=len(complete),pure_horizontal_remaining_attributes=len(remaining),
        remaining_by_floor=dict(sorted(collections.Counter(str(r['floor'])for r in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining,
        mixed_edges=sum(r['classification']=='mixed_horizontal_vertical'for r in rows.values()),mixed_horizontal_unmatched_extent_count=None,vertical_segments_routed_to_plan=0)
    if result['ordinary_junction_mappings']!=original['ordinary_junction_mappings']or result['member_domain_observations'][:len(original['member_domain_observations'])]!=original['member_domain_observations']:raise ValueError('old ordinary/member providers changed')
    return result

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('bridge provider input changed')
    checked();from refresh_alias_member_bridge_attributes import verify,base
    from alias_aware_provider_inventory import verify_output as verify_original
    bundle=paths['viewer_manifest'].parents[2];qualified=verify(bundle)
    if qualified.get('artifact_replay')!='passed':raise ValueError('current alias bridge viewer did not replay')
    original=verify_original(paths['original_inventory'].parent)
    if encode(original)!=paths['original_inventory'].read_bytes():raise ValueError('original complete alias inventory did not replay')
    audit=load(paths['viewer_audit'])
    if Path(audit['source_paths']['proof']).resolve()!=paths['native_proof'].resolve()or audit['original_input_hashes'][str(paths['native_proof'].resolve())]!=sha(paths['native_proof']):raise ValueError('viewer and bridge native proof differ')
    result=inventory(original,load(paths['native_proof']),load(paths['viewer_manifest'])['attributeValueContext']['alias_member_bridges'],base.effective_attributes(bundle),load(paths['baseline_frontier']),{k:sha(p)for k,p in paths.items()})
    checked();result.update(inputs=manifest['inputs'],current_bridge_viewer_native_replayed=True,complete_original_alias_inventory_replayed=True)
    return result

def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('alias_member_bridge_context','refresh_alias_member_bridge_attributes','rebuild_alias_member_inline_bridges','alias_aware_provider_inventory')})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'provider-inventory.json';target.write_bytes(encode(result));(output/'horizontal-frontier.json').write_bytes(encode(result['current_horizontal_frontier']))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'provider-inventory.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('bridge provider implementation or receipt changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes()or encode(fresh['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('independent bridge inventory differs')
    return fresh

def main():
    p=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
