"""Transfer uniform plan DN over a source-proved lower-member path range.

An independently mapped high-member prefix is removed from the two ordered
routes. The remaining native plan member and every remaining plan DN region
must agree. Internal node identities and per-axis-edge lengths stay unknown.
"""
import argparse,copy,hashlib,importlib,sys
from pathlib import Path
for n in ['orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology']:sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reviewed_expression_metrics import verify_output as group_owner
from rebuild_compound_riser_header_members import verify_output as member_owner
from rebuild_compound_carrier_atom_origins import verify_output as origin_owner
from riser_header_interval_application import implementation_hashes as interval_implementations,MODE as INTERVAL_MODE
from compound_riser_header_members import oriented
from qualified_member_caption_scope import departure_guard
from compound_member_interfaces import native_label_guard
from native_paired_caption_geometry import collect as captions
from batch_native_path_coverage import collect as coverage
from source_readability import read_source
from native_replay_session import verify_once

MODE='native_reviewed_uniform_lower_subroute_plan_DN_v1'

def select(scope,member,interval,plan,axis,routing,plan_DN,plan_guard,axis_guard):
    if scope['status']!='native_bounded_range_correspondence':raise ValueError('both local source views must be qualified')
    me={e['edge_id'].rsplit(':',1)[1]:e for e in member['scoped_graph']['edges']};nodes={n['node_id'].rsplit(':',1)[1]:n for n in member['scoped_graph']['nodes']};approach,departure=me['approach'],me['departure'];nominal=departure['member']['nominal_mm']
    pr=scope['views']['plan']['route'];ar=scope['views']['iso']['route'];pe={e['edge_id']:e for e in plan['edges']};ae={e['edge_id']:e for e in axis['edges']}
    if (scope['system']!=member['system']or scope['floor']!=member['floor']or approach['member']['nominal_mm']==nominal
        or ar['edges'][0]!=approach['candidate_axis_edge']or ar['nodes'][1]!=member['new_axis_tee']or nodes['gate']['source_node_id']!=pr['nodes'][0]or nodes['departure']['source_node_id']!=pr['nodes'][2]):raise ValueError('independent prefix and exact ordered range do not agree')
    if (interval['axis_edge_id']!=ar['edges'][0]or interval['member_scope_id']!=member['scope_id']or interval['member_kind']!='approach'or interval['nominal_mm']!=approach['member']['nominal_mm']
        or interval['endpoint_evidence']['axis_tee']!=member['new_axis_tee']or interval['endpoint_evidence']['plan_circle']!=member['source_circle']):raise ValueError('prefix mapping needs its independently revalidated gate and native member')
    if interval['axis_attribute_paths']!=ae[ar['edges'][0]]['attribute_paths']or interval['plan_attribute_paths']!=approach['attribute_paths']:raise ValueError('current native prefix extent differs from retained interval')
    first=oriented(pe[pr['edges'][0]],pr['nodes'][0]);second=oriented(pe[pr['edges'][1]],pr['nodes'][1]);prefix=approach['attribute_paths'];expected=[[prefix[0][-1],first[0][-1]]]+second
    if len(first)!=1 or len(first[0])!=2 or prefix[0][0]!=first[0][0]or departure['attribute_paths']!=expected:raise ValueError('lower member does not exactly specialize the two projected prefix edges')
    if (plan_guard['original_guard_reexecuted']is not True or plan_guard['original_thresholds_unchanged']is not True or plan_guard['F_and_other_new_DN_guards_retained']is not True
        or plan_guard['source_document_mutated']is not False):raise ValueError('original scoped plan caption owner must pass')
    remaining=pr['edges'][2:];values=[]
    for eid in remaining:
        r=plan_DN[eid];e=pe[eid]
        if r['nominal_mm']!=nominal or r['system']!=scope['system']or r['scope_paths']!=e['attribute_paths']or not r['lineage']:raise ValueError('lower source range contains unknown, conflicting or differently scoped plan DN')
        values.append(copy.deepcopy(r))
    records=[];excluded=[]
    for eid in ar['edges'][1:]:
        e=ae[eid];r=routing[eid]
        if e['system']!=scope['system']or any(e[k]!=scope['floor']for k in ['floor_start','floor_end']):raise ValueError('lower axis range changes system or floor')
        domains=r['segment_domains'];expected={(pi,si)for pi,path in enumerate(e['attribute_paths'])for si in range(len(path)-1)}
        actual={(s['path_index'],s['segment_index'])for s in domains}
        if expected!=actual or len(actual)!=len(domains):raise ValueError('complete original segment direction inventory required')
        horizontal=[];vertical=[]
        for s in domains:
            pi,si=s['path_index'],s['segment_index']
            if s['scope_points']!=e['attribute_paths'][pi][si:si+2]or s['native_source_status']!='single_source_line_covers':raise ValueError('original native segment extent or direction witness differs')
            if s['direction_class']=='horizontal':horizontal.append(copy.deepcopy(s))
            elif s['direction_class']=='vertical':vertical.append(copy.deepcopy(s))
            else:raise ValueError('unresolved original axis direction')
        classification='horizontal_only'if not vertical else'vertical_only'if not horizontal else'mixed_horizontal_vertical'
        if r['classification']!=classification:raise ValueError('whole-edge direction summary differs from original segment inventory')
        excluded.extend(dict(edge_id=eid,path_index=s['path_index'],segment_index=s['segment_index'],scope_points=s['scope_points'],reason='vertical_portion_remains_owned_by_drawing11')for s in vertical)
        if not horizontal:continue
        records.append(dict(axis_edge_id=eid,system=e['system'],floor=scope['floor'],axis_nodes=[e['start_node_id'],e['end_node_id']],axis_attribute_paths=copy.deepcopy(e['attribute_paths']),nominal_mm=nominal,
            whole_horizontal_edge=not vertical,horizontal_segment_domains=horizontal,scope_paths=[s['scope_points']for s in horizontal],
            source_scope_id=scope['scope_id']+':LOWER-UNIFORM-DN',plan_member_scope_id=member['scope_id'],plan_lower_member_id=departure['edge_id'],plan_remaining_edges=copy.deepcopy(remaining),
            mapping_kind='uniform_DN_path_range_without_internal_node_pairing',source='native_floor_plan_uniform_lower_member_and_T_regions',axis_labels_validation_only=True,
            physical_length_mm=None,per_axis_edge_length_allocation=None,internal_node_identities_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False))
    if not records:raise ValueError('no horizontal lower range')
    return dict(scope_id=scope['scope_id'],nominal_mm=nominal,prefix_axis_edge=ar['edges'][0],prefix_axis_nodes=ar['nodes'][:2],native_circle=copy.deepcopy(member['source_circle']),plan_lower_member=copy.deepcopy(departure),remaining_plan_DN_regions=values,
        scoped_plan_caption_guard=copy.deepcopy(plan_guard),axis_caption_consistency_guard=copy.deepcopy(axis_guard),records=records,excluded_vertical_domains=excluded,
        no_internal_node_identity_required_for_uniform_DN=True,no_DN_used_to_discover_correspondence=True,physical_lengths_assigned=0,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        if any(sha(s['path'])!=s['sha256']for s in inputs.values()):raise ValueError('uniform lower range input changed')
    checked();group=verify_once(Path(inputs['group_metric_proof']['path']).parent,group_owner);members=verify_once(Path(inputs['member_proof']['path']).parent,member_owner);origin=verify_once(Path(inputs['atom_proof']['path']).parent,origin_owner)
    interval_path=Path(inputs['interval_proof']['path']);interval_receipt=load(interval_path.parent/'receipt.json');intervals=load(interval_path)
    if (intervals['mode']!=INTERVAL_MODE or interval_receipt['mode']!=INTERVAL_MODE or interval_receipt['implementation_sha256']!=interval_implementations()or interval_receipt['output_sha256']!=sha(interval_path)
        or sha(interval_receipt['manifest']['path'])!=interval_receipt['manifest']['sha256']or any(sha(v['path'])!=v['sha256']for v in intervals['inputs'].values())):raise ValueError('retained complete interval parent bytes, code or inputs differ')
    for artifact,key in [(group,'group_metric_proof'),(members,'member_proof'),(origin,'atom_proof'),(intervals,'interval_proof')]:
        if encode(artifact)!=Path(inputs[key]['path']).read_bytes():raise ValueError('fresh original owner replay differs')
    scopes=load(group['inputs']['scope_proof']['path']);partition=load(inputs['partition_proof']['path']);anchor=load(scopes['inputs']['anchor_proof']['path'])
    if inputs['partition_proof']!=anchor['inputs']['partition']:raise ValueError('plan DN is not the partition freshly replayed by the group owner')
    for data in [members,intervals]:
        for key,sourcekey in [('plan_source','plan_source'),('plan_graph','plan_graph'),('axis_source','iso_source'),('axis_graph','iso_graph')]:
            if data['inputs'][key]!=scopes['inputs'][sourcekey]:raise ValueError('native member source namespace differs')
    if intervals['inputs']['member_proof']!=inputs['member_proof']or intervals['inputs']['atom_proof']!=inputs['atom_proof']:raise ValueError('member gate proof has different native ancestors')
    if group['inputs']['plan_graph']!=partition['inputs']['current_graph']or group['inputs']['plan_source']!=partition['inputs']['source']:raise ValueError('current native plan DN graph differs')
    routing=load(inputs['routing_proof']['path'])
    if routing['inputs']['graph']!=scopes['inputs']['iso_graph']or routing['inputs']['source']!=scopes['inputs']['iso_source']:raise ValueError('axis direction graph or source differs')
    plan=load(scopes['inputs']['plan_graph']['path']);axis=load(scopes['inputs']['iso_graph']['path']);docs={};preflight={}
    for v in ['plan','iso']:docs[v],preflight[v]=read_source(scopes['inputs'][v+'_source']['path'])
    from refresh_reviewed_ring_partition_DN import effective
    viewer=Path(inputs['current_viewer_manifest']['path']).parents[2];vm=load(inputs['current_viewer_manifest']['path'])
    if (encode(effective(viewer))!=Path(inputs['current_effective']['path']).read_bytes()
        or vm['attributeValueContext']['reviewed_expression_group_metrics']['source_bindings']['native_metric_proof']!=inputs['group_metric_proof']['sha256']):raise ValueError('actual current viewer values or reviewed source group differs')
    cap={v:captions(doc)for v,doc in docs.items()};dn={r['edge_id']:r for r in partition['after_inherited_kernel']['records']};routes={r['edge_id']:dict(r,segment_domains=[s for s in routing['records']if s['edge_id']==r['edge_id']])for r in routing['edges']};known={r['edge_id']:r['values']for r in load(inputs['current_effective']['path'])};reports=[];pending=[]
    for scope in scopes['records']:
        if scope['status']!='native_bounded_range_correspondence':pending.append(dict(scope_id=scope['scope_id'],reason='original_local_source_range_held',failures=copy.deepcopy(scope['failures'])));continue
        try:
            candidates=[r for r in members['records']if r['system']==scope['system']and r['floor']==scope['floor']];
            if len(candidates)!=1:raise ValueError('one native member prefix required')
            member=candidates[0];me={e['edge_id'].rsplit(':',1)[1]:e for e in member['scoped_graph']['edges']};prior=[r for r in intervals['member_records']if r['member_scope_id']==member['scope_id']and r['member_kind']=='approach']
            if len(prior)!=1:raise ValueError('one independently revalidated prefix interval required')
            pg=departure_guard(docs['plan'],me['approach'],me['departure'],cap['plan'],origin['floors'][str(scope['floor'])]);ids=scope['views']['iso']['route']['edges'][1:];cov=coverage(docs['iso'],axis,ids,scopes['inputs']['iso_source']['sha256'],scopes['inputs']['iso_graph']['sha256'])
            if cov['unresolved']or any(s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 for e in cov['edges']for s in e['segments']):raise ValueError('complete unique lower axis source paths required')
            handles={w['source_handle']for e in cov['edges']for s in e['segments']for w in s['witnesses']};ag=native_label_guard(docs['iso'],handles,me['departure']['member']['nominal_mm'],cap['iso']);r=select(scope,member,prior[0],plan,axis,routes,dn,pg,ag)
            for row in r['records']:
                old=known[row['axis_edge_id']].get('diameter_nominal_mm')
                if old not in [None,'']and old!=row['nominal_mm']:raise ValueError('old known axis DN conflicts; never overwrite')
                row['old_known_nominal_mm']=old
            r['fresh_native_axis_coverage']=cov;reports.append(r)
        except ValueError as exc:pending.append(dict(scope_id=scope['scope_id'],reason=str(exc)))
    checked();records=[r for report in reports for r in report['records']]
    if len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('competing uniform range writers')
    return dict(mode=MODE,inputs=inputs,source_preflight=preflight,groups=reports,records=records,pending=pending,
        counts=dict(scope_groups=len(scopes['records']),qualified_uniform_groups=len(reports),qualified_horizontal_DN_records=len(records),qualified_pure_horizontal_edges=sum(r['whole_horizontal_edge']for r in records),qualified_mixed_edge_scopes=sum(not r['whole_horizontal_edge']for r in records),qualified_horizontal_domains=sum(len(r['horizontal_segment_domains'])for r in records),new_unknown_whole_edge_DN_records=sum(r['whole_horizontal_edge']and r['old_known_nominal_mm']in[None,'']for r in records),excluded_vertical_domains=sum(len(g['excluded_vertical_domains'])for g in reports)),
        original_native_group_member_gate_and_caption_owners_reexecuted=True,plan_DN_source_partition_requalified_by_group_parent=True,
        selected_prefix_mapping_freshly_requalified_by_native_group_boundaries_member_roles_and_caption_owners=True,
        complete_unchanged_interval_parent_retained_as_lineage=True,complete_historical_interval_pipeline_replayed=False,
        graph_mutated=False,components_changed=False,physical_lengths_assigned=0,vertical_values_assigned=0,internal_node_identities_assigned=False,human_accepted=False,viewer_adoption_pending=True,whole_goal_complete=False)

def implementations():return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in ['qualified_member_caption_scope','reviewed_expression_metrics','rebuild_compound_riser_header_members','rebuild_compound_carrier_atom_origins','riser_header_interval_application','compound_member_interfaces','batch_native_path_coverage']})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('native uniform range implementation changed')
    output.mkdir(parents=True);p=output/'reviewed-uniform-subroute-DN.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))));return r
def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');p=output/'reviewed-uniform-subroute-DN.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementations()or sha(r['manifest']['path'])!=r['manifest']['sha256']or sha(p)!=r['output_sha256']:raise ValueError('uniform range receipt differs')
    fresh=compute(load(r['manifest']['path']))
    if encode(fresh)!=p.read_bytes():raise ValueError('native uniform range replay differs')
    return fresh
def main():
    p=argparse.ArgumentParser()
    for n in ['manifest','output','verify-output']:p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,counts=r['counts'],pending=r['pending']),flush=True)
if __name__=='__main__':main()
