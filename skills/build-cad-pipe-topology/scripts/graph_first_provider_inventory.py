"""Inherit the published cycle/vertical scopes before further graph discovery."""
import argparse,collections,copy,importlib,sys
from pathlib import Path
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
MODE='qualified_graph_first_provider_inventory_v1'

def inherit(original,cycle,metrics,context,effective,bindings):
    from bridge_aware_provider_inventory import MODE as OLD_MODE
    from rebuild_anchored_cycle_gate_batch import MODE as CYCLE_MODE
    from graph_first_attribute_context import MODE as CONTEXT_MODE
    if original.get('mode')!=OLD_MODE or cycle.get('mode')!=CYCLE_MODE or context.get('mode')!=CONTEXT_MODE or context['source_bindings']['cycle_metric_proof']!=bindings['metric_proof']or metrics['inputs']['cycle_proof']['sha256']!=bindings['cycle_proof']or cycle['inputs']['inventory']['sha256']!=bindings['original_inventory']:raise ValueError('graph-first provider ancestry differs')
    result=copy.deepcopy(original);rows={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective}
    if rows.keys()!=values.keys()or len(rows)!=len(result['records'])or len(values)!=len(effective):raise ValueError('effective edge inventory differs')
    qualified={r['axis_edge_id']:r for r in context['cycle_records']};source={r['iso_edges'][0]:r for f in cycle['floors'].values()for r in f['records']}
    if not qualified.keys()<=source.keys():raise ValueError('published cycle is outside qualified correspondence batch')
    for f,proof in cycle['floors'].items():
        mapping=result['ordinary_junction_mappings'][f]
        for p,a in proof['new_junction_mapping'].items():
            if p in mapping or a in mapping.values():raise ValueError('cycle gate competes with old anchor')
            mapping[p]=a
    for eid,r in qualified.items():
        row=rows[eid];s=source[eid];v=values[eid]
        if row['has_existing_correspondence']or row['correspondence_observations']or s['mapping_id']!=r['mapping_id']or s['plan_edges']!=[r['plan_edge_id']]:raise ValueError('cycle path competes with old provider')
        if v.get('cycle_gate_mapping_id')!=r['mapping_id']or v.get('cycle_gate_complete_centerline_mm')!=r['complete_horizontal_centerline_mm']:raise ValueError('published cycle effective value differs')
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(dict(provider='cycle_gate_plan_runs',domain='ordinary_local_graph',mapping_id=r['mapping_id'],plan_edges=[r['plan_edge_id']],grouped_axis_edges=[eid],floor=r['floor']))
    oldfront={r['edge_id']:r for r in original['remaining_horizontal_attributes']};remaining=[];complete=[]
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid];length=any(positive(v.get(k))for k in COMPLETE_FIELDS+('cycle_gate_complete_centerline_mm',))
        if positive(v.get('diameter_nominal_mm'))and length:complete.append(eid);continue
        if eid not in oldfront:raise ValueError('previous horizontal completeness regressed')
        pending=copy.deepcopy(oldfront[eid]);pending.update(attributes=copy.deepcopy(v),correspondence_observations=copy.deepcopy(row['correspondence_observations']))
        if eid in qualified:pending.update(existing_mapping_id=qualified[eid]['mapping_id'],complete_centerline=True,next_scope='existing_DN_conflict_source_scope_reconciliation')
        remaining.append(pending)
    result.update(mode=MODE,original_provider_inputs=copy.deepcopy(original['inputs']),remaining_horizontal_attributes=remaining,source_bindings=bindings,
        new_cycle_axis_edges=sorted(qualified),new_correspondences_assigned=0,DN_or_length_values_assigned=0,
        newly_inherited_cycle_correspondences=len(qualified),previously_qualified_cycle_and_vertical_scopes_inherited=True,
        member_namespaces_preserved=True,all_current_vertical_DN_domains=context['all_current_vertical_domain_count'],human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in rows.values()),
        pure_horizontal_complete_DN_and_centerline=len(complete),pure_horizontal_remaining_attributes=len(remaining),
        horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)),all_current_vertical_DN_domains=context['all_current_vertical_domain_count'])
    result['current_horizontal_frontier']=dict(status='actual_current_graph_first_viewer_frontier_all_providers_retained',axis_edges=len(rows),
        pure_horizontal_edges=sum(r['classification']=='horizontal_only'for r in rows.values()),pure_horizontal_complete=len(complete),pure_horizontal_remaining_attributes=len(remaining),
        remaining_by_floor=dict(sorted(collections.Counter(str(r['floor'])for r in remaining).items())),remaining_by_next_scope=result['counts']['horizontal_next_scopes'],records=remaining,
        mixed_edges=sum(r['classification']=='mixed_horizontal_vertical'for r in rows.values()),mixed_horizontal_unmatched_extent_count=None,vertical_segments_routed_to_plan=0)
    if result['member_domain_observations']!=original['member_domain_observations']:raise ValueError('old member observations changed')
    return result

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in manifest['inputs'].items()):raise ValueError('graph-first inventory input changed')
    checked();from refresh_graph_first_attributes import verify,base
    from bridge_aware_provider_inventory import verify_output as verify_original
    from native_replay_session import verify_once
    bundle=paths['viewer_manifest'].parents[2];replay=verify(bundle)
    if replay.get('artifact_replay')!='passed':raise ValueError('current viewer did not replay')
    original=verify_once(paths['original_inventory'].parent,verify_original)
    if encode(original)!=paths['original_inventory'].read_bytes():raise ValueError('original complete inventory differs')
    context=load(paths['viewer_manifest'])['attributeValueContext']['graph_first_extensions']
    if context['source_bindings']['vertical_inheritance_proof']!=sha(paths['vertical_proof']):raise ValueError('vertical source differs from current viewer')
    r=inherit(original,load(paths['cycle_proof']),load(paths['metric_proof']),context,base.effective_attributes(bundle),{k:sha(p)for k,p in paths.items()})
    checked();r.update(inputs=manifest['inputs'],current_viewer_and_complete_original_inventory_replayed=True)
    return r

def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('refresh_graph_first_attributes','graph_first_attribute_context','cycle_gate_plan_lengths','bridge_aware_provider_inventory')})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    r=compute(load(manifest_path));output.mkdir(parents=True);p=output/'provider-inventory.json';p.write_bytes(encode(r));(output/'horizontal-frontier.json').write_bytes(encode(r['current_horizontal_frontier']))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(p))))
    return r

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'provider-inventory.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('graph-first inventory receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes()or encode(r['current_horizontal_frontier'])!=(output/'horizontal-frontier.json').read_bytes():raise ValueError('graph-first provider independent replay differs')
    return r

def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and new output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
