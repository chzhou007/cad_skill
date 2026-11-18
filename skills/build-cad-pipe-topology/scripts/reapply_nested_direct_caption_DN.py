"""Compose current nested direct annotation owners with original source paths."""
import argparse,copy,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reapply_nested_paired_caption_DN import verify_output as verify_parent
from native_nested_direct_caption_DN import collect as direct_reader
from axis_unbranched_vertical_DN import source_key,native_items,annotation_index,chain_evidence
from axis_omission_vertical_DN import omission_corridor,owned_annotation_guard

MODE='native_nested_direct_caption_DN_composition_v1'

def compose(doc,graph,route,parent,source_hash,graph_hash):
    before=encode(graph),encode(route),encode(parent);handles=parent['pair_qualification']['unmatched_target_text_handles']
    direct=direct_reader(doc,graph,route,handles,source_hash,graph_hash);pending={source_key(p):p for p in parent['pending']};scopes={source_key(s):s for s in route['records']};edges={e['edge_id']:e for e in graph['edges']};records=[]
    if len(pending)!=len(parent['pending']):raise ValueError('duplicate prior unresolved domains')
    for r in direct['records']:
        key=source_key(r)
        if key not in pending or pending[key]['original_reason']!='repeated native DN layout does not identify one source branch':raise ValueError('direct owner would overwrite a different prior source scope')
        records.append(dict(copy.deepcopy(r),connection_rule='original_direct_reader_complete_nested_WCS_projection'))
    keys={source_key(r)for r in records};items=native_items(doc,graph);index=annotation_index(doc,graph,source_hash);replayed={o['source_text']['handle']:o['native_evidence']for r in direct['records']for o in r['observations']};held=[]
    for key,p in pending.items():
        if key in keys or p.get('original_reason')!='no_qualified_axis_annotation_on_this_vertical_segment':continue
        seeds=[r for r in direct['records']if r['edge_id']==key[0]]
        if not seeds:continue
        try:
            if len({s['nominal_mm']for s in seeds})!=1:raise ValueError('competing source DN requires transition extent')
            target=scopes[key];edge=edges[key[0]]
            if target['direction_class']!='vertical':raise ValueError('target must remain original vertical domain')
            same=[s for s in seeds if s['path_index']==key[1]]
            if same:
                seed=min(same,key=lambda s:(abs(s['segment_index']-key[2]),s['segment_index']));lo,hi=sorted((seed['segment_index'],key[2]));corridor=[scopes[key[0],key[1],i]for i in range(lo,hi+1)];continuity=chain_evidence(corridor,edge.get('source_insert_handle'),items);rule='original_nested_direct_DN_and_two_arm_bends'
            else:
                seed=sorted(seeds,key=source_key)[0];continuity=omission_corridor(doc,graph,edge,target,seed,scopes,items,source_hash);corridor=[s for c in continuity['corridors']for s in c['scopes']];rule='original_nested_direct_DN_and_omission_pair'
            guard=owned_annotation_guard(doc,seeds,corridor,index,source_hash,edge,edges,replayed)
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],scope_points=copy.deepcopy(target['scope_points']),system=target['system'],floor_start=target['floor_start'],floor_end=target['floor_end'],nominal_mm=seed['nominal_mm'],seed_record=copy.deepcopy(seed),continuity_evidence=continuity,annotation_guard=guard,connection_rule=rule,source='axis11_original_direct_annotation_and_source_continuity',whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
        except ValueError as exc:held.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],reason=str(exc)))
    added={source_key(r)for r in records}
    if len(added)!=len(records)or not added<=pending.keys():raise ValueError('new direct/continuity domains duplicate or leave current pending scope')
    if before!=(encode(graph),encode(route),encode(parent)):raise ValueError('original source graph or parent mutated')
    return dict(mode=MODE,records=records,pending=[copy.deepcopy(p)for p in parent['pending']if source_key(p)not in added],direct_qualification=direct,continuity_held=held,counts=dict(previous_known=parent['counts']['current_known'],screened_pending=len(pending),new_direct=len(direct['records']),new_continuity=len(records)-len(direct['records']),new_known=len(records),current_known=parent['counts']['current_known']+len(records),remaining_unknown=len(pending)-len(records)),complete_current_pending_population_screened=True,original_direct_and_continuity_kernels_unchanged=True,repeated_layout_threshold_changed=False,graph_mutated=False,components_reassigned=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def check():
        if any(sha(v['path'])!=v['sha256']for v in inputs.values()):raise ValueError('fixed direct-caption inputs changed')
    check();parent=verify_parent(Path(inputs['parent_attribute_proof']['path']).parent)
    for name in('axis_source','axis_graph','routing'):
        if inputs[name]!=parent['inputs'][name]:raise ValueError('native parent source ancestry differs')
    provider=load(inputs['parent_provider']['path']);viewer=load(inputs['parent_viewer_manifest']['path'])
    if parent['counts']['current_known']!=provider['counts']['all_current_vertical_DN_domains']:raise ValueError('actual published vertical parent differs')
    current=viewer.get('attributeValueContext',{}).get('nested_pair_axis_vertical_DN',{})
    if current.get('all_current_vertical_domains')!=parent['counts']['current_known']:raise ValueError('actual viewer vertical context differs')
    doc,preflight=read_source(inputs['axis_source']['path']);result=compose(doc,load(inputs['axis_graph']['path']),load(inputs['routing']['path']),parent,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256']);check();result.update(inputs=inputs,source_preflight=preflight,published=False);return result

def implementations():
    names=('native_nested_direct_caption_DN','reapply_nested_paired_caption_DN','native_segment_dn_candidates_v2','native_segment_dn_candidates','native_repeated_branch_DN_layout','native_paired_caption_geometry','axis_local_DN_segment_domains','axis_unbranched_vertical_DN','axis_omission_vertical_DN','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'nested-direct-vertical-DN.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementations(),output_sha256=sha(target))));return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'nested-direct-vertical-DN.json'
    if receipt['mode']!=MODE or sha(m['path'])!=m['sha256']or receipt['implementation_sha256']!=implementations()or sha(target)!=receipt['output_sha256']:raise ValueError('nested direct source/code/output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent nested direct native replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--output');p.add_argument('--verify-output');a=p.parse_args()
    if a.verify_output:print(verify_output(a.verify_output)['counts'],flush=True)
    else:print(produce(a.manifest,a.output)['counts'],flush=True)
