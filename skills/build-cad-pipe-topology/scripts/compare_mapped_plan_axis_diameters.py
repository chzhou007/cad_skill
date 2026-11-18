"""Compare current mapped plan scopes with independently owned axis DN labels.

Different local values flag an extent question; equal values alone do not
establish equal extents. No graph, physical value or expert answer is changed.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_line_path_evidence import LAYERS
from native_repeated_branch_DN_layout import collect
from wave_rebased_plan_attributes import MODE as ATTRIBUTE_MODE,verify_output as verify_attributes
from match_wave_rebased_circle_paths import BATCH_SCHEMA
from match_source_checked_crossview_paths import selected_snapshot

MODE='mapped_plan_axis_native_DN_extent_comparison_v1'


def compare(mapping,attributes,axis,ownership):
    if (mapping.get('mode')!=BATCH_SCHEMA or attributes.get('mode')!=ATTRIBUTE_MODE
        or attributes.get('graph_sha256')!=mapping.get('plan_graph_sha256')
        or attributes.get('iso_graph_sha256')!=mapping.get('iso_graph_sha256')
        or attributes.get('source_sha256')!=mapping.get('source_sha256',{}).get('plan')
        or attributes.get('physical_values_fused') is not False or attributes.get('human_accepted') is not False):
        raise ValueError('current independently checked mapped plan attribute scopes required')
    if (ownership.get('status')!='native_repeated_instance_layout_binds_selected_DN_to_other_branches'
        or ownership.get('source_sha256')!=mapping['source_sha256']['iso'] or ownership.get('graph_sha256')!=mapping['iso_graph_sha256']
        or axis.get('metadata',{}).get('source_sha256')!=ownership['source_sha256']
        or any(ownership.get(k) is not False for k in ('target_texts_used_as_controls','graph_mutated','physical_values_fused','human_accepted'))):
        raise ValueError('independent current axis annotation ownership required')
    mapped=mapping['records'];values={r['mapping_id']:r for r in attributes['records']};edges={e['edge_id']:e for e in axis['edges']}
    if len(values)!=len(attributes['records']) or len({r['mapping_id'] for r in mapped})!=len(mapped) or set(values)!={r['mapping_id'] for r in mapped}:
        raise ValueError('mapped and attributed path population differs')
    targets={r['source_text']['handle'] for r in ownership['records']};by_edge={};seen=set();mapped_edges={eid for r in mapped for eid in r['iso_edges']}
    if not targets or len(targets)!=len(ownership['records']):raise ValueError('native annotation scope empty or repeated')
    for proof in ownership['records']:
        eid=proof['current_edge_id'];binding=proof['native_binding'];value=proof['nominal_mm_candidate']
        if (eid not in edges or eid not in mapped_edges or binding.get('current_graph_owners')!=[eid]
            or proof.get('source_chain')!=[binding.get('root_handle'),binding.get('child_handle')]
            or binding.get('layer')!=LAYERS.get(edges[eid]['system']) or binding.get('Z_coincident') is not True
            or proof['source_text'].get('source_sha256')!=ownership['source_sha256']
            or proof.get('scope')!='native_nested_branch_annotation_only_not_whole_edge_DN'
            or proof.get('whole_edge_DN_assigned') is not False or proof.get('human_accepted') is not False
            or len(set(proof.get('independent_control_roots',[])))<4
            or targets.intersection(proof.get('independent_control_text_handles',[]))
            or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):
            raise ValueError('axis source annotation owner, independent controls or unknown extent differs')
        by_edge.setdefault(eid,[]).append(proof)
    records=[]
    for row in mapped:
        attribute=values[row['mapping_id']];diameter=attribute['diameter'];value=diameter['nominal_mm']
        if (any(attribute[k]!=row[k] for k in ('kind','floor','system','plan_edges','iso_edges'))
            or selected_snapshot(axis,row['iso_edges'])!=row['iso_snapshot'] or not diameter.get('lineage')
            or diameter.get('system')!=row['system'] or diameter.get('edge_id') not in row['plan_edges']
            or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):
            raise ValueError('mapped local snapshot or plan DN lineage changed')
        proofs=[p for eid in row['iso_edges'] for p in by_edge.get(eid,[])]
        for proof in proofs:
            h=proof['source_text']['handle']
            if h in seen:raise ValueError('native local DN annotation belongs to more than one mapped path')
            seen.add(h)
        different=any(p['nominal_mm_candidate']!=value for p in proofs)
        status=('different_native_DN_values_segment_extents_unresolved' if different else 'same_local_values_extents_still_unproven') if proofs else 'no_selected_native_axis_annotation_not_an_agreement'
        records.append(dict(mapping_id=row['mapping_id'],group_id=row.get('group_id'),kind=row['kind'],equipment_id=row.get('equipment_id'),floor=row['floor'],system=row['system'],
            plan_edges=row['plan_edges'],iso_edges=row['iso_edges'],plan_drawn_nominal_mm=value,plan_DN_lineage=copy.deepcopy(diameter['lineage']),
            axis_native_observations=copy.deepcopy(proofs),status=status,whole_axis_DN_fusion_blocked=bool(different),
            equal_segment_extents_proved=False,whole_axis_DN_selected=False,physical_length_mm=None,human_accepted=False))
    if seen!=targets:raise ValueError('selected native annotations were not accounted for')
    return dict(mode=MODE,status='source_owned_local_DN_comparison_segment_extents_and_fusion_pending',records=records,
        source_sha256=copy.deepcopy(mapping['source_sha256']),plan_graph_sha256=mapping['plan_graph_sha256'],iso_graph_sha256=mapping['iso_graph_sha256'],
        annotated_paths=sum(bool(r['axis_native_observations']) for r in records),difference_paths=sum(r['whole_axis_DN_fusion_blocked'] for r in records),
        paths_without_selected_axis_annotations=sum(not r['axis_native_observations'] for r in records),
        DN_fusion_blocked_mapping_ids=[r['mapping_id'] for r in records if r['whole_axis_DN_fusion_blocked']],
        local_graphs_mutated=False,physical_values_fused=False,source_contradictions_confirmed=False,human_accepted=False,hil_ready=False)


def compute(paths,policy):
    for key in ('attributes','attribute_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('mapped DN comparison dependency changed '+key)
    folder=Path(paths['attributes']).resolve().parent
    if Path(paths['attributes']).resolve()!=folder/'wave-plan-attributes.json' or Path(paths['attribute_receipt']).resolve()!=folder/'wave-plan-attribute-receipt.json':raise ValueError('noncanonical mapped DN attribute stage')
    attributes=verify_attributes(folder);receipt=load(paths['attribute_receipt']);mapping_path=receipt['inputs']['mapping']['path'];mapping=load(mapping_path)
    mapping_receipt=load(receipt['inputs']['mapping_receipt']['path']);local=mapping_receipt['local_inputs'];source=local['iso_source'];graph=local['iso_graph']
    if sha(source['path'])!=source['sha256'] or sha(graph['path'])!=graph['sha256']:raise ValueError('native axis comparison input changed')
    doc,preflight=read_source(source['path']);axis=load(graph['path']);ownership=collect(doc,axis,policy['axis_text_handles'],source['sha256'],graph['sha256'])
    result=compare(mapping,attributes,axis,ownership);result.update(source_preflight=preflight,mapping_sha256=sha(mapping_path),attributes_sha256=sha(paths['attributes']),native_axis_ownership=ownership)
    return result


def implementation_hashes():
    from wave_rebased_plan_attributes import implementation_hashes as inherited
    result=inherited()
    for name in (Path(__file__).name,'native_repeated_branch_DN_layout.py','source_dn_bulk_screen.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def check_result(data):
    if (data.get('mode')!=MODE or data.get('status')!='source_owned_local_DN_comparison_segment_extents_and_fusion_pending'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','source_contradictions_confirmed','human_accepted','hil_ready'))):
        raise ValueError('mapped local DN comparison escaped its source-only scope')
    rows=data['records'];ids=[r['mapping_id'] for r in rows]
    if not rows or len(ids)!=len(set(ids)):raise ValueError('mapped DN comparison scope empty or repeated')
    blocked=[];annotated=0;unexamined=0
    for row in rows:
        if (any(row.get(k) is not False for k in ('equal_segment_extents_proved','whole_axis_DN_selected','human_accepted'))
            or row.get('physical_length_mm') is not None):raise ValueError('mapped local DN comparison promoted unproved physical scope')
        observations=row['axis_native_observations'];different=any(p['nominal_mm_candidate']!=row['plan_drawn_nominal_mm'] for p in observations)
        expected=('different_native_DN_values_segment_extents_unresolved' if different else 'same_local_values_extents_still_unproven') if observations else 'no_selected_native_axis_annotation_not_an_agreement'
        if row['status']!=expected or row['whole_axis_DN_fusion_blocked']!=bool(different):raise ValueError('mapped local DN difference classification differs')
        annotated+=bool(observations);unexamined+=not observations
        if different:blocked.append(row['mapping_id'])
    if (data['DN_fusion_blocked_mapping_ids']!=blocked or data['annotated_paths']!=annotated or data['difference_paths']!=len(blocked)
        or data['paths_without_selected_axis_annotations']!=unexamined):raise ValueError('mapped local DN comparison counts or blocked paths differ')
    return dict(status='pending',source_replay='passed',mapped_paths=len(rows),annotated_paths=annotated,DN_difference_paths=len(blocked),paths_without_selected_axis_annotations=unexamined,
        plan_graph_sha256=data['plan_graph_sha256'],iso_graph_sha256=data['iso_graph_sha256'],mapping_sha256=data['mapping_sha256'],
        attributes_sha256=data['attributes_sha256'],physical_values_fused=False,source_contradictions_confirmed=False,human_accepted=False,hil_ready=False,
        pending=['Resolve the native annotation segment extents before affected whole-axis DN fusion; unselected annotations are not agreement evidence'])


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'DN-comparison-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('mapped DN comparison implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('mapped DN comparison input changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'DN-comparison.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('mapped DN comparison native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('attribute-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(attributes=a.attribute_run/'wave-plan-attributes.json',attribute_receipt=a.attribute_run/'wave-plan-attribute-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'DN-comparison.json';target.write_bytes(encode(result))
    (a.output/'DN-comparison-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={key:dict(path=str(value.resolve()),sha256=sha(value)) for key,value in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(paths=len(result['records']),annotated_paths=result['annotated_paths'],difference_paths=result['difference_paths'],physical_values_fused=False),flush=True)


if __name__=='__main__':main()
