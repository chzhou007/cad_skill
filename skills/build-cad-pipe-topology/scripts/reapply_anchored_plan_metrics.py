"""Reapply existing metric kernels to current mapped horizontal scopes in batch.

Split children may retain an ancestor's coarse joint hold. Only native joint
origins, disjoint current extents and exact T/path evidence can clear that hold.
"""
import argparse,collections,copy,csv,importlib,json,math,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from crossview_equipment_branch_inventory import index_graph,native_tee
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
from cycle_gate_plan_lengths import qualify
from batch_native_path_coverage import collect as coverage
from anchor_bounded_main_paths import component_profiles
from native_inline_joint_path_coverage import native_joint
from repair_native_flexible_joints import fingerprint
from third_arm_crossview_paths import native_component_profiles
from member_external_anchored_routes import scoped_components,ordered_components
from native_line_path_evidence import _on

MODE='source_scoped_anchored_plan_metric_reapplication_v1'
COARSE='source_drawn_pipe_only_flexible_joint_interior_unknown'

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as handle:return list(csv.DictReader(handle))

def overlap(a,b,c,d,tol=.05):
    length=math.dist(a,b)
    if length<=tol:return False
    u=[(b[i]-a[i])/length for i in(0,1)]
    if any(abs((p[0]-a[0])*u[1]-(p[1]-a[1])*u[0])>tol for p in(c,d)):return False
    low,high=sorted(sum((p[i]-a[i])*u[i]for i in(0,1))for p in(c,d))
    return min(length,high)-max(0,low)>tol

def joint_scope(edge,joints):
    relevant=[];outside=[]
    for joint in joints:
        if joint['system']!=edge['system']:continue
        c,d=[p[:2]for p in joint['contact_points_wcs']]
        intersects=any(overlap(a,b,c,d)for path in edge['attribute_paths']for a,b in zip(path,path[1:]))
        (relevant if intersects else outside).append(copy.deepcopy(joint))
    require(not relevant,'actual native inline joint remains inside current metric scope')
    return dict(status='all_original_native_joint_origins_outside_current_child_scope',excluded_joint_origins=outside,relevant_joint_origins=[],source_metadata_unchanged=True,physical_joint_lengths_assigned=0)

def joint_origins(doc,graph,inventory,template):
    name=template['block_name'];digest=template['block_fingerprint_sha256']
    require(name in doc.blocks and fingerprint(doc.blocks[name])==digest,'original joint template changed')
    declared={r['source_handle']for r in graph.get('expertFlexibleJointRepair',{}).get('steps',[])}
    population={e.dxf.handle for e in doc.modelspace().query('INSERT')if e.dxf.name==name}
    rows=[r for r in inventory if r.get('source_block_name')==name];handles=[r.get('source_top_handle')or r.get('source_handle')for r in rows]
    require(declared and declared==population==set(handles)and len(handles)==len(set(handles)),'joint origin population needs its original complete native owner')
    edges={e['edge_id']:e for e in graph['edges']}
    return [native_joint(doc,graph,edges[row['edge_id']],row,name,digest,.05)for row in rows]

