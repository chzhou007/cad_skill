"""Rebuild source-qualified planar member intervals before axis DN composition."""
import argparse,copy,importlib,sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from native_replay_session import verify_once
from rebuild_anchor_bounded_main_batch import verify_output as verify_parent
from source_readability import read_source
from native_paired_end_labels import collect as end_labels
from compound_carrier_members import carrier_risks,member
from native_current_junction_reader import make_reader
from crossview_equipment_branch_inventory import native_tee
from match_source_checked_crossview_paths import selected_snapshot
from batch_native_path_coverage import collect as coverage
from native_plan_projection_lengths import unit_evidence,lengths
MODE='native_compound_carrier_member_projection_v1'

def member_graph(plan,records):
    nodes={};edges={};original_nodes={n['node_id']:n for n in plan['nodes']};original_edges={e['edge_id']:e for e in plan['edges']}
    for r in records:
        drawing_nodes=[a['plan_T']for a in r['anchors']]
        for nid,drawing,anchor in zip(r['member_node_ids'],drawing_nodes,r['anchors']):
            node=dict(copy.deepcopy(original_nodes[drawing]),node_id=nid,drawing_node_id=drawing,member_scope_id=r['member_scope_id'],physical_elevation_mm=None)
            if nid in nodes and nodes[nid]!=node:raise ValueError('member node lineage conflicts')
            nodes[nid]=node;equipment=anchor['equipment_id'];nodes.setdefault(equipment,copy.deepcopy(original_nodes[equipment]))
            branch=copy.deepcopy(original_edges[anchor['plan_branch']]);branch_id=r['member_scope_id']+':'+branch['edge_id'];original_id=branch['edge_id']
            if drawing not in(branch['start_node_id'],branch['end_node_id']):raise ValueError('native branch is not incident on member T')
            branch.update(edge_id=branch_id,drawing_edge_id=original_id,member_scope_id=r['member_scope_id'],nominal_mm=None,installed_whole_length_mm=None)
            for key in('start_node_id','end_node_id'):
                if branch[key]==drawing:branch[key]=nid
            if branch_id in edges and edges[branch_id]!=branch:raise ValueError('member branch duplicated with different ownership')
            edges[branch_id]=branch
        edge=dict(edge_id=r['member_edge_id'],drawing_edge_id=r['plan_edge_id'],member_scope_id=r['member_scope_id'],start_node_id=r['member_node_ids'][0],end_node_id=r['member_node_ids'][1],
            system=r['system'],floor_start=r['floor'],floor_end=r['floor'],attribute_paths=copy.deepcopy(r['plan_attribute_paths']),source_handles=[r['plan_LINE']],
            diameter_nominal_mm=r['nominal_mm'],source_level_literal=r['source_level_literal'],physical_elevation_mm=None,
            plan_run_centerline_mm=r['plan_run_centerline_mm'],installed_whole_length_mm=None,net_pipe_cut_length_mm=None,component_member_allocation='unresolved',source_mapping_id=r['mapping_id'])
        if edge['edge_id']in edges:raise ValueError('duplicate member main')
        edges[edge['edge_id']]=edge
    return dict(scope='source_checked_member_intervals_and_original_logical_branches_only',nodes=list(nodes.values()),edges=list(edges.values()),
        source_drawing_graph_unchanged=True,global_topology_complete=False,other_member_connections_inferred=False,
        component_or_equipment_instances_created=False,calculation_ready=False,human_accepted=False)

