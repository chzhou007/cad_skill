"""Compose inherited native pair geometry and omission continuity in one batch."""
import argparse,copy,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_air_vent_attribute_normalization import verify_output as verify_parent
from native_nested_paired_caption_DN import collect as paired_reader
from axis_unbranched_vertical_DN import native_items,annotation_index,source_key
from axis_omission_vertical_DN import omission_corridor,owned_annotation_guard

MODE='native_nested_paired_caption_DN_composition_v1'

def compose(doc,graph,route,parent,annotations,source_hash,graph_hash):
    before=encode(graph),encode(route),encode(parent),encode(annotations)
    handles=sorted({h for b in annotations['repeated_native_qualification'] for p in b['pieces'] if p['status']=='pending' for h in p['handles']})
    paired=paired_reader(doc,graph,route,handles,source_hash,graph_hash)
    pending={source_key(p):p for p in parent['pending']};scopes={source_key(s):s for s in route['records']};edges={e['edge_id']:e for e in graph['edges']}
    records=[]
    for r in paired['records']:
        k=source_key(r)
        if k not in pending or pending[k]['original_reason']!='repeated native DN layout does not identify one source branch':
            raise ValueError('new paired geometry would overwrite a different prior scope')
        records.append(dict(copy.deepcopy(r),connection_rule='original_nested_straddling_pair_geometry'))
    direct_keys={source_key(r) for r in records};items=native_items(doc,graph);index=annotation_index(doc,graph,source_hash)
    replayed={o['source_text']['handle']:o['native_evidence'] for r in paired['records'] for o in r['observations']}
    held=[]
    for k,p in pending.items():
        if k in direct_keys or p.get('original_reason')!='no_qualified_axis_annotation_on_this_vertical_segment':continue
        seeds=[s for s in paired['records'] if s['edge_id']==k[0] and s['path_index']!=k[1]]
        if not seeds:continue
        try:
            if len({s['nominal_mm'] for s in seeds})!=1:raise ValueError('competing source values need a transition extent')
            if scopes[k]['direction_class']!='vertical':raise ValueError('omission target not vertical')
            seed=sorted(seeds,key=source_key)[0];edge=edges[k[0]]
            continuity=omission_corridor(doc,graph,edge,scopes[k],seed,scopes,items,source_hash)
            corridor=[s for c in continuity['corridors'] for s in c['scopes']]
            guard=owned_annotation_guard(doc,seeds,corridor,index,source_hash,edge,edges,replayed)
            scope=scopes[k]
            records.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],scope_points=copy.deepcopy(scope['scope_points']),system=scope['system'],
                floor_start=scope['floor_start'],floor_end=scope['floor_end'],nominal_mm=seed['nominal_mm'],seed_record=copy.deepcopy(seed),
                continuity_evidence=continuity,annotation_guard=guard,connection_rule='original_nested_pair_and_omission_continuity',
                source='axis11_original_paired_caption_and_native_omission',whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
        except ValueError as exc:held.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],reason=str(exc)))
    new={source_key(r) for r in records}
    if len(new)!=len(records) or not new<=pending.keys():raise ValueError('duplicate or out-of-parent target domains')
    remaining=[copy.deepcopy(p) for p in parent['pending'] if source_key(p) not in new]
    if before!=(encode(graph),encode(route),encode(parent),encode(annotations)):raise ValueError('native input changed')
    return dict(mode=MODE,records=records,pending=remaining,pair_qualification=paired,omission_held=held,
        counts=dict(previous_known=parent['counts']['current_known'],screened_pending=len(pending),new_direct=len(direct_keys),new_omission=len(records)-len(direct_keys),
            new_known=len(records),current_known=parent['counts']['current_known']+len(records),remaining_unknown=len(remaining)),
        complete_current_pending_population_screened=True,original_pair_and_omission_kernels_unchanged=True,layout_control_threshold_changed=False,
        graph_mutated=False,components_reassigned=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def check():
        if any(sha(v['path'])!=v['sha256'] for v in inputs.values()):raise ValueError('fixed source or parent changed')
    check();parent=verify_parent(Path(inputs['parent_attribute_proof']['path']).parent)
    provider=load(inputs['parent_provider']['path']);viewer=load(inputs['parent_viewer_manifest']['path'])
    if (parent['counts']['current_known']!=provider['counts']['all_current_vertical_DN_domains']
        or parent['counts']['current_known']!=viewer['attributeValueContext']['continuous_axis_vertical_DN']['all_current_vertical_domains']):
        raise ValueError('actual published vertical parent differs')
    for name in ('axis_source','axis_graph','routing'):
        if inputs[name]!=parent['inputs'][name]:raise ValueError('native parent ancestry differs')
    annotations=load(inputs['annotation_baseline']['path']);sh=inputs['axis_source']['sha256'];gh=inputs['axis_graph']['sha256']
    if annotations['source_sha256']!=sh or annotations['graph_sha256']!=gh:raise ValueError('annotation source/graph differs')
    doc,preflight=read_source(inputs['axis_source']['path']);graph=load(inputs['axis_graph']['path']);route=load(inputs['routing']['path'])
    result=compose(doc,graph,route,parent,annotations,sh,gh);check()
    result.update(inputs=inputs,source_preflight=preflight,published=False);return result

def implementations():
    names=('native_nested_paired_caption_DN','reapply_air_vent_attribute_normalization','native_paired_caption_geometry','native_repeated_branch_DN_layout',
        'axis_local_DN_segment_domains','axis_omission_vertical_DN','axis_unbranched_vertical_DN','pipe_annotation_attributes','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__) for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'nested-paired-vertical-DN.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementations(),output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'nested-paired-vertical-DN.json'
    if (receipt['mode']!=MODE or sha(m['path'])!=m['sha256'] or receipt['implementation_sha256']!=implementations() or sha(target)!=receipt['output_sha256']):raise ValueError('nested paired source/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent native nested pair replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(produce(a.manifest,a.output)['counts'],flush=True)
