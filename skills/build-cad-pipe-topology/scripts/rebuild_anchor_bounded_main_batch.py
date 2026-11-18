"""Replay complete current native parents, then expand bounded main regions."""
import argparse,copy,csv,importlib,sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from extend_native_main_chain_batch import verify_output as verify_parent
from ordered_group_plan_lengths import verify_output as verify_ordered
from rebuild_full_plan_DN import PARENTS
from native_replay_session import verify_once
from anchor_bounded_main_paths import apply
from native_current_junction_reader import make_reader
from native_plan_projection_lengths import unit_evidence,lengths
from native_main_interval_metrics import measure
MODE='native_anchor_bounded_main_batch_v1'

def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as stream:return list(csv.DictReader(stream))

def compute(manifest,announce=lambda message:None):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('bounded main source input changed')
    checked();announce('Replaying complete native batch and source ancestry')
    parent=verify_once(paths['batch_result'].parent,verify_parent)
    if encode(parent)!=paths['batch_result'].read_bytes():raise ValueError('complete source parent differs')
    axis=load(paths['axis_graph'])
    if parent['identity_graph_sha256']!=sha(paths['axis_graph']):raise ValueError('axis parent identity differs')
    ordered=verify_once(paths['ordered_proof'].parent,verify_ordered)
    if ordered['native_axis_graph_sha256']!=sha(paths['axis_graph']):raise ValueError('ordered anchor identity differs')
    parents=copy.deepcopy(parent['floors'])
    for group in ordered['groups']:
        floor=str(group['floor']);mapping=parents[floor]['junction_mapping']
        for pair in group['internal_main_junction_correspondence']:
            p,a=pair['plan_node'],pair['axis_node']
            if p in mapping and mapping[p]!=a:raise ValueError('retained ordered anchor conflicts')
            if a in mapping.values()and mapping.get(p)!=a:raise ValueError('retained ordered anchor collapses')
            mapping[p]=a
    ad,ap=read_source(paths['axis_source']);components_axis=csv_rows(paths['axis_components']);floors={};preflight=dict(iso=ap);new_records=[]
    for floor in sorted(parents):
        plan_path=paths['plan_graph_'+floor];plan=load(plan_path);kind=manifest['plan_parent_modes'][floor]
        if kind not in PARENTS:raise ValueError('unknown local source owner')
        local=verify_once(plan_path.parent,importlib.import_module(PARENTS[kind]).verify_output)
        if local['output_graph_sha256']!=sha(plan_path):raise ValueError('current plan owner differs')
        doc,preflight[floor]=read_source(paths['plan_source_'+floor]);units=unit_evidence(doc,load(paths['unit_policy_'+floor]));components=csv_rows(paths['components_'+floor])
        hashes=dict(plan=dict(source_sha256=sha(paths['plan_source_'+floor]),graph_sha256=sha(plan_path)),iso=dict(source_sha256=sha(paths['axis_source']),graph_sha256=sha(paths['axis_graph'])))
        reader=make_reader(load(paths['current_T_source_config']),hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
        result=apply(dict(plan=doc,iso=ad),dict(plan=plan,iso=axis),parents[floor],int(floor),dict(plan=components,iso=components_axis),hashes,manifest['isometric_horizontal_directions_degrees'],dict(plan=reader))
        metrics=[]
        for row in result['records']:
            group=next(g for g in result['groups']if g['mapping_id']in row['source_group_ids'])
            metric=measure(doc,plan,components,group['native']['plan']['path_coverage'],row,units,dict(hashes['plan'],inventory_sha256=sha(paths['components_'+floor])),load(paths['inline_origin']))
            metrics.append(metric)
        result['metrics']=metrics;result['source_hashes']=hashes;floors[floor]=result;new_records.extend(result['records'])
        announce(f'{floor}F: {len(result["records"])} unique native intervals; {len(result["new_junction_mapping"])} new Ts; {len(result["pending"])} unresolved route scopes')
    if len({e for r in new_records for e in r['iso_edges']})!=len(new_records):raise ValueError('cross-floor new axis writers overlap')
    checked()
    return dict(mode=MODE,floors=floors,source_preflight=preflight,source_hashes={k:sha(p)for k,p in paths.items()},
        counts=dict(floors=len(floors),new_axis_edges=len(new_records),new_junctions=sum(len(f['new_junction_mapping'])for f in floors.values()),source_checked_path_observations=sum(len(f['groups'])for f in floors.values()),unresolved_route_scopes=sum(len(f['pending'])for f in floors.values())),
        original_batch_preserved=True,local_topology_changed=False,axis_graph_changed=False,component_assignments_changed=False,DN_used_for_mapping=False,
        attribute_fusion_performed=False,net_pipe_cut_lengths_assigned=0,physical_installed_lengths_assigned=0,human_accepted=False)

def implementation_hashes():
    names=('anchor_bounded_main_paths','native_current_junction_reader','current_circle_plan_DN','user_circle_endpoint_plan_DN','confirmed_overlap_plan_DN','main_continuity_plan_DN','native_local_detail_T_evidence','native_projected_circle_main_role','native_user_circle_endpoint_rays','native_confirmed_overlap_rays','current_circle_main_lineage','source_reviewed_circle_branch_evidence','extend_native_main_chain_batch','ordered_group_plan_lengths','crossview_equipment_branch_inventory','batch_native_path_coverage','match_source_checked_crossview_paths','source_readability','native_plan_projection_lengths','attach_anchored_floor_main_attributes')
    names=names+('native_inherited_duplicate_circle_evidence','rebuild_wave_cohort_crossview_batch','native_main_interval_metrics','inherited_batch_plan_metrics','inherited_circle_branch_inventory','native_inline_joint_path_coverage')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest_path),lambda m:print(m,flush=True))
    if before!=implementation_hashes():raise RuntimeError('native bounded main implementation changed')
    output.mkdir(parents=True);target=output/'anchor-bounded-main-results.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=before,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'anchor-bounded-main-results.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('bounded main receipt or code changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('native bounded main replay differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification uses original bound inputs')
            result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
