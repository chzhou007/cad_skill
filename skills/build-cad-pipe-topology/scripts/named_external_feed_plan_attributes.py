"""Plan DN and source-pipe XY on independently mapped external feeds.

Reuse complete scalar/F scans, native through-T inheritance and inline metrics.
Boundary names corroborate identity; they are never horizontal DN seeds.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_named_external_boundary_paths import verify_output as verify_mapping,implementation_hashes as mapping_hashes,MODE as MAPPING_MODE
from anchored_floor_main_plan_attributes import verify_output as verify_main_attributes,implementation_hashes as main_attribute_hashes,observe_annotations,inline_projection
from through_source_DN_inheritance import infer
from native_plan_projection_lengths import unit_evidence
from source_readability import read_source

MODE='named_external_feed_plan_DN_XY_attributes_v1'


def preserve_inheritance(old,observations,inherited,external_ids):
    original={r['evidence_id']:r for r in old['direct_observations']};current={r['evidence_id']:r for r in observations}
    if len(original)!=len(old['direct_observations']) or len(current)!=len(observations) or any(current.get(k)!=v for k,v in original.items()):raise ValueError('previous native scalar/F observations changed')
    if any(row['edge_id'] not in external_ids for key,row in current.items() if key not in original):raise ValueError('new annotation lies outside selected external feeds')
    by={r['edge_id']:r for r in inherited['records']};checks=[]
    for row in old['records']:
        eid=row['plan_edges'][0];previous=row['diameter'];now=by.get(eid)
        if not now or any(now[k]!=previous[k] for k in ('system','nominal_mm','status')):raise ValueError('external extension changes existing main DN '+eid)
        checks.append(dict(plan_edge=eid,nominal_mm=now['nominal_mm'],DN_status=now['status'],old_value_preserved=True))
    return checks


def build_records(graph,mapping,inherited,units):
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('local_graphs_mutated') is not False or mapping.get('physical_values_assigned')!=0
        or any(mapping.get(k) is not False for k in ('human_accepted','hil_ready'))
        or inherited.get('source_sha256')!=mapping['source_sha256']['plan'] or inherited.get('graph_sha256')!=mapping['graph_sha256']['plan']):raise ValueError('checked external correspondence required')
    dn={r['edge_id']:r for r in inherited['records']};rows=[];used=set()
    if len(dn)!=len(inherited['records']):raise ValueError('duplicate inherited DN scope')
    for record in mapping['records']:
        if len(record['plan_edges'])!=1 or len(record['iso_edges'])!=1 or record['plan_edges'][0] in used:raise ValueError('unique single external paths required')
        eid=record['plan_edges'][0];used.add(eid);diameter=dn[eid];value=diameter['nominal_mm']
        if (diameter['system']!=record['system'] or diameter.get('human_accepted') is not False
            or value is not None and diameter.get('status') not in ('direct_plan_DN','T_inherited_plan_DN')
            or value is None and diameter.get('status') not in ('conflict','unresolved')
            or any(record.get(k) is not False for k in ('external_ports_connected_to_each_other','physical_external_connection_verified','physical_port_verified','human_accepted'))
            or record.get('physical_length_mm') is not None or record.get('whole_edge_DN_assigned') is not False
            or value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0)):raise ValueError('external DN evidence or service differs')
        edge=next(e for e in graph['edges'] if e['edge_id']==eid)
        if diameter['scope_paths']!=edge['attribute_paths']:raise ValueError('DN must cover original pipe paths on both sides of the checked joint')
        metric=inline_projection(graph,record['native_plan_inline_path'],record,units)
        axis=record['native_axis_path_coverage'];display=record['axis_display_only_segment_index'];gaps={r['gap_segment_index'] for r in record['native_axis_confirmed_gap']}
        indices=[s['index'] for s in axis['segments'] if s['status']=='single_source_line_covers']
        if (not indices or set(indices)&({display}|gaps) or {s['index'] for s in axis['segments']}!=set(indices)|{display}|gaps):raise ValueError('axis pipe scope contains unknown or annotation segments')
        observation=record['native_axis_destination']['nominal_mm_observed']
        rows.append(dict(mapping_id=record['mapping_id'],kind=record['kind'],floor=record['floor'],system=record['system'],identifier=record['identifier'],destination=record['destination'],
            plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],plan_boundary_node=record['plan_boundary_node'],axis_boundary_node=record['axis_boundary_node'],axis_port_id=record['axis_port_id'],
            diameter=copy.deepcopy(diameter),horizontal_projection=metric,inline_interiors_unknown=True,complete_horizontal_centerline_route_mm=None,
            axis_pipe_segment_indices=indices,axis_display_only_segment_index=display,axis_inline_gap_segment_indices=sorted(gaps),axis_named_DN_observation_mm=observation,
            axis_DN_consistency='same_as_plan' if value==observation else 'plan_unknown' if value is None else 'source_disagreement',
            axis_named_DN_used_as_plan_seed=False,whole_axis_edge_DN_selected=False,installed_whole_edge_length_mm=None,physical_ports_verified=False,
            external_ports_connected_to_each_other=False,physical_external_connection_verified=False,human_accepted=False))
    return rows


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','main_attributes','main_attribute_receipt','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('external attribute input changed '+key)
    folder=Path(paths['mapping']).resolve().parent;prior=Path(paths['main_attributes']).resolve().parent
    if Path(paths['mapping']).name!='mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'named-external-path-mapping-receipt.json':raise ValueError('noncanonical external mapping')
    if Path(paths['main_attributes']).name!='attributes.json' or Path(paths['main_attribute_receipt']).resolve()!=prior/'floor-main-attribute-receipt.json':raise ValueError('noncanonical complete main attribute owner')
    mapping=verify_mapping(folder);old=verify_main_attributes(prior);receipt=load(paths['mapping_receipt']);mr=load(receipt['inputs']['main_receipt']['path']);main=load(receipt['inputs']['main_mapping']['path']);local=mr['local_inputs']
    sh=main['source_sha256']['plan'];gh=main['plan_graph_sha256']
    if (mapping['graph_sha256']!=old['graph_sha256'] or mapping['source_sha256']!=old['source_sha256'] or old['mapping_sha256']!=sha(receipt['inputs']['main_mapping']['path'])
        or sha(local['plan_source']['path'])!=sh or sha(local['plan_graph']['path'])!=gh):raise ValueError('external and complete main attributes use different native parents')
    graph=load(local['plan_graph']['path']);doc,preflight=read_source(local['plan_source']['path']);origin=load(load(paths['main_attribute_receipt'])['inputs']['F_origin']['path'])
    frames=[f for group in origin.get('groups',[]) for f in group.get('line_F_frames',[])];feeds={r['plan_edges'][0] for r in mapping['records']};mains={r['plan_edges'][0] for r in main['records']}
    if feeds&mains or len(feeds)!=len(mapping['records']):raise ValueError('external scope overlaps a main writer')
    observations,annotation=observe_annotations(doc,graph,feeds|mains,frames,sh,gh)
    inherited=infer(graph,[{k:r[k] for k in ('edge_id','nominal_mm','evidence_id')} for r in observations],feeds|mains,main['evidence']['native_T_proofs']['plan'],sh,gh)
    preserved=preserve_inheritance(old,observations,inherited,feeds);units=unit_evidence(doc,load(paths['metric_policy']))
    if units!=old['unit_evidence']:raise ValueError('external lengths use a different verified native plan unit scope')
    rows=build_records(graph,mapping,inherited,units)
    for key in ('mapping','mapping_receipt','main_attributes','main_attribute_receipt','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('external attribute input changed during replay '+key)
    return dict(mode=MODE,status='source_checked_external_plan_DN_XY_attributes_not_fused',records=rows,mapping_sha256=sha(paths['mapping']),main_attributes_sha256=sha(paths['main_attributes']),
        source_sha256=mapping['source_sha256'],graph_sha256=mapping['graph_sha256'],source_preflight=preflight,source_annotation_evidence=annotation,direct_observations=observations,
        inherited_DN=inherited,prior_main_DN_preservation=preserved,unit_evidence=units,known_DN_records=sum(r['diameter']['nominal_mm'] is not None for r in rows),
        inline_length_incomplete_records=len(rows),local_graphs_mutated=False,physical_values_fused=False,installed_whole_lengths_assigned=0,human_accepted=False,hil_ready=False)


def implementation_hashes():
    result=mapping_hashes();result.update(main_attribute_hashes());result[Path(__file__).name]=sha(__file__);return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'external-feed-plan-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('external attribute implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('external attribute dependency changed')
    result=compute({k:r['path'] for k,r in receipt['inputs'].items()},load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'attributes.json').read_bytes() or sha(directory/'attributes.json')!=receipt['output_sha256']:raise ValueError('external plan attributes native replay differs')
    return result


def main():
    p=argparse.ArgumentParser()
    for key in ('mapping-run','main-attribute-run','metric-policy','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'named-external-path-mapping-receipt.json',main_attributes=a.main_attribute_run/'attributes.json',main_attribute_receipt=a.main_attribute_run/'floor-main-attribute-receipt.json',metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    data=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'attributes.json';target.write_bytes(encode(data))
    (a.output/'external-feed-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(Path(v).resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(external_attributes=len(data['records']),known_DN=data['known_DN_records'],whole_physical_lengths_assigned=0),flush=True)

if __name__=='__main__':main()
