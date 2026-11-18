"""Reapply a source-qualified historical provider to unchanged current scopes.

Generic unknown DN cannot erase a more specific native reading. Explicit
conflicts, changed scope snapshots and mixed/branch metrics still block fusion.
No old source owner, correspondence or graph is rewritten by this adapter.
"""
import argparse,copy,csv,importlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from native_replay_session import verify_once
from wave_rebased_plan_attributes import verify_output as verify_provider,MODE as PROVIDER_MODE
from reconstruct_wave_main_cohorts import verify_output as verify_plan
from native_exploded_caption_identity import verify_output as verify_axis
from match_source_checked_crossview_paths import selected_snapshot
from native_main_endpoint_extent import qualify
from source_readability import read_source
from fresh_reviewed_plan_inventory import inspect_view
from match_wave_rebased_circle_paths import correspond_current
from wave_rebased_plan_attributes import configuration
from inherited_circle_plan_attributes import attribute
MODE='native_qualified_plan_scope_reapplication_v1'

def match_current(provider,mapping,current,plan,axis,raw,angles):
    if provider.get('mode')!=PROVIDER_MODE or provider.get('physical_values_fused')is not False or provider.get('local_graphs_mutated')is not False or provider.get('human_accepted')is not False:raise ValueError('native source provider must retain its local-only scope')
    by={r['mapping_id']:r for r in mapping['records']};scopes={r['mapping_id']:r for r in raw['sourceFullPlanBatchAttributes']['records']};records=[];pending=[];seen=set()
    for value in provider['records']:
        mid=value['mapping_id'];old=by[mid]
        if value['kind']!='main_between_equipment_branches':pending.append(dict(provider_mapping_id=mid,reason='branch_horizontal_and_vertical_domains_remain_separate'));continue
        options=[r for r in current if r['kind']=='same_floor_T_to_T_main'and all(r[k]==value[k]for k in('floor','system','plan_edges','iso_edges'))]
        if len(options)!=1:pending.append(dict(provider_mapping_id=mid,reason='no_unique_current_one_to_one_main_correspondence'));continue
        row=options[0];scope=scopes[row['mapping_id']];dn=value['diameter']['nominal_mm']
        if len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('provider group metric cannot be assigned to one child')
        if any(r.get('status')=='conflict'for r in scope['plan_DN_records']):pending.append(dict(provider_mapping_id=mid,current_mapping_id=row['mapping_id'],reason='explicit_current_DN_conflict_requires_source_resolution'));continue
        prior=scope['plan_drawn_nominal_mm']
        if prior is not None:
            if prior!=dn:raise ValueError('specific native provider conflicts with current known plan DN')
            pending.append(dict(provider_mapping_id=mid,current_mapping_id=row['mapping_id'],reason='known_plan_DN_retained_existing_attribute_owner'));continue
        if any(r.get('status')not in('source_scope_unverified','unresolved','annotation_blocked')for r in scope['plan_DN_records']):raise ValueError('unsupported generic unknown state')
        for view,graph in(('plan',plan),('iso',axis)):
            if selected_snapshot(graph,row[view+'_edges'])!=old[view+'_snapshot']:raise ValueError('qualified provider current scope snapshot changed')
            if {row[view+'_start'],row[view+'_end']}!={old[view+'_start'],old[view+'_end']}:raise ValueError('provider endpoint correspondence differs')
        if value.get('physical_source_identity_resolved')is not False or value.get('whole_axis_physical_length_mm')is not None:raise ValueError('provider physical identity or installed length changed')
        result=qualify(plan,axis,row,dn,value['horizontal_projection'],angles)
        if result['complete_horizontal_centerline_route_mm']is None:pending.append(dict(provider_mapping_id=mid,current_mapping_id=row['mapping_id'],reason='native_endpoint_extent_not_complete'));continue
        eid=result['axis_edge_id']
        if eid in seen:raise ValueError('specific native provider repeats an axis writer')
        seen.add(eid);record=copy.deepcopy(row);record.pop('plan_snapshot',None);record.pop('iso_snapshot',None);record.update(status='native_path_correspondence_independently_source_checked',DN_used_for_mapping=False,human_accepted=False)
        records.append(dict(result,current_mapping=record,provider_mapping_id=mid,provider_group_id=value['group_id'],provider_DN_record=copy.deepcopy(value['diameter']),provider_metric=copy.deepcopy(value['horizontal_projection']),generic_scope_retained_as_superseded=copy.deepcopy(scope),physical_source_identity_resolved=False,installed_whole_edge_length_mm=None,unshown_branch_connector_length_mm=None,run_centerline_includes_inline_assembly_extents=True,detail_inline_positions_scaled_to_plan=False,DN_used_for_mapping=False))
    return records,pending

