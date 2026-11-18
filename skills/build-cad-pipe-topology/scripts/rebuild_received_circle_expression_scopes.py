"""Reapply original bounded routes after an exact received circle connection."""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
import normalized_reviewed_expression_scope as original
import received_projected_circle_authority as received

MODE='received_circle_and_normalized_reviewed_expression_scope_v1'


def apply_received(previous,doc,graph,source_spec,graph_spec,authorities):
    result=copy.deepcopy(previous)
    used=set()
    for scope in result['records']:
        view=scope['views']['plan'];prior=copy.deepcopy(view['junction_failures'])
        for nid in view['route']['nodes']:
            if nid not in authorities:continue
            if view['junction_failures'].get(nid)!=received.OLD_HOLD:
                raise ValueError('received circle target is not the original explicit-extent hold')
            view['junctions'][nid]=received.collect(doc,graph,nid,source_spec['sha256'],graph_spec['sha256'],authorities)
            del view['junction_failures'][nid];used.add(nid)
        scope.update(original.original.qualify(scope['views'],scope['answer']))
        scope['prior_plan_junction_failures_before_received_reply']=prior
    if used!=set(authorities):raise ValueError('received authority escaped the original bounded route')
    result.update(mode=MODE,previous_mode=original.MODE,
        explicit_received_circle_nodes=sorted(used),old_axis_normalization_preserved=True,
        accepted_scope_count=sum(r['status']=='native_bounded_range_correspondence'for r in result['records']),
        held_scope_count=sum(r['status']=='held_local_source_evidence'for r in result['records']))
    return result


def compute(manifest):
    inputs=manifest['inputs']
    for spec in inputs.values():received.checked(spec)
    previous_manifest=load(inputs['original_manifest']['path']);previous=original.compute(previous_manifest);i=previous_manifest['inputs']
    graph=load(i['plan_graph']['path']);doc,_=read_source(i['plan_source']['path'])
    config=load(inputs['received_authority_manifest']['path'])
    authorities=received.prepare(config,i['plan_source'],i['plan_graph'],graph)
    result=apply_received(previous,doc,graph,i['plan_source'],i['plan_graph'],authorities)
    result['received_authority_inputs']=copy.deepcopy(inputs)
    for spec in inputs.values():received.checked(spec)
    return result


def implementations():return dict(entry=sha(__file__),previous_scope=original.implementations(),received_authority=received.implementations())


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();result=compute(load(manifest))
    if implementations()!=code:raise ValueError('received circle scope implementation changed')
    output.mkdir(parents=True);target=output/'reviewed-expression-scopes.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(target))))
    return result


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');target=output/'reviewed-expression-scopes.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementations()or sha(target)!=r['output_sha256']:
        raise ValueError('received circle scope receipt changed')
    received.checked(r['manifest']);fresh=compute(load(r['manifest']['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('received circle scope native replay differs')
    return fresh


def main():
    p=argparse.ArgumentParser()
    for k in('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(encode(dict(mode=MODE,accepted_scopes=r['accepted_scope_count'],held_scopes=r['held_scope_count'],
        received_circles=r['explicit_received_circle_nodes'],DN_values_assigned=0,length_values_assigned=0)).decode(),flush=True)


if __name__=='__main__':main()
