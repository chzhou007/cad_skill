"""Replay qualified interface parents, then rebuild all eligible inline bridges."""
import argparse,csv,importlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from rebuild_compound_member_interfaces import verify_output as verify_interfaces
from compound_member_bridges import collect,MODE
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('member bridge input changed')
    checked();parent=verify_interfaces(paths['member_interfaces'].parent)
    if encode(parent)!=paths['member_interfaces'].read_bytes():raise ValueError('member interface parent changed')
    for key in('plan_source','axis_source','plan_graph','axis_graph','raw_axis_graph'):
        if parent['source_hashes'][key]!=sha(paths[key]):raise ValueError('bridge parent belongs to different source '+key)
    pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source'])
    def rows(p):
        with p.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
    hashes={k:sha(p)for k,p in paths.items()};units=unit_evidence(pd,load(paths['unit_policy']))
    result=collect(pd,ad,load(paths['plan_graph']),load(paths['axis_graph']),parent,rows(paths['plan_inventory']),rows(paths['axis_inventory']),load(paths['template_origin']),hashes,units,load(paths['axis_orientation_policy'])['isometric_horizontal_directions_degrees'])
    checked();result.update(source_preflight=dict(plan=pp,axis=ap),unit_evidence=units,parent_interface_qualification='independent_current_native_replay_with_checked_immutable_ancestor_reuse')
    return result
def implementation_hashes():
    names=('compound_member_bridges','rebuild_compound_member_interfaces','compound_member_interfaces','native_inline_joint_path_coverage','native_inline_anchors','repair_native_flexible_joints','native_proxy_evidence','native_plan_projection_lengths','native_line_path_evidence','source_readability','native_paired_caption_geometry','native_main_endpoint_extent','checked_native_parent_application','batch_native_path_coverage','crossview_equipment_branch_inventory','attach_anchored_floor_main_attributes','native_dn_text_position')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);(output/'member-bridges.json').write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(output/'member-bridges.json'),human_accepted=False)))
    return result
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest']
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(output/'member-bridges.json')!=receipt['output_sha256']:raise ValueError('bridge implementation or artifact changed')
    result=compute(load(m['path']))
    if encode(result)!=(output/'member-bridges.json').read_bytes():raise ValueError('independent native bridge reconstruction differs')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