def recompute_provider(paths,plan,axis,raw):
    """Rebuild a new provider on current parents; never bypass an old receipt."""
    previous=load(paths['provider']);previous_mapping=load(paths['provider_mapping']);settings=load(paths['mapping_policy']);attribute_settings=load(paths['attribute_policy'])
    generic=raw['sourceFullPlanBatchAttributes']['records'];groups={r['group_id']for r in previous['records']if r['kind']=='main_between_equipment_branches'and any(s['plan_edges']==r['plan_edges']and s['iso_edges']==r['iso_edges']and s['floor']==r['floor']and s['system']==r['system']and s['plan_drawn_nominal_mm']is None for s in generic)}
    docs={};preflights={};graphs=dict(plan=plan,iso=axis);hashes={}
    for v in graphs:
        prefix='axis'if v=='iso'else v;docs[v],preflights[v]=read_source(paths[prefix+'_source']);hashes[v]=dict(source_sha256=sha(paths[prefix+'_source']),graph_sha256=sha(paths[prefix+'_graph']))
        if graphs[v]['metadata']['source_sha256']!=hashes[v]['source_sha256']:raise ValueError('current local source differs')
    circle=load(paths['circle_policy'])
    with paths['axis_devices'].open(encoding='utf-8-sig',newline='')as stream:devices=list(csv.DictReader(stream))
    fresh_values=[];fresh_mappings=[];fresh_groups=[]
    for gid in sorted(groups):
        specs=[s for s in settings['groups']if s['group_id']==gid];attribute_specs=[s for s in attribute_settings['groups']if s['group_id']==gid]
        if len(specs)!=1 or len(attribute_specs)!=1:raise ValueError('source group configuration missing or duplicated')
        spec,config=specs[0],attribute_specs[0];inventory=[]
        for did in spec['equipment_ids']:
            views={v:inspect_view(docs[v],graphs[v],did,spec['floor'],hashes[v],v,devices,circle if v=='plan'else None)for v in graphs}
            ready=all(views[v].get('services',{}).get(s,{}).get('ready_for_mapping_comparison')is True for v in views for s in('supply','return'))
            if not ready:raise ValueError('current independent source service failed '+did)
            inventory.append(dict(equipment_id=did,floor=spec['floor'],views=views,ready_for_mapping_comparison=True))
        mapping=correspond_current(docs,graphs,dict(records=inventory),circle,spec,hashes)
        original=load(config['calibration_origin']['path']);scope,calibration,metric=configuration(config,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'],original['graph_sha256'])
        values=attribute(docs['plan'],plan,mapping,scope,calibration,metric,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
        # Old scopes are history. New source/parent receipts above prove this
        # new reading; compare semantic values without manufacturing old hashes.
        old={r['mapping_id']:r for r in previous['records']if r['group_id']==gid}
        for value in values['records']:
            prior=old[value['mapping_id']]
            for key in('kind','floor','system','plan_edges','iso_edges','diameter','horizontal_projection'):
                if value[key]!=prior[key]:raise ValueError('historical qualified source value changed '+value['mapping_id']+'/'+key)
            fresh_values.append(dict(value,group_id=gid))
        fresh_mappings.extend(mapping['records']);fresh_groups.append(dict(group_id=gid,mapping=mapping,attributes=values))
    result=dict(mode=PROVIDER_MODE,records=fresh_values,physical_values_fused=False,local_graphs_mutated=False,human_accepted=False,source_sha256=hashes['plan']['source_sha256'],graph_sha256=hashes['plan']['graph_sha256'],mapping_sha256=sha(paths['provider_mapping']))
    return result,dict(records=fresh_mappings),dict(groups=fresh_groups,source_preflight=preflights,old_provider_receipt_accepted=False,current_native_provider_recomputed=True,historical_values_exact=True)

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('qualified source extension input changed')
    checked();parent=verify_once(paths['plan_graph'].parent,verify_plan);verify_once(paths['axis_graph'].parent,verify_axis)
    if parent['output_graph_sha256']!=sha(paths['plan_graph']):raise ValueError('current native plan differs')
    batch=load(paths['batch']);raw=load(paths['raw_axis_graph']);plan=load(paths['plan_graph']);axis=load(paths['axis_graph']);provider,mapping,native_provider=recompute_provider(paths,plan,axis,raw)
    if sha(paths['provider_mapping'])!=provider['mapping_sha256']or provider['source_sha256']!=plan['metadata']['source_sha256']or batch['identity_graph_sha256']!=sha(paths['axis_graph']):raise ValueError('current and provider source identity differs')
    receipt=paths['batch'].with_name('main-chain-batch-receipt.json')
    if raw['sourceFullPlanBatchAttributes']['source_hashes']['mapping_receipt']!=sha(receipt):raise ValueError('qualified axis and batch mapping identity differs')
    floor=manifest['floor']
    if type(floor)is not int or set(r['floor']for r in provider['records'])!={floor}:raise ValueError('explicit provider floor required')
    records,pending=match_current(provider,mapping,batch['floors'][str(floor)]['records'],plan,axis,raw,manifest['horizontal_directions_degrees'])
    raw_edges={e['edge_id']:e for e in raw['edges']};native={e['edge_id']:e for e in axis['edges']}
    for r in records:
        eid=r['axis_edge_id']
        if any(raw_edges[eid].get(k)!=native[eid].get(k)for k in('system','start_node_id','end_node_id','attribute_paths','equipment_inventory')):raise ValueError('qualified axis payload differs from native graph')
    checked();return dict(mode=MODE,inputs=manifest['inputs'],records=records,pending=pending,provider_mode=provider['mode'],specific_provider_reconstructed=True,native_provider=native_provider,source_scope_rebase='current_native_parents_and_fresh_original_provider_readers_not_old_receipt_acceptance',counts=dict(provider_scopes=len(provider['records']),new_one_to_one_main_scopes=len(records),other_scopes_retained=len(pending)),existing_mapping_IDs_preserved=True,source_graphs_mutated=False,DN_used_for_mapping=False,physical_pipe_count_inferred=False,axis_values_fused=False,human_accepted=False)

def implementation_hashes():
    names=('wave_rebased_plan_attributes','inherited_circle_plan_attributes','native_canonical_main_family_view','native_main_endpoint_extent','reconstruct_wave_main_cohorts','native_exploded_caption_identity','match_source_checked_crossview_paths','native_replay_session','fresh_reviewed_plan_inventory','match_wave_rebased_circle_paths','source_readability','calibrated_direct_dn_evidence','checked_plan_DN_scope_attributes')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);p=output/'qualified-plan-scope-extension.json';p.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(p))))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];p=output/'qualified-plan-scope-extension.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=r['output_sha256']:raise ValueError('qualified source extension implementation or input changed')
    result=compute(load(m['path']))
    if encode(result)!=p.read_bytes():raise ValueError('independent specific source extension differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('pinned manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
