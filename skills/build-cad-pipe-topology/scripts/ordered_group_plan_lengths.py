"""Allocate checked path groups by native T order, never by drawn ratios.

Independently anchored ends fix orientation. Both complete native corridors and
every T replay before index correspondence. The inherited metric readers then
read each actual plan child, including qualified inline joints. Missing joint
lengths remain unknown; a route group total is never copied to its children.
"""
import argparse,copy,csv,hashlib,importlib,math,sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from batch_native_main_chains import source_check
from match_source_checked_crossview_paths import selected_snapshot
from native_plan_projection_lengths import unit_evidence,lengths
from native_inline_joint_path_coverage import collect as inline_coverage
from anchored_floor_main_plan_attributes import inline_projection
from attach_anchored_floor_main_attributes import horizontal_domain
from native_replay_session import verify_once
MODE='native_ordered_group_child_plan_lengths_v1'

def independent_anchors(records,excluded):
    result={};owners={}
    for r in records:
        if r['mapping_id']in excluded:continue
        for side in ('start','end'):
            key=(r['system'],r['plan_'+side]);value=r['iso_'+side]
            if key in result and result[key]!=value:raise ValueError('independent parent anchors conflict')
            result[key]=value;owners.setdefault(key,[]).append(r['mapping_id'])
    return result,owners

def allocate_group(docs,graphs,row,anchors,units,components,template,hashes,angles):
    system=row['system'];floor=row['floor']
    if (anchors.get((system,row['plan_start']))!=row['iso_start']or anchors.get((system,row['plan_end']))!=row['iso_end']):raise ValueError('both ordered group ends need independent fixed anchors')
    if (row['kind']!='native_main_chain_between_independent_junctions'or len(row['plan_edges'])<2
        or len(row['plan_edges'])!=len(row['iso_edges'])or len(row['plan_nodes'])!=len(row['iso_nodes'])
        or len(row['plan_nodes'])!=len(row['plan_edges'])+1):raise ValueError('ordered native segmentation differs')
    for view in ('plan','iso'):
        if (row[view+'_nodes'][0]!=row[view+'_start']or row[view+'_nodes'][-1]!=row[view+'_end']
            or selected_snapshot(graphs[view],row[view+'_edges'])!=row[view+'_snapshot']):raise ValueError('ordered group orientation or native snapshot changed')
    # This inherited checker examines the full native corridor, not just unused
    # edges. Removing a competing route cannot manufacture order/uniqueness.
    native=source_check(docs,graphs,row,hashes)
    plan=graphs['plan'];by={e['edge_id']:e for e in plan['edges']};nodes={n['node_id']:n for n in plan['nodes']};records=[]
    for i,(pe,ie)in enumerate(zip(row['plan_edges'],row['iso_edges'])):
        edge=by[pe];child=dict(floor=floor,system=system,plan_edges=[pe],iso_edges=[ie],iso_start=row['iso_nodes'][i],iso_end=row['iso_nodes'][i+1])
        axis_path=horizontal_domain(graphs['iso'],child,angles)
        if edge.get('source_view_context')is not None:raise ValueError('detail spans need their separate member plan metric owner')
        if edge.get('source_flexible_joints'):
            h=dict(hashes['plan']);policy=dict(h,edges=[pe],block_name=template['block_name'],block_fingerprint_sha256=template['block_fingerprint_sha256'])
            joint=inline_coverage(docs['plan'],plan,components,policy,h)['records'][0]
            projection=inline_projection(plan,joint,child,units);reader='inherited_native_inline_pipe_XY';complete=None;inline_unknown=[j['source_handle']for j in joint['joints']]
            evidence=joint
        else:
            projection=lengths(plan,native['plan']['path_coverage'],child,units);reader='inherited_native_plan_projection';inline_unknown=[];evidence=None;complete=None
            if len(edge['attribute_paths'])==1:
                p=edge['attribute_paths'][0];ends=[nodes[edge[k]]for k in('start_node_id','end_node_id')]
                if all(math.dist(point,[node['x'],node['y']])<=.05 for point,node in zip((p[0],p[-1]),ends)):complete=projection['value_mm']
        if projection['installed_whole_edge_length_mm']is not None or projection['value_mm']<=0:raise ValueError('inherited child metric was promoted or empty')
        records.append(dict(mapping_id=row['mapping_id'],axis_edge_id=ie,plan_edge_id=pe,index_in_group=i,floor=floor,system=system,
            plan_Ts=row['plan_nodes'][i:i+2],axis_Ts=row['iso_nodes'][i:i+2],axis_attribute_paths=[copy.deepcopy(axis_path)],
            known_plan_pipe_XY_mm=projection['value_mm'],complete_horizontal_run_centerline_mm=complete,physical_installed_length_mm=None,net_pipe_cut_length_mm=None,
            source_projection=projection,metric_reader=reader,inline_source_proof=evidence,unknown_inline_joint_handles=inline_unknown,
            length_allocation_method='native_T_order_between_two_independent_anchors',axis_drawn_lengths_or_ratios_used=False,
            child_equipment_or_external_interface_identity_inferred=False,human_accepted=False))
    return dict(mapping_id=row['mapping_id'],floor=floor,system=system,records=records,
        internal_main_junction_correspondence=[dict(plan_node=p,axis_node=a,basis='unique_native_corridor_order_with_fixed_ends')for p,a in zip(row['plan_nodes'][1:-1],row['iso_nodes'][1:-1])],
        native_source_check=native,known_plan_pipe_XY_total_mm=sum(r['known_plan_pipe_XY_mm']for r in records),
        complete_run_children=sum(r['complete_horizontal_run_centerline_mm']is not None for r in records),partial_pipe_XY_children=sum(r['complete_horizontal_run_centerline_mm']is None for r in records),
        physical_group_installed_length_mm=None,human_accepted=False)

