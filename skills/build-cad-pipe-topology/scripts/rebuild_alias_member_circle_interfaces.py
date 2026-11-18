"""Native owner for member interfaces expressed through confirmed view aliases."""
import argparse,csv,importlib,sys
from pathlib import Path
pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(pipeline)not in sys.path:sys.path.insert(0,str(pipeline))
from confirm_crossview_paths import load,sha,encode
from checked_bounded_attribute_parent import apply as apply_parent
from source_readability import read_source
from confirmed_compound_pipe_lanes import verify_output as verify_lanes
from confirmed_member_plan_paths import collect as member_paths
from native_plan_projection_lengths import unit_evidence
from alias_member_circle_interfaces import collect,MODE

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('alias interface input changed')
    checked();parent,qualification=apply_parent(manifest['parent_application'],Path(__file__).resolve().parents[2])
    for k in('provider_inventory','viewer_manifest','plan_graph','axis_graph','plan_source','axis_source'):
        if parent['inputs'][k]['sha256']!=sha(paths[k]):raise ValueError('original complete parent source scope differs: '+k)
    inventory=load(paths['provider_inventory']);owner=load(paths['member_proof'])
    if inventory['inputs']['owner_extension']['sha256']!=sha(paths['member_proof']):raise ValueError('member owner outside qualified parent ancestry')
    for k in('plan_graph','axis_graph','plan_source','axis_source'):
        if owner['inputs'][k]['sha256']!=sha(paths[k]):raise ValueError('confirmed member owner source differs')
    pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source']);plan=load(paths['plan_graph']);axis=load(paths['axis_graph'])
    units=unit_evidence(pd,load(paths['unit_policy']));lanes=verify_lanes(paths['lanes'].parent)
    if lanes['source_sha256']!=sha(paths['plan_source']):raise ValueError('confirmed lane source differs')
    with paths['components'].open(encoding='utf-8-sig',newline='')as f:components=list(csv.DictReader(f))
    members=member_paths(pd,plan,components,lanes,load(paths['member_policy']),units,sha(paths['plan_source']),sha(paths['plan_graph']))
    if encode(members)!=encode(owner['member_plan_paths']):raise ValueError('fresh native confirmed alias/member cohort differs')
    if any(row['floor']!=manifest['floor']for row in members['records']):raise ValueError('member cohort floor differs')
    context=load(paths['viewer_manifest'])['attributeValueContext'];policy=load(paths['orientation_policy'])
    result=collect(pd,ad,plan,axis,members,context,inventory['ordinary_junction_mappings'][str(manifest['floor'])],units,policy,{k:sha(paths[k])for k in('plan_source','axis_source','plan_graph','axis_graph')})
    checked();result.update(inputs=manifest['inputs'],floor=manifest['floor'],source_preflight=dict(plan=pp,axis=ap),unit_evidence=units,parent_qualification=qualification,confirmed_alias_member_cohort_native_replayed=True)
    return result

def implementation_hashes():
    names=('alias_member_circle_interfaces','checked_bounded_attribute_parent','confirmed_member_plan_paths','confirmed_compound_pipe_lanes','compound_member_interfaces','native_paired_caption_geometry','compound_pipe_label_evidence','batch_native_path_coverage','axis_attribute_source_routing','source_readability','native_plan_projection_lengths')
    return dict({name:sha(importlib.import_module(name).__file__)for name in names},entry=sha(__file__))

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True)
    target=output/'alias-member-interfaces.json';target.write_bytes(encode(result));graph=output/'member_graph.json';graph.write_bytes(encode(result['member_local_graph']))
    import checked_bounded_attribute_parent as parent
    (output/'parent-execution.json').write_bytes(encode(parent.LAST_APPLICATION))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),member_graph_sha256=sha(graph),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'alias-member-interfaces.json';graph=output/'member_graph.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']or sha(graph)!=receipt['member_graph_sha256']:raise ValueError('alias interface implementation or artifact changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes()or encode(fresh['member_local_graph'])!=graph.read_bytes():raise ValueError('independent alias member interface reconstruction differs')
    return fresh

def main():
    p=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            result=produce(a.manifest,a.output)
    import checked_bounded_attribute_parent as parent
    print(dict(counts=result['counts'],parent_native_replay=parent.LAST_APPLICATION.get('native_replay_performed'),parent_current_dependency_reuse=parent.LAST_APPLICATION.get('dependency_checked_reuse'),human_accepted=False),flush=True)
if __name__=='__main__':main()
