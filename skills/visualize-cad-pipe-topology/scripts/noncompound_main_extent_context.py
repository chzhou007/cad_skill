"""Compose checked, noncompound T-to-T centreline lengths onto axis identities."""
import copy,sys,math,collections
from pathlib import Path
owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(owner)not in sys.path:sys.path.insert(0,str(owner))
from confirm_crossview_paths import load,sha
from rebuild_noncompound_main_extents import verify_output,MODE as SOURCE_MODE
from native_replay_session import verify_once
MODE='qualified_native_noncompound_main_extents_v1'


def component_identities(raw_edge,rendered_edge,rendered):
    def names(edge):
        result=[]
        for item in edge.get('equipment_inventory',[]):
            group=item.get('device_names',[])
            if len(group)!=item['count']:raise ValueError('component inventory names/count differ')
            result.extend(group)
        return result
    source=names(raw_edge);display=names(rendered_edge)
    instances=[r for r in rendered.get('instances',[])if r.get('edge_id')==raw_edge['edge_id']]
    if len({r['id']for r in instances})!=len(instances):raise ValueError('component instance identity repeats')
    if collections.Counter(source)!=collections.Counter(r.get('source_device_name')for r in instances)or collections.Counter(display)!=collections.Counter(r.get('name')for r in instances):raise ValueError('component source/display identities or edge ownership differ')
    return [dict(instance_id=r['id'],source_device_name=r['source_device_name'],display_name=r['name'],source_top_handle=r.get('source_top_handle'),edge_id=r['edge_id'])for r in instances]


def collect(raw,rendered,proof,bindings,prior):
    if (proof.get('mode')!=SOURCE_MODE or proof.get('compound_parent_replayed')is not True
        or any(proof.get(k)is not False for k in('local_topology_changed','source_paths_mutated','human_accepted'))
        or proof.get('installed_lengths_assigned')!=0 or not proof.get('existing_correspondences_unchanged')):
        raise ValueError('unsupported noncompound native main proof')
    if proof['source_hashes']['raw_axis_graph']!=bindings['axis_graph']:raise ValueError('native main belongs to another raw graph')
    member=prior.get('compound_member_mains',{})
    if member.get('source_bindings',{}).get('native_proof')!=proof['source_hashes']['member_proof']:raise ValueError('current compound member parent differs')
    owners=set()
    for key in('compound_member_mains','member_plan_runs','ordered_group_plan_runs','ordered_anchor_branches','anchor_bounded_mains'):
        for r in prior.get(key,{}).get('records',[]):
            if r.get('axis_edge_id'):owners.add(r['axis_edge_id'])
    original={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for r in proof['records']:
        eid=r['axis_edge_id'];edge=original[eid];scope=edge.get('batch_plan_attribute_scopes')
        if eid in seen or eid in owners or eid in proof['retained_member_axis_edges']:raise ValueError('main conflicts with an existing attribute owner')
        if scope!=r['old_scope']or scope['mapping_id']!=r['mapping_id']or scope['plan_edges']!=[r['plan_edge_id']]or scope['plan_drawn_nominal_mm']!=r['nominal_mm']:raise ValueError('native main mapping or plan DN changed')
        if any(edge.get(k)!=view[eid].get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths')):raise ValueError('rendered main differs from raw identity')
        components=component_identities(edge,view[eid],rendered)
        if any(edge.get(k)!=r[v]for k,v in(('system','system'),('start_node_id','axis_start_node'),('end_node_id','axis_end_node'),('attribute_paths','axis_attribute_paths'))):raise ValueError('native main endpoint snapshot differs')
        if any(edge.get(k)for k in('axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','external_feed_plan_attributes')):raise ValueError('unrelated native attribute owner')
        nominal=r['nominal_mm'];value=r['complete_horizontal_centerline_route_mm'];projection=r['source_projection']
        if any(isinstance(x,bool)or not isinstance(x,(int,float))or not math.isfinite(x)or x<=0 for x in(nominal,value)):raise ValueError('known plan DN and complete centreline required')
        if projection is None or abs(projection['value_mm']-value)>.0001 or r['whole_installed_length_mm']is not None or r['net_pipe_cut_length_mm']is not None:raise ValueError('physical installed length was promoted')
        if r['plan_DN_record']['nominal_mm']!=nominal or r['plan_DN_record']['scope_paths']!=r['native_source_evidence']['plan']['snapshot']['edges'][0]['attribute_paths']:raise ValueError('qualified local DN scope differs')
        if any(r['source_hashes'][v][k+'_sha256']!=scope[k+'_sha256'][v]for v in('plan','iso')for k in('source','graph')):raise ValueError('native source hashes differ')
        keys=('mapping_id','axis_edge_id','plan_edge_id','floor','system','nominal_mm','endpoint_relations','axis_start_node','axis_end_node','axis_attribute_paths','plan_nodes','axis_nodes','complete_horizontal_centerline_route_mm','source_projection','whole_installed_length_mm','net_pipe_cut_length_mm','source_paths_mutated','plan_DN_record','DN_status','source_hashes','metric_reader')
        record={k:copy.deepcopy(r[k])for k in keys};record.update(component_instance_identities=components,related_HIL_confirmation_inherited=False,human_accepted=False)
        seen.add(eid);records.append(record)
    if len(records)!=proof['counts']['requalified_main_edges']:raise ValueError('complete main inventory differs')
    return dict(mode=MODE,records=records,axis_edges=len(records),source_bindings=bindings,
        existing_attribute_owners_preserved=True,compound_carriers_excluded=True,source_paths_mutated=False,
        installed_lengths_assigned=0,local_topology_changed=False,human_accepted=False)


def from_artifact(raw_path,rendered_path,proof_path,prior):
    paths=list(map(Path,(raw_path,rendered_path,proof_path)));before={str(p):sha(p)for p in paths}
    proof=verify_once(Path(proof_path).parent,verify_output)
    receipt=load(Path(proof_path).parent/'receipt.json');manifest=load(receipt['manifest']['path'])
    member_path=Path(manifest['inputs']['member_proof']['path'])
    if sha(member_path)!=proof['source_hashes']['member_proof']:raise ValueError('current member artifact changed')
    from compound_member_attribute_context import collect as member_context
    raw,rendered=load(raw_path),load(rendered_path);member=prior['compound_member_mains']
    expected=member_context(raw,rendered,load(member_path),member['source_bindings'])
    if member!=expected:raise ValueError('retained member context differs from replayed parent')
    result=collect(raw,rendered,proof,dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),member_proof=sha(member_path)),prior)
    if any(sha(p)!=digest for p,digest in before.items()):raise ValueError('native context inputs changed')
    return result
