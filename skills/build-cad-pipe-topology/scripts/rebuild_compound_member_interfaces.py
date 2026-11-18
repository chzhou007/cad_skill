"""Apply the qualified parent, then independently rebuild compound interfaces."""
import argparse,importlib,sys
from pathlib import Path
_orchestration=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_orchestration) not in sys.path:sys.path.insert(0,str(_orchestration))
from confirm_crossview_paths import load,sha,encode
from checked_native_parent_application import apply as apply_parent
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
from compound_member_interfaces import collect,MODE

def compute(manifest):
    paths={k:Path(v['path']) for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256'] for k,v in manifest['inputs'].items()):raise ValueError('member interface input changed')
    checked();parent,qualification=apply_parent(manifest['parent_application'],Path(__file__).resolve().parents[2])
    if encode(parent)!=paths['member_proof'].read_bytes():raise ValueError('complete checked member parent differs')
    for name in ('plan_source','axis_source','plan_graph','axis_graph'):
        if parent['source_hashes'][name]!=sha(paths[name]):raise ValueError('member parent belongs to another source or graph')
    pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source']);plan=load(paths['plan_graph']);axis=load(paths['axis_graph'])
    units=unit_evidence(pd,load(paths['unit_policy']));angles=load(paths['axis_orientation_policy'])['isometric_horizontal_directions_degrees']
    result=collect(pd,ad,plan,axis,parent,units,angles,{k:sha(paths[k]) for k in ('plan_source','axis_source','plan_graph','axis_graph')})
    checked();result.update(source_preflight=dict(plan=pp,iso=ap),unit_evidence=units,parent_qualification=qualification,source_hashes={k:sha(p) for k,p in paths.items()},
        source_comparison_status='scoped_native_two_view_member_geometry_checked_external_routes_and_component_member_allocation_pending')
    return result

def implementation_hashes():
    names=('compound_member_interfaces','native_paired_caption_geometry','native_paired_end_labels','compound_carrier_members','native_main_endpoint_extent',
        'native_plan_projection_lengths','batch_native_path_coverage','crossview_equipment_branch_inventory','source_readability','checked_native_parent_application')
    return dict({n:sha(importlib.import_module(n).__file__) for n in names},entry=sha(__file__))
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);(output/'member-interfaces.json').write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),
        output_sha256=sha(output/'member-interfaces.json'),human_accepted=False)))
    return result
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];proof=output/'member-interfaces.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes() or sha(m['path'])!=m['sha256'] or sha(proof)!=receipt['output_sha256']:raise ValueError('member interface implementation or artifact changed')
    result=compute(load(m['path']))
    if encode(result)!=proof.read_bytes():raise ValueError('independent native member interface reconstruction differs')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification uses original inputs')
            result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
