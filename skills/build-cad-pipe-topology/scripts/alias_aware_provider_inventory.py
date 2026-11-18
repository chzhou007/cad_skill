"""Inherit the complete old inventory plus native alias member providers.

Ordinary anchors are unchanged. Member scopes are added in their own namespace;
the frontier is derived from actual effective values of the qualified viewer.
"""
import argparse,collections,copy,importlib,math,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
MODE='qualified_alias_aware_crossview_provider_inventory_v1'
COMPLETE_FIELDS=('anchored_main_complete_centerline_mm','batch_complete_horizontal_centerline_mm','plan_segment_whole_main_centerline_mm','member_plan_run_centerline_mm','compound_member_plan_run_centerline_mm','circle_member_complete_centerline_mm','ordered_group_complete_run_mm','noncompound_main_complete_centerline_mm','bounded_main_complete_centerline_mm','alias_member_complete_centerline_mm')

def positive(value):
    if isinstance(value,bool)or value in(None,''):return False
    try:return math.isfinite(float(value))and float(value)>0
    except (ValueError,TypeError):return False

def inventory(original,proof,context,effective,baseline,bindings):
    from alias_member_circle_interfaces import MODE as SOURCE_MODE
    from alias_member_interface_context import MODE as CONTEXT_MODE
    if proof.get('mode')!=SOURCE_MODE or context.get('mode')!=CONTEXT_MODE or context['source_bindings']['native_proof']!=bindings['native_proof']or proof['inputs']['provider_inventory']['sha256']!=bindings['original_inventory']:raise ValueError('alias inventory source binding differs')
    if original.get('new_correspondences_assigned')!=0 or proof.get('ordinary_junction_mapping_extended')is not False or proof.get('human_accepted')is not False or context.get('human_accepted')is not False:raise ValueError('unqualified provider ancestry')
    result=copy.deepcopy(original);rows={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective};old_front={r['edge_id']:r for r in baseline['records']}
    if len(rows)!=len(result['records'])or set(rows)!=set(values):raise ValueError('actual current effective edge inventory differs')
    expected={r['axis_edge_id']:r for r in proof['records']};current={r['axis_edge_id']:r for r in context['records']};member_ids={r['edge_id']for r in proof['member_local_graph']['edges']}
    if expected.keys()!=current.keys()or len(expected)!=len(proof['records'])or len(current)!=len(context['records']):raise ValueError('new native member provider inventory differs')
    added=[]
    for eid,p in expected.items():
        c=current[eid];member=p['plan_member_edge_id']
        if not member.startswith('MEMBER:')or member not in member_ids or c['mapping_id']!=p['mapping_id']or c['plan_member_edge_id']!=member:raise ValueError('member namespace or correspondence identity differs')
        row=rows[eid]
        if row['correspondence_observations']or row['has_existing_correspondence']:raise ValueError('new member observation competes with old provider')
        observation=dict(provider='alias_member_interfaces',domain='physical_member_graph',mapping_id=p['mapping_id'],plan_edges=[],member_edge_id=member)
        row['correspondence_observations'].append(observation);row['has_existing_correspondence']=True
        result['member_domain_observations'].append(dict(observation,axis_edge_id=eid,anchors=dict(axis_nodes=p['axis_nodes'],member_scope_id=p['member_scope_id'])))
        added.append(eid)
    remaining=[];complete=[]
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid]
        if positive(v.get('diameter_nominal_mm'))and any(positive(v.get(k))for k in COMPLETE_FIELDS):complete.append(eid);continue
        if eid not in old_front:raise ValueError('previously completed horizontal edge regressed: '+eid)
        pending=copy.deepcopy(old_front[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']))
        if pending['next_scope']=='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path'and row['has_existing_correspondence']:pending['next_scope']='known_member_correspondence_incomplete_metric'if any(o['domain']=='physical_member_graph'for o in row['correspondence_observations'])else'known_local_correspondence_incomplete_attributes'
        remaining.append(pending)
    result.update(mode=MODE,original_provider_inventory_inputs=copy.deepcopy(original['inputs']),source_bindings=bindings,remaining_horizontal_attributes=remaining,new_alias_member_axis_edges=sorted(added),actual_effective_values_read=True,new_correspondences_assigned=0,previously_qualified_member_correspondences_inherited=len(added),ordinary_junction_mappings_unchanged=True,DN_or_length_values_assigned=0,vertical_segments_routed_to_plan=0,mixed_unmapped_horizontal_extent_count=None,human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),member_domain_observations=len(result['member_domain_observations']),pure_horizontal_remaining_attributes=len(remaining),pure_horizontal_complete_DN_and_centerline=len(complete),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)),mixed_edges_without_any_correspondence=sum(r['classification']=='mixed_horizontal_vertical'and not r['has_existing_correspondence']for r in rows.values()))
    result['current_horizontal_frontier']=dict(status='actual_qualified_viewer_frontier_with_all_alias_member_providers',axis_edges=len(rows),pure_horizontal_edges=sum(r['classification']=='horizontal_only'for r in rows.values()),pure_horizontal_complete=len(complete),pure_horizontal_remaining_attributes=len(remaining),remaining_by_floor=dict(sorted(collections.Counter(str(r['floor'])for r in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining,mixed_edges=sum(r['classification']=='mixed_horizontal_vertical'for r in rows.values()),mixed_horizontal_unmatched_extent_count=None,vertical_segments_routed_to_plan=0)
    if result['ordinary_junction_mappings']!=original['ordinary_junction_mappings']:raise ValueError('member nodes entered ordinary anchor namespace')
    return result

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('alias inventory input changed')
    checked();from refresh_alias_member_interface_attributes import verify,base
    bundle=paths['viewer_manifest'].parents[2];qualified=verify(bundle)
    if qualified.get('artifact_replay')!='passed':raise ValueError('current alias viewer did not replay')
    audit=load(paths['viewer_audit']);proof=load(paths['native_proof'])
    if Path(audit['source_paths']['proof']).resolve()!=paths['native_proof'].resolve()or audit['original_input_hashes'][str(paths['native_proof'].resolve())]!=sha(paths['native_proof']):raise ValueError('viewer and member source proof differ')
    original=load(paths['original_inventory']);context=load(paths['viewer_manifest'])['attributeValueContext']['alias_member_interfaces']
    result=inventory(original,proof,context,base.effective_attributes(bundle),load(paths['baseline_frontier']),{k:sha(p)for k,p in paths.items()})
    checked();result['inputs']=manifest['inputs'];result['current_alias_viewer_native_replayed']=True;return result

def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('alias_member_interface_context','refresh_alias_member_interface_attributes','rebuild_alias_member_circle_interfaces')})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'provider-inventory.json';target.write_bytes(encode(result));(output/'horizontal-frontier.json').write_bytes(encode(result['current_horizontal_frontier']))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)));return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'provider-inventory.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('alias provider inventory receipt changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes()or encode(fresh['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('independent alias provider inventory differs')
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
