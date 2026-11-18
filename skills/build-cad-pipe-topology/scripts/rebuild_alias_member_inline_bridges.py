"""Independently replay the alias parent and reapply its entire external-port cohort."""
import argparse,csv,importlib,sys
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
from rebuild_alias_member_circle_interfaces import verify_output as verify_parent
from alias_member_inline_bridges import collect,MODE

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('alias bridge input changed')
    checked();parent=verify_parent(paths['member_interfaces'].parent)
    if encode(parent)!=paths['member_interfaces'].read_bytes():raise ValueError('alias interface native replay differs')
    for key in('plan_source','axis_source','plan_graph','axis_graph','unit_policy','orientation_policy','components'):
        if parent['inputs'][key]['sha256']!=sha(paths[key]):raise ValueError('alias bridge parent source differs: '+key)
    if sha(paths['plan_inventory'])!=sha(paths['components']):raise ValueError('plan component ownership outside original parent')
    pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source'])
    def rows(path):
        with path.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
    units=unit_evidence(pd,load(paths['unit_policy']))
    result=collect(pd,ad,load(paths['plan_graph']),load(paths['axis_graph']),parent,rows(paths['plan_inventory']),rows(paths['axis_inventory']),
        load(paths['template_origin']),{k:sha(p)for k,p in paths.items()},units,load(paths['orientation_policy'])['isometric_horizontal_directions_degrees'])
    checked();result.update(inputs=manifest['inputs'],source_preflight=dict(plan=pp,axis=ap),unit_evidence=units,
        parent_alias_interfaces_independently_replayed=True,human_accepted=False)
    return result

def implementation_hashes():
    names=('alias_member_inline_bridges','rebuild_alias_member_circle_interfaces','alias_member_circle_interfaces','compound_member_bridges',
        'native_inline_joint_path_coverage','native_inline_anchors','repair_native_flexible_joints','batch_native_path_coverage',
        'native_plan_projection_lengths','native_main_endpoint_extent','source_readability','native_dn_text_position')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True)
    proof=output/'alias-member-bridges.json';proof.write_bytes(encode(result))
    graph=output/'member_graph.json';graph.write_bytes(encode(result['member_local_graph']))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(proof),member_graph_sha256=sha(graph),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];proof=output/'alias-member-bridges.json';graph=output/'member_graph.json'
    if(receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']
        or sha(proof)!=receipt['output_sha256']or sha(graph)!=receipt['member_graph_sha256']):raise ValueError('alias bridge receipt, implementation or source changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=proof.read_bytes()or encode(fresh['member_local_graph'])!=graph.read_bytes():raise ValueError('independent native alias bridges differ')
    return fresh

def main():
    parser=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output:r=verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
            r=produce(args.manifest,args.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