def inherited_holds(context,eid):
    return [dict(provider=key,mapping_id=r.get('mapping_id'),reasons=copy.deepcopy(r['incomplete_reasons']))for key,root in context.items()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')==eid and r.get('incomplete_reasons')]

def clearable(edge,holds):
    reasons={reason for hold in holds for reason in hold['reasons']}
    require(not reasons or reasons=={COARSE},'existing specific incomplete reasons need their own source owner')
    if reasons:
        require(edge.get('path_length_scope')==COARSE and bool(edge.get('split_source_edge')),'coarse joint hold is not a source-tracked split child')
    if edge.get('path_length_complete')is False:
        require(edge.get('path_length_scope')==COARSE,'unknown original path extent needs its specific owner')
    return bool(reasons or edge.get('path_length_scope')==COARSE)

def checked_parent(manifest):
    inputs=manifest['inputs'];spec=inputs['provider'];snapshot=inputs['provider_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-anchored-metric-parent-')as temporary:
        output=Path(temporary)/'checked';names=['external-member-routes.json','provider-inventory.json','member-local-graph.json']
        command=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complete_owner.py'),'--skills-root',str(Path(snapshot['path']).parent/'skills'),'--snapshot',snapshot['path'],'--native-run',str(Path(spec['path']).parent),'--owner','rebuild_member_external_routes','--result-files',json.dumps(names),'--output',str(output)]
        run=subprocess.run(command,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf8')
        require(run.returncode==0,'original complete provider failed: '+run.stderr[-4000:]);raw=(output/'provider-inventory.json').read_bytes()
        require(raw==Path(spec['path']).read_bytes()and load(output/'execution.json')['owner']=='rebuild_member_external_routes','complete provider identity differs')
        return json.loads(raw)

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():require(all(sha(paths[k])==v['sha256']for k,v in inputs.items()),'anchored metric input changed')
    checked();announce('Replaying the complete original provider in its pinned runtime');provider=checked_parent(manifest)
    axis=load(paths['axis_graph']);ad,ap=read_source(paths['axis_source']);ai=csvrows(paths['axis_components']);an,ae,_=index_graph(axis)
    context=load(paths['viewer_manifest'])['attributeValueContext'];config=load(paths['current_T_source_config']);todo={r['edge_id']:r for r in provider['remaining_horizontal_attributes']if not r['complete_centerline']};by={r['edge_id']:r for r in provider['records']}
    require(provider['original_provider_inventory_inputs']['axis_graph']==inputs['axis_graph'],'metric uses another axis graph')
    records=[];held=[];floors={}
    for floor in(1,2,3):
        f=str(floor);require(provider['original_provider_inventory_inputs']['plan_graph_'+f]==inputs['plan_graph_'+f],'metric uses another plan graph')
        plan=load(paths['plan_graph_'+f]);pn,pe,_=index_graph(plan);pi=csvrows(paths['plan_components_'+f]);doc,readable=read_source(paths['plan_source_'+f]);units=unit_evidence(doc,load(paths['unit_policy_'+f]));reader=current_plan_reader(config,inputs['plan_source_'+f]['sha256'],inputs['plan_graph_'+f]['sha256']);mapping=provider['ordinary_junction_mappings'][f];candidates=[]
        floor_todo=[r for r in todo.values()if r['floor']==floor]
        for current in floor_todo:
            eid=current['edge_id'];obs=[o for o in by[eid]['correspondence_observations']if o['domain']=='ordinary_local_graph'and len(o['plan_edges'])==1 and len(o.get('grouped_axis_edges',[eid]))==1]
            item=dict(edge_id=eid,floor=floor,next_scope=current['next_scope'])
            try:
                require(len(obs)==1,'unique ordinary whole-path correspondence required; keep member or partial owner')
                o=obs[0];require(not o.get('source_detail_difference'),'existing native source detail discrepancy holds adoption')
                require(current['next_scope']!='known_inline_assembly_interiors_missing_physical_length','original inline-assembly owner retains unknown physical length')
                edge=pe[o['plan_edges'][0]];axis_edge=ae[eid];holds=inherited_holds(context,eid);coarse=clearable(edge,holds)
                pairs=[[edge['start_node_id'],edge['end_node_id']],[edge['end_node_id'],edge['start_node_id']]]
                require(any([mapping.get(n)for n in ends]==[axis_edge['start_node_id'],axis_edge['end_node_id']]for ends in pairs),'current ordinary endpoint correspondence is incomplete')
                pp=component_profiles(pi,[edge['edge_id']])[0];aa=component_profiles(ai,[eid])[0];require(pp==aa,'native source component profiles differ')
                native=coverage(doc,plan,[edge['edge_id']],inputs['plan_source_'+f]['sha256'],inputs['plan_graph_'+f]['sha256'])
                tees={v:{}for v in('plan','axis')}
                for n in(edge['start_node_id'],edge['end_node_id']):tees['plan'][n]=reader(doc,plan,n,inputs['plan_source_'+f]['sha256'],inputs['plan_graph_'+f]['sha256'])
                for n in(axis_edge['start_node_id'],axis_edge['end_node_id']):tees['axis'][n]=native_tee(ad,axis,n,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
                spec=dict(mapping_id=o['mapping_id'],plan_edges=o['plan_edges'],iso_edges=[eid],floor=floor,system=edge['system'],classification='horizontal_only',native_path_evidence=dict(plan=native),component_profiles=dict(plan=pp,iso=aa),iso_start=axis_edge['start_node_id'],iso_end=axis_edge['end_node_id'])
                metric=qualify(plan,axis,spec,units,manifest['horizontal_directions_degrees'])
                candidates.append(dict(item,metric=metric,original_observation=copy.deepcopy(o),native_T=tees,coarse_hold=coarse,original_incomplete_holds=holds))
            except (ValueError,KeyError)as exc:held.append(dict(item,reason=str(exc)))
        joints=joint_origins(doc,plan,pi,load(paths['joint_template']))if any(r['coarse_hold']for r in candidates)else[]
        eligible=[]
        for row in candidates:
            try:
                row['joint_exclusion']=joint_scope(pe[row['metric']['plan_edge_id']],joints)if row['coarse_hold']else None
                eligible.append(row)
            except ValueError as exc:held.append(dict(edge_id=row['edge_id'],floor=floor,next_scope=row['next_scope'],reason=str(exc)))
        candidates=eligible
        profiles={}
        if candidates:
            profiles=dict(plan=native_component_profiles(doc,plan,pi,[r['metric']['plan_edge_id']for r in candidates],'plan'),axis=native_component_profiles(ad,axis,ai,[r['edge_id']for r in candidates],'iso'))
        for row in candidates:
            metric=row['metric'];edge=pe[metric['plan_edge_id']];axis_edge=ae[row['edge_id']]
            exclusion=row['joint_exclusion']
            scopes={v:scoped_components(profiles[v],e['attribute_paths'],e['edge_id'])for v,e in [('plan',edge),('axis',axis_edge)]}
            ordered_paths={v:copy.deepcopy(e['path_points'])for v,e in [('plan',edge),('axis',axis_edge)]}
            for v,e in [('plan',edge),('axis',axis_edge)]:
                if e['start_node_id']!=(metric['plan_nodes'][0]if v=='plan'else metric['axis_nodes'][0]):ordered_paths[v].reverse()
            # The correspondence may reverse plan direction relative to axis.
            if mapping[edge['start_node_id']]!=axis_edge['start_node_id']:ordered_paths['plan'].reverse()
            pairs=ordered_components(scopes,ordered_paths)
            records.append(dict(metric,source_scope_id='ANCHORED-METRIC:'+row['original_observation']['mapping_id'],original_observation=row['original_observation'],native_T=row['native_T'],native_component_pairs=pairs,original_incomplete_holds=row['original_incomplete_holds'],coarse_joint_hold_exclusion=exclusion,plan_source_sha256=inputs['plan_source_'+f]['sha256'],plan_graph_sha256=inputs['plan_graph_'+f]['sha256'],axis_source_sha256=inputs['axis_source']['sha256'],native_axis_graph_sha256=inputs['axis_graph']['sha256'],DN_evidence_changed=False,related_HIL_confirmation_inherited=False))
        floors[f]=dict(source_preflight=readable,units=units,complete_native_joint_origins=joints,candidate_count=len(candidates),pending_horizontal_length_edges=len(floor_todo));announce('Floor '+f+': '+str(len(candidates))+' native metric scopes')
    checked();return dict(mode=MODE,inputs=inputs,records=records,held=held,floors=floors,complete_original_provider_replayed=True,all_pending_horizontal_length_scopes_screened=True,original_metric_readers_reused=True,native_T_paths_components_and_joint_origins_replayed=True,source_graphs_mutated=False,component_owners_changed=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False,counts=dict(pending_horizontal_length_scopes=len(todo),complete_centerlines=len(records),coarse_child_holds_proved_outside_scope=sum(r['coarse_joint_hold_exclusion']is not None for r in records),held=len(held)))

def implementations():
    root=Path(__file__).resolve().parents[2];names=('cycle_gate_plan_lengths','native_main_interval_metrics','native_plan_projection_lengths','native_main_endpoint_extent','native_inline_joint_path_coverage','repair_native_flexible_joints','third_arm_crossview_paths','member_external_anchored_routes','native_current_junction_reader','batch_native_path_coverage','source_readability')
    return dict(entry=sha(__file__),parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complete_owner.py'),**{n:sha(importlib.import_module(n).__file__)for n in names})

def inventory_from(original,proof,effective):
    """Adopt only the actual rendered scalar metrics; never add correspondences."""
    result=copy.deepcopy(original);values={r['edge_id']:r['values']for r in effective};metrics={r['axis_edge_id']:r for r in proof['records']};by={r['edge_id']:r for r in original['records']};remaining=[];completed=[]
    for eid,r in metrics.items():
        require(r['original_observation']in by[eid]['correspondence_observations'],'metric correspondence no longer belongs to original provider')
        require(values[eid].get('anchored_metric_complete_centerline_mm')==r['complete_horizontal_centerline_mm']and values[eid].get('anchored_metric_mapping_id')==r['source_scope_id'],'actual metric reader did not adopt source value')
    for old in original['remaining_horizontal_attributes']:
        row=copy.deepcopy(old);eid=row['edge_id']
        if eid in metrics:
            require(not row['complete_centerline'],'metric overwrites an already known complete centreline')
            row['complete_centerline']=True
            row['attributes'].update({k:v for k,v in values[eid].items()if k.startswith('anchored_metric_')})
            if row['known_whole_DN']is not None:completed.append(eid);continue
            row['next_scope']='known_anchored_metric_plan_DN_scope_unresolved'
        remaining.append(row)
    require(set(metrics)<={r['edge_id']for r in original['remaining_horizontal_attributes']},'metric scope is outside original horizontal frontier')
    result.update(mode=MODE,remaining_horizontal_attributes=remaining,anchored_metric_attribute_observations=copy.deepcopy(proof['records']),new_attribute_complete_axis_edges=sorted(completed),all_old_correspondences_and_member_domains_preserved=True,DN_or_vertical_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    counts=dict(collections.Counter(r['next_scope']for r in remaining));result['counts']['horizontal_next_scopes']=counts
    frontier=copy.deepcopy(original['current_horizontal_frontier']);frontier.update(status='source_scoped_anchored_metrics_adopted',records=remaining,remaining_by_next_scope=counts,pure_horizontal_remaining_attributes=len(remaining),pure_horizontal_complete=frontier['pure_horizontal_complete']+len(completed),remaining_by_floor=dict(collections.Counter(str(r['floor'])for r in remaining)))
    result['current_horizontal_frontier']=frontier
    require(result['records']==original['records']and result['member_domain_observations']==original['member_domain_observations']and result['ordinary_junction_mappings']==original['ordinary_junction_mappings']and result['current_component_inventory']==original['current_component_inventory'],'metric inventory changed topology or components')
    return result
def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh anchored metric output');before=implementations();proof=compute(load(manifest),lambda v:print(v,flush=True));require(before==implementations(),'metric implementation changed');output.mkdir(parents=True);(output/'anchored-plan-metrics.json').write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(output/'anchored-plan-metrics.json'),human_accepted=False)));return proof
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(output/'anchored-plan-metrics.json')==receipt['output_sha256'],'anchored metric receipt changed');proof=compute(load(receipt['manifest']['path']));require(encode(proof)==(output/'anchored-plan-metrics.json').read_bytes(),'independent native anchored metric replay differs');return proof
def main():
    p=argparse.ArgumentParser()
    for k in('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
