"""Reapply inherited component identity and normalized elbows to attribute inputs."""
import copy,csv,importlib,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_axis_main_T_DN import verify_output as verify_parent
from native_typed_inline_body_DN import collect as typed_direct,qualify_templates,historical_types
from inherited_attribute_elbow_items import collect as elbow_items
import reapply_nested_direct_caption_DN as original

MODE='inherited_typed_component_and_normalized_elbow_axis_DN_v1'

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))

def compute(manifest):
    ins=manifest['inputs']
    def checked():
        if any(sha(s['path'])!=s['sha256']for s in ins.values()):raise ValueError('typed attribute source, parent or historical capability changed')
    checked();parent=verify_parent(Path(ins['parent_attribute_proof']['path']).parent)
    for key in('axis_source','axis_graph','routing','canonical_components'):
        if ins[key]!=parent['inputs'][key]:raise ValueError('current source ancestry differs')
    viewer=load(ins['parent_viewer_manifest']['path']);provider=load(ins['parent_provider']['path']);context=viewer['attributeValueContext']['axis_rule_vertical_DN']
    if context['all_current_vertical_domains']!=parent['counts']['current_known']or provider['counts']['all_current_vertical_DN_domains']!=parent['counts']['current_known']:raise ValueError('actual published vertical parent differs')
    if context['source_bindings']['native_graph']!=ins['axis_graph']['sha256']or context['source_bindings']['native_source']!=ins['axis_source']['sha256']:raise ValueError('current axis graph/source binding differs')
    doc,preflight=read_source(ins['axis_source']['path']);baseline,bpre=read_source(ins['baseline_source']['path']);graph=load(ins['axis_graph']['path']);route=load(ins['routing']['path']);inventory=csvrows(ins['canonical_components']['path']);types_map=historical_types(Path(ins['legacy_component_reader']['path']).read_text(encoding='utf8'));catalogue=csvrows(ins['legacy_catalogue']['path']);templates=qualify_templates(doc,baseline,catalogue,types_map,manifest['template_selections'])
    old_direct=load(parent['inputs']['parent_attribute_proof']['path']);handles=[r['text_handle']for r in old_direct['direct_qualification']['held']];proxy=copy.deepcopy(parent);proxy['pair_qualification']=dict(unmatched_target_text_handles=handles);normalization={}
    def direct(*args):return typed_direct(*args,inventory,templates)
    def items(d,g):
        values,proof=elbow_items(d,g,load(ins['historical_normalization']['path']));normalization.update(proof);return values
    namespace=dict(original.compose.__globals__,direct_reader=direct,native_items=items);compose=types.FunctionType(original.compose.__code__,namespace,original.compose.__name__,original.compose.__defaults__,original.compose.__closure__);result=compose(doc,graph,route,proxy,ins['axis_source']['sha256'],ins['axis_graph']['sha256']);checked()
    if encode(parent)!=Path(ins['parent_attribute_proof']['path']).read_bytes():raise ValueError('original source parent changed')
    result.update(mode=MODE,inputs=ins,source_preflight=preflight,historical_source_preflight=bpre,template_selections=manifest['template_selections'],historical_component_type_and_geometry_replayed=True,private_elbow_attribute_items=normalization,original_topology_normalization_replayed=True,physical_ports_inferred=False,source_documents_mutated=False,viewer_adoption_pending=True)
    return result

def implementations():
    names=('native_typed_inline_body_DN','inherited_attribute_elbow_items','reapply_nested_direct_caption_DN','reapply_axis_main_T_DN','native_nested_direct_caption_DN','topology_normalization','axis_unbranched_vertical_DN','native_inline_anchors','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('typed attribute implementation changed')
    output.mkdir(parents=True);p=output/'typed-inline-axis-DN.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))));return r

def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'typed-inline-axis-DN.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementations()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('typed attribute inputs/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=p.read_bytes():raise ValueError('independent typed attribute replay differs')
    return fresh
