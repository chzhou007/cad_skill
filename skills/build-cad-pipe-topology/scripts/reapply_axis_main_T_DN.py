"""Rebuild and independently replay complete current vertical T inheritance."""
from pathlib import Path
import argparse,csv,importlib
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_nested_direct_caption_DN import verify_output as verify_parent
from native_air_vent_attribute_items import collect as normalized_items
from native_axis_main_T_DN import collect,MODE

def compute(manifest):
    ins=manifest['inputs']
    def check():
        if any(sha(v['path'])!=v['sha256']for v in ins.values()):raise ValueError('fixed main-T DN inputs changed')
    check();parent=verify_parent(Path(ins['parent_attribute_proof']['path']).parent)
    for name in('axis_source','axis_graph','routing'):
        if ins[name]!=parent['inputs'][name]:raise ValueError('native main-T source ancestry differs')
    provider=load(ins['parent_provider']['path']);viewer=load(ins['parent_viewer_manifest']['path'])
    if provider['counts']['all_current_vertical_DN_domains']!=parent['counts']['current_known']or viewer['attributeValueContext']['nested_direct_axis_vertical_DN']['all_current_vertical_domains']!=parent['counts']['current_known']:raise ValueError('actual published vertical parent differs')
    doc,preflight=read_source(ins['axis_source']['path']);graph=load(ins['axis_graph']['path']);route=load(ins['routing']['path'])
    with Path(ins['canonical_components']['path']).open(encoding='utf-8-sig',newline='')as f:inventory=list(csv.DictReader(f))
    items,normalization=normalized_items(doc,graph,inventory);r=collect(doc,graph,route,parent,items,ins['axis_source']['sha256'],ins['axis_graph']['sha256']);check();r.update(inputs=ins,source_preflight=preflight,inherited_air_vent_normalization=normalization,published=False);return r

def implementations():
    names=('native_axis_main_T_DN','native_air_vent_attribute_items','axis_continuous_source_vertical_DN','axis_unbranched_vertical_DN','crossview_equipment_branch_inventory','native_junction_ray_evidence','pipe_annotation_attributes','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    r=compute(load(manifest));output.mkdir(parents=True);target=output/'main-T-vertical-DN.json';target.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementations(),output_sha256=sha(target))));return r

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'main-T-vertical-DN.json'
    if receipt['mode']!=MODE or sha(m['path'])!=m['sha256']or receipt['implementation_sha256']!=implementations()or sha(target)!=receipt['output_sha256']:raise ValueError('main-T source/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent main-T source replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--output');p.add_argument('--verify-output');a=p.parse_args()
    if a.verify_output:print(verify_output(a.verify_output)['counts'],flush=True)
    else:print(produce(a.manifest,a.output)['counts'],flush=True)