def implementation_hashes():
    names=('batch_native_main_chains','native_plan_projection_lengths','native_inline_joint_path_coverage','anchored_floor_main_plan_attributes',
        'attach_anchored_floor_main_attributes','match_source_checked_crossview_paths','crossview_equipment_branch_inventory','source_readability')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('ordered group input changed')
    checked();parent=load(paths['parent_manifest']);context=parent['attributeValueContext'];batch=load(paths['batch_result']);receipt=load(paths['batch_receipt']);axis=load(paths['axis_graph']);raw=load(paths['parent_graph'])
    if (parent['sourceHashes']['graph']!=sha(paths['parent_graph'])or receipt['output_sha256']!=sha(paths['batch_result'])
        or batch['identity_graph_sha256']!=sha(paths['axis_graph'])):raise ValueError('qualified source batch/axis scope changed')
    selected={g['mapping_id']for g in context['groups']};groups=[];pending=[];preflight={};template=load(paths['inline_origin'])
    if not selected:raise ValueError('no qualified uniform native groups')
    if template.get('confirmation_basis')!='source_geometry_calibrated'or not template.get('expert_evidence'):raise ValueError('inherited inline template provenance missing')
    docs_axis,preflight['iso']=read_source(paths['axis_source']);angles=load(paths['group_policy'])['isometric_horizontal_directions_degrees'];seen=set()
    from rebuild_full_plan_DN import PARENTS
    for floor,data in batch['floors'].items():
        rows=[r for r in data['records']if r['mapping_id']in selected]
        if not rows:continue
        plan=load(paths['plan_graph_'+floor]);doc,preflight[floor]=read_source(paths['plan_source_'+floor]);units=unit_evidence(doc,load(paths['unit_policy_'+floor]))
        kind=manifest['plan_parent_modes'][floor]
        if kind not in PARENTS:raise ValueError('unknown local plan owner')
        native_parent=verify_once(paths['plan_graph_'+floor].parent,importlib.import_module(PARENTS[kind]).verify_output)
        if native_parent['output_graph_sha256']!=sha(paths['plan_graph_'+floor]):raise ValueError('current local plan owner differs')
        with paths['components_'+floor].open(encoding='utf-8-sig',newline='')as stream:components=list(csv.DictReader(stream))
        anchors,owners=independent_anchors(data['records'],selected)
        hashes=dict(plan=dict(source_sha256=sha(paths['plan_source_'+floor]),graph_sha256=sha(paths['plan_graph_'+floor]),inventory_sha256=sha(paths['components_'+floor])),
            iso=dict(source_sha256=sha(paths['axis_source']),graph_sha256=sha(paths['axis_graph'])))
        for row in rows:
            if row['mapping_id']in seen:raise ValueError('duplicate selected group')
            seen.add(row['mapping_id']);original=next(r for r in raw['sourceFullPlanBatchAttributes']['records']if r['mapping_id']==row['mapping_id'])
            if original['mapping_receipt_sha256']!=sha(paths['batch_receipt'])or original['plan_edges']!=row['plan_edges']or original['iso_edges']!=row['iso_edges']:raise ValueError('qualified axis path group differs')
            for eid in row['iso_edges']:
                old=next(e for e in axis['edges']if e['edge_id']==eid);current=next(e for e in raw['edges']if e['edge_id']==eid)
                if any(old.get(k)!=current.get(k)for k in('start_node_id','end_node_id','system','attribute_paths')):raise ValueError('qualified axis child geometry changed')
            try:group=allocate_group(dict(plan=doc,iso=docs_axis),dict(plan=plan,iso=axis),row,anchors,units,components,template,hashes,angles)
            except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],reason=str(exc)));continue
            group['independent_anchor_mapping_ids']={side:owners[(row['system'],row['plan_'+side])]for side in('start','end')};group['source_sha256']={k:v['source_sha256']for k,v in hashes.items()};group['plan_graph_sha256']=hashes['plan']['graph_sha256'];groups.append(group)
    if seen!=selected:raise ValueError('qualified group population omitted')
    checked();records=[r for g in groups for r in g['records']]
    return dict(mode=MODE,groups=groups,pending=pending,source_preflight=preflight,counts=dict(selected_groups=len(selected),source_checked_groups=len(groups),child_plan_metrics=len(records),
        complete_run_children=sum(r['complete_horizontal_run_centerline_mm']is not None for r in records),partial_pipe_XY_children=sum(r['complete_horizontal_run_centerline_mm']is None for r in records)),
        axis_source_graph_sha256=sha(paths['parent_graph']),native_axis_graph_sha256=sha(paths['axis_graph']),qualified_parent_manifest_sha256=sha(paths['parent_manifest']),
        proportional_length_allocation=False,local_graphs_mutated=False,component_assignments_mutated=False,physical_joint_lengths_assigned=0,net_pipe_cut_lengths_assigned=0,human_accepted=False)

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'ordered-group-plan-lengths.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'ordered-group-plan-lengths.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('ordered group bindings changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('ordered group independent native replay differs')
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
    print(result['counts'],result['pending'],flush=True)
if __name__=='__main__':main()
