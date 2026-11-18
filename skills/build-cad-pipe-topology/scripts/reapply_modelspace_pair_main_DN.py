"""Replay paired/direct source-LINE seeds and requalify all adopted main-T DN."""
import copy,csv,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_multiline_main_T_DN import verify_output as verify_parent
from native_air_vent_attribute_items import collect as normalized_items
from native_modelspace_paired_main_seeds import collect,MODE
from axis_unbranched_vertical_DN import source_key

def compute(manifest):
    ins=manifest['inputs']
    def checked():
        if any(sha(s['path'])!=s['sha256']for s in ins.values()):raise ValueError('fixed modelspace pair source inputs changed')
    checked();parent=verify_parent(Path(ins['parent_attribute_proof']['path']).parent)
    for k in('axis_source','axis_graph','routing','canonical_components'):
        if ins[k]!=parent['inputs'][k]:raise ValueError('source ancestry differs')
    viewer=load(ins['parent_viewer_manifest']['path']);provider=load(ins['parent_provider']['path']);context=viewer['attributeValueContext']['axis_rule_vertical_DN']
    if context['all_current_vertical_domains']!=parent['counts']['current_known']or provider['counts']['all_current_vertical_DN_domains']!=parent['counts']['current_known']or context['source_bindings']['native_source']!=ins['axis_source']['sha256']or context['source_bindings']['native_graph']!=ins['axis_graph']['sha256']:raise ValueError('current published parent differs')
    rules=[['original_native_main_T_and_unlabelled_branch_continuity'],['original_native_multiline_main_through_T_and_branch_continuity']];known=[r for r in context['records']if r['source_rules']in rules];knownkeys={source_key(r)for r in known};private=copy.deepcopy(parent)
    if len(knownkeys)!=len(known)or not known:raise ValueError('complete current adopted main-T inventory required')
    private['pending'] += [dict(edge_id=r['edge_id'],path_index=r['path_index'],segment_index=r['segment_index'],original_reason='no_qualified_axis_annotation_on_this_vertical_segment')for r in known];private['counts']['current_known']-=len(known)
    doc,preflight=read_source(ins['axis_source']['path']);g=load(ins['axis_graph']['path']);route=load(ins['routing']['path'])
    with Path(ins['canonical_components']['path']).open(encoding='utf-8-sig',newline='')as f:inventory=list(csv.DictReader(f))
    items,normalization=normalized_items(doc,g,inventory);r=collect(doc,g,route,private,items,ins['axis_source']['sha256'],ins['axis_graph']['sha256']);fresh={source_key(v):v for v in r['records']};requalified=[]
    for old in known:
        k=source_key(old)
        if k not in fresh or fresh[k]['nominal_mm']!=old['nominal_mm']:raise ValueError('previously adopted native main-T DN no longer independently requalifies '+str(k))
        requalified.append(dict(original_published_record=copy.deepcopy(old),fresh_native_evidence=copy.deepcopy(fresh[k])))
    r['records']=[row for row in r['records']if source_key(row)not in knownkeys];oldpending={source_key(p)for p in parent['pending']}
    if {source_key(p)for p in r['pending']}|{source_key(v)for v in r['records']}!=oldpending:raise ValueError('current unknown scopes not conserved')
    r['counts']=dict(previous_known=parent['counts']['current_known'],screened_pending=len(parent['pending']),screened_corridors=sum(p['original_reason']=='no_qualified_axis_annotation_on_this_vertical_segment'for p in parent['pending']),new_known=len(r['records']),current_known=parent['counts']['current_known']+len(r['records']),remaining_unknown=len(r['pending']))
    r.update(inputs=ins,source_preflight=preflight,inherited_air_vent_normalization=normalization,existing_main_T_requalification=dict(status='passed',count=len(requalified),records=requalified,old_values_changed=False),private_known_scope_replay_not_graph_mutation=True,viewer_adoption_pending=True);checked();return r

def implementations():
    names=('native_modelspace_paired_main_seeds','reapply_multiline_main_T_DN','native_multiline_main_T_DN','native_air_vent_attribute_items','native_paired_caption_geometry','native_paired_end_labels','axis_continuous_source_vertical_DN','axis_unbranched_vertical_DN','source_direct_dn_evidence','pipe_annotation_attributes','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('implementation changed')
    output.mkdir(parents=True);p=output/'modelspace-pair-main-DN.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))));return r

def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'modelspace-pair-main-DN.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementations()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('modelspace pair source/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=p.read_bytes():raise ValueError('independent modelspace pair replay differs')
    return fresh