def compute(manifest,announce=lambda _:None):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('member projection input changed')
    checked();announce('Replaying original native parents and current mapping source owners')
    parent=verify_once(paths['parent_main_proof'].parent,verify_parent)
    if encode(parent)!=paths['parent_main_proof'].read_bytes():raise ValueError('current native parent differs')
    for key,digest in parent['source_hashes'].items():
        if key not in paths or sha(paths[key])!=digest:raise ValueError('native parent source differs '+key)
    batch=load(paths['batch_result']);axis=load(paths['axis_graph']);plan=load(paths['plan_graph']);raw=load(paths['raw_axis_graph'])
    floor=manifest['floor'];f=str(floor)
    if batch['identity_graph_sha256']!=sha(paths['axis_graph'])or sha(paths['plan_graph'])!=sha(paths['plan_graph_'+f])or sha(paths['plan_source'])!=sha(paths['plan_source_'+f]):raise ValueError('member graph/mapping source binding differs')
    plan_doc,plan_preflight=read_source(paths['plan_source']);axis_doc,axis_preflight=read_source(paths['axis_source'])
    barriers=carrier_risks(plan_doc,plan,sha(paths['plan_source']));captions=end_labels(axis_doc)
    by_caption={};competing=set()
    for pair in captions['pairs']:
        for row in pair['observations']:
            key=row['native_pipe']['source_LINE']
            if key in by_caption:competing.add(key)
            else:by_caption[key]=row
    for key in competing:del by_caption[key]
    byplan={}
    for corridor in barriers['corridors']:
        for row in corridor['edges']:byplan.setdefault(row['edge_id'],{})[corridor['source_LINE']]=corridor
    units=unit_evidence(plan_doc,load(paths['unit_policy']));sh=sha(paths['plan_source']);gh=sha(paths['plan_graph']);ah=sha(paths['axis_source']);ag=sha(paths['axis_graph'])
    reader=make_reader(load(paths['current_T_source_config']),sh,gh);tee_cache={};records=[];pending=[];screened=0
    inherited={r['mapping_id']:r for r in raw['sourceFullPlanBatchAttributes']['records']}
    for row in batch['floors'][f]['records']:
        if not any(eid in byplan for eid in row['plan_edges']):continue
        screened+=1
        try:
            if row['kind']!='same_floor_T_to_T_main'or len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('member interval needs an existing one-to-one main mapping')
            native={}
            for view,doc,graph,source_hash,graph_hash in(('plan',plan_doc,plan,sh,gh),('iso',axis_doc,axis,ah,ag)):
                if selected_snapshot(graph,row[view+'_edges'])!=row[view+'_snapshot']:raise ValueError('current mapped source snapshot differs')
                cov=coverage(doc,graph,row[view+'_edges'],source_hash,graph_hash);junctions={}
                for nid in(row[view+'_start'],row[view+'_end']):
                    key=(view,nid)
                    if key not in tee_cache:tee_cache[key]=(reader if view=='plan'else native_tee)(doc,graph,nid,source_hash,graph_hash)
                    junctions[nid]=tee_cache[key]
                native[view]=dict(coverage=cov,junctions=junctions,source_sha256=source_hash,graph_sha256=graph_hash,snapshot=selected_snapshot(graph,row[view+'_edges']))
            lines={view:{w['source_handle']for e in native[view]['coverage']['edges']for s in e['segments']for w in s.get('witnesses',[])if w.get('scope')=='modelspace'}for view in native}
            if any(len(v)!=1 for v in lines.values()):raise ValueError('member interval has mixed native LINE witnesses')
            pl=next(iter(lines['plan']));al=next(iter(lines['iso']))
            if al not in by_caption:raise ValueError('no unique native paired end caption for axis member')
            for pn,an in zip((row['plan_start'],row['plan_end']),(row['iso_start'],row['iso_end'])):
                if batch['floors'][f]['junction_mapping'].get(pn)!=an:raise ValueError('member endpoint correspondence differs')
            metric=lengths(plan,native['plan']['coverage'],row,units)
            corridor=byplan[row['plan_edges'][0]].get(pl)
            if corridor is None:raise ValueError('native member LINE is outside the compound declaration corridor')
            result=member(row,plan,axis,pl,al,corridor,by_caption[al],native,metric)
            old=inherited[row['mapping_id']]
            result['superseded_scalar_observation']=dict(plan_nominal_mm=old['plan_drawn_nominal_mm'],whole_axis_nominal_mm=old['whole_axis_nominal_mm'],
                reason='scalar_T_inheritance_did_not_identify_a_compound_carrier_member',old_observation_preserved=True)
            records.append(result)
        except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],plan_edges=row['plan_edges'],axis_edges=row['iso_edges'],reason=str(exc)))
    if len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('member axis writers overlap')
    checked();return dict(mode=MODE,floor=floor,records=records,pending=pending,carrier_barriers=barriers,native_end_labels=captions,
        source_preflight=dict(plan=plan_preflight,iso=axis_preflight),unit_evidence=units,member_local_graph=member_graph(plan,records),
        counts=dict(current_mapping_scopes_screened=screened,member_main_intervals=len(records),member_run_centerlines=len(records),pending=len(pending)),
        source_hashes={k:sha(p)for k,p in paths.items()},source_drawing_graphs_unchanged=True,DN_selected_from_axis_value=False,
        previous_scalar_observations_retained=True,other_member_connections_inferred=False,global_plan_topology_complete=False,human_accepted=False)

def implementation_hashes():
    names=('native_paired_end_labels','compound_carrier_members','native_main_endpoint_extent','native_current_junction_reader','native_plan_projection_lengths','batch_native_path_coverage','source_compound_dn_evidence','source_readability')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path),lambda s:print(s,flush=True));output.mkdir(parents=True);target=output/'member-projections.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'member-projections.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('member projection dependencies changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('native member projection replay differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification uses original inputs')
            result=verify_output(a.verify_output)
        else:
            if not(a.manifest and a.output):p.error('manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
