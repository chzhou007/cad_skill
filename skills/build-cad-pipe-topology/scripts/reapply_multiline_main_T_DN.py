"""Rebuild and independently replay native multi-LINE main-to-T DN rules."""
import csv,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_typed_inline_attribute_DN import verify_output as verify_parent
from native_air_vent_attribute_items import collect as normalized_items
from native_multiline_main_T_DN import collect,MODE

def compute(manifest):
    ins=manifest['inputs']
    def checked():
        if any(sha(s['path'])!=s['sha256']for s in ins.values()):raise ValueError('fixed multiline source inputs changed')
    checked();parent=verify_parent(Path(ins['parent_attribute_proof']['path']).parent)
    for key in('axis_source','axis_graph','routing','canonical_components'):
        if ins[key]!=parent['inputs'][key]:raise ValueError('source ancestry differs')
    viewer=load(ins['parent_viewer_manifest']['path']);provider=load(ins['parent_provider']['path']);c=viewer['attributeValueContext']['axis_rule_vertical_DN']
    if c['all_current_vertical_domains']!=parent['counts']['current_known']or provider['counts']['all_current_vertical_DN_domains']!=parent['counts']['current_known']or c['source_bindings']['native_source']!=ins['axis_source']['sha256']or c['source_bindings']['native_graph']!=ins['axis_graph']['sha256']:raise ValueError('current published parent differs')
    doc,preflight=read_source(ins['axis_source']['path']);g=load(ins['axis_graph']['path']);route=load(ins['routing']['path'])
    with Path(ins['canonical_components']['path']).open(encoding='utf-8-sig',newline='')as f:inventory=list(csv.DictReader(f))
    items,normalization=normalized_items(doc,g,inventory);r=collect(doc,g,route,parent,items,ins['axis_source']['sha256'],ins['axis_graph']['sha256']);checked();r.update(inputs=ins,source_preflight=preflight,inherited_air_vent_normalization=normalization,viewer_adoption_pending=True);return r

def implementations():
    names=('native_multiline_main_T_DN','reapply_typed_inline_attribute_DN','native_air_vent_attribute_items','axis_continuous_source_vertical_DN','axis_unbranched_vertical_DN','crossview_equipment_branch_inventory','native_junction_ray_evidence','pipe_annotation_attributes','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('implementation changed')
    output.mkdir(parents=True);p=output/'multiline-main-T-DN.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))));return r

def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'multiline-main-T-DN.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementations()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('multiline source/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=p.read_bytes():raise ValueError('independent multiline main replay differs')
    return fresh
