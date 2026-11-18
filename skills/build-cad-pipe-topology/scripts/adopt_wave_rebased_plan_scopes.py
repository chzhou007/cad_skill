"""Adopt fresh plan scopes while preserving the exact historical attributes.

An explicit child proof validates current local topology; historical receipts
and IDs retain their original identities. New scopes remain partial unless a
separate physical extent stage proves a whole edge.
"""
import argparse,copy,hashlib,math,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_source_checked_crossview_paths import selected_snapshot
from axis_local_DN_segment_domains import locate

MODE='wave_rebased_plan_scope_adoption_v1'
ROOT='sourceWaveRebasedPlanScopeAdoption'


def metric_signature(metric):
    return [(p['plan_edge'],p['path_index'],p['segment_index'],p['source_line_handle'],p['points'],p['length_mm']) for p in metric['pieces']]


def partial_attribute(row,scope,source_hashes,mapping_hash,attribute_hash):
    metric=copy.deepcopy(scope['horizontal_projection']);single=len(row['iso_edges'])==1
    metric.update(edge_value_mm=metric['value_mm'] if single else None,
        allocation='whole_mapped_axis_edge_projection' if single else 'route_total_only_not_allocated_to_each_axis_edge')
    dn=copy.deepcopy(scope['diameter']);value=dn['nominal_mm']
    return dict(status='partial_plan_attributes_source_checked',mapping_id=row['mapping_id'],mapping_basis='native_source_and_main_branch_order',
        mapping_kind=row['kind'],mapping_evidence_sha256=mapping_hash,floor=row['floor'],system=row['system'],plan_edges=list(row['plan_edges']),iso_edges=list(row['iso_edges']),
        source_hashes=copy.deepcopy(source_hashes),horizontal_projection=metric,
        diameter=dict(nominal_mm=None,status='source_checked_plan_DN_axis_extent_partial',plan_candidate=None,plan_observations=[],axis_observation=None,
            selected_physical_diameter=False,plan_drawn_nominal_mm=value,plan_drawn_values=[dn],plan_scope_evidence_sha256=attribute_hash,
            plan_drawn_status='source_checked_plan_DN_scope_human_pending'),
        plan_DN_scope_evidence_sha256=attribute_hash,whole_axis_main_scope=None,axis_vertical_drawing_strokes=[],whole_edge_physical_length_mm=None,
        equipment_connector_length_mm=None,physical_ports_verified=False,human_accepted=False)


def adopt(parent,local,plan,mapping,attributes,comparison,domains,policy,hashes):
    if ROOT in parent:raise ValueError('current wave plan scopes already adopted')
    if (mapping['plan_graph_sha256']!=attributes['graph_sha256'] or mapping['iso_graph_sha256']!=attributes['iso_graph_sha256']
        or attributes['mapping_sha256']!=hashes['mapping'] or comparison['mapping_sha256']!=hashes['mapping']
        or comparison['attributes_sha256']!=hashes['attributes'] or comparison['plan_graph_sha256']!=attributes['graph_sha256']
        or comparison['iso_graph_sha256']!=attributes['iso_graph_sha256'] or attributes['physical_values_fused'] is not False
        or comparison['physical_values_fused'] is not False or comparison['source_contradictions_confirmed'] is not False
        or comparison['human_accepted'] is not False or attributes['human_accepted'] is not False):raise ValueError('fresh current mapping, attributes and comparison required')
    if parent['nodes']!=local['nodes']:raise ValueError('scope adoption parent changed local nodes')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys():raise ValueError('scope adoption changed local edge identities')
    for eid,edge in old.items():
        if {k:v for k,v in edge.items() if k not in ('cross_view_attributes','axis_riser_attributes','plan_segment_attributes')}!=raw[eid]:
            raise ValueError('scope adoption parent changed local geometry or components')
    rows=mapping['records'];values={r['mapping_id']:r for r in attributes['records']};differences={r['mapping_id']:r for r in comparison['records']}
    if len(values)!=len(attributes['records']) or len(differences)!=len(comparison['records']) or set(values)!=set(differences) or set(values)!={r['mapping_id'] for r in rows}:
        raise ValueError('complete mapped attribute/comparison scope required')
    if (domains.get('graph_sha256')!=mapping['iso_graph_sha256'] or domains.get('source_sha256')!=mapping['source_sha256']['iso']
        or domains.get('graph_mutated') is not False or domains.get('physical_values_assigned')!=0):raise ValueError('current axis annotation domains required')
    by_edge={}
    for domain in domains['records']:by_edge.setdefault(domain['edge_id'],[]).append(domain)
    expected_old=policy.get('retained_historical_mapping_ids',[])
    if len(expected_old)!=len(set(expected_old)):raise ValueError('historical mapping identities repeated')
    old_graph_hash=mapping['evidence']['native_wave_inventory_rebase']['old_plan_graph_sha256'];out=copy.deepcopy(parent);target={e['edge_id']:e for e in out['edges']}
    sources=dict(plan=mapping['source_sha256']['plan'],isometric=mapping['source_sha256']['iso'],plan_graph=mapping['plan_graph_sha256'],local_iso_graph=mapping['iso_graph_sha256'])
    proof=[];history=[];retained=[];claimed=set();new_ids=[]
    for row in rows:
        current=values[row['mapping_id']];difference=differences[row['mapping_id']]
        if (selected_snapshot(local,row['iso_edges'])!=row['iso_snapshot'] or selected_snapshot(plan,row['plan_edges'])!=row['plan_snapshot']
            or any(current[k]!=row[k] or difference[k]!=row[k] for k in ('kind','floor','system','plan_edges','iso_edges'))):raise ValueError('current mapped local path or source scope changed')
        for eid in row['iso_edges']:
            if eid in claimed:raise ValueError('current plan scope writers overlap')
            claimed.add(eid);edge=target[eid];previous=old[eid].get('cross_view_attributes')
            if edge['system']!=row['system']:raise ValueError('current axis service changed')
            if previous is not None:
                metric=previous['horizontal_projection'];diameter=previous['diameter'];old_value=diameter.get('plan_drawn_nominal_mm')
                if (previous['mapping_id'] not in expected_old or previous.get('human_accepted') is not False
                    or previous['floor']!=row['floor'] or previous['system']!=row['system'] or previous['plan_edges']!=row['plan_edges'] or previous['iso_edges']!=row['iso_edges']
                    or previous['source_hashes']['plan_graph']!=old_graph_hash or previous['source_hashes']['plan']!=sources['plan']
                    or previous['source_hashes']['local_iso_graph']!=sources['local_iso_graph']
                    or old_value!=current['diameter']['nominal_mm'] or metric_signature(metric)!=metric_signature(current['horizontal_projection'])
                    or abs(metric['value_mm']-current['horizontal_projection']['value_mm'])>1e-8):raise ValueError('historical plan DN/XY scope changed and needs explicit reconciliation')
                if difference['whole_axis_DN_fusion_blocked'] and diameter.get('selected_physical_diameter') is True:
                    raise ValueError('historical whole DN has an unresolved native extent difference')
                retained.append(previous['mapping_id']);history.append(dict(edge_id=eid,historical_mapping_id=previous['mapping_id'],historical_attributes=copy.deepcopy(previous),historical_attributes_sha256=hashlib.sha256(encode(previous)).hexdigest()))
                added=False
            else:
                edge['cross_view_attributes']=partial_attribute(row,current,sources,hashes['mapping'],hashes['attributes']);new_ids.append(eid);added=True
            item=dict(current_mapping_id=row['mapping_id'],historical_mapping_id=previous['mapping_id'] if previous else None,edge_id=eid,
                mapping_kind=row['kind'],floor=row['floor'],system=row['system'],plan_edges=list(row['plan_edges']),iso_edges=list(row['iso_edges']),
                source_sha256=copy.deepcopy(mapping['source_sha256']),plan_graph_sha256=mapping['plan_graph_sha256'],iso_graph_sha256=mapping['iso_graph_sha256'],
                mapping_sha256=hashes['mapping'],attribute_scope_sha256=hashes['attributes'],comparison_sha256=hashes['comparison'],
                diameter=copy.deepcopy(current['diameter']),horizontal_projection=copy.deepcopy(current['horizontal_projection']),
                native_axis_annotation_domains=copy.deepcopy(by_edge.get(eid,[])),DN_extent_comparison=copy.deepcopy(difference),
                added_attribute=added,historical_attribute_semantics_preserved=not added,whole_axis_DN_fusion_blocked=difference['whole_axis_DN_fusion_blocked'],
                equal_plan_axis_segment_extents_proved=False,related_HIL_confirmation_inherited=False,human_accepted=False)
            edge['cross_view_attributes']['current_plan_scope_evidence']=copy.deepcopy(item);proof.append(item)
    if set(retained)!=set(expected_old) or len(retained)!=len(expected_old):raise ValueError('not all historical mapped attributes were retained exactly once')
    out[ROOT]=dict(mode=MODE,status='current_plan_scopes_adopted_partial_axis_extents_and_HIL_pending',records=proof,historical_attribute_snapshots=history,
        parent_graph_sha256=hashes['parent_graph'],mapping_sha256=hashes['mapping'],attribute_scope_sha256=hashes['attributes'],comparison_sha256=hashes['comparison'],
        retained_historical_attributes=len(retained),added_partial_attributes=len(new_ids),added_axis_edges=new_ids,
        prior_topology_components_and_other_attributes_preserved=True,whole_DN_or_lengths_added=0,related_HIL_confirmation_inherited=False,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_current_plan_scope_adoption')
    return out,out[ROOT]


def compute(paths,policy):
    for key in ('parent_graph','devices','comparison','comparison_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('current plan adoption input changed '+key)
    from compare_mapped_plan_axis_diameters import verify_output as verify_comparison
    from attach_lower_floor_plan_attributes import verify_output as verify_parent
    folder=Path(paths['comparison']).resolve().parent
    if Path(paths['comparison']).resolve()!=folder/'DN-comparison.json' or Path(paths['comparison_receipt']).resolve()!=folder/'DN-comparison-receipt.json':raise ValueError('noncanonical native comparison stage')
    comparison=verify_comparison(folder);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('current plan adoption parent or components changed')
    receipt=load(paths['comparison_receipt']);attribute_receipt=load(receipt['inputs']['attribute_receipt']['path']);mapping_path=attribute_receipt['inputs']['mapping']['path'];mapping=load(mapping_path)
    attributes_path=receipt['inputs']['attributes']['path'];attributes=load(attributes_path);mapping_receipt=load(attribute_receipt['inputs']['mapping_receipt']['path']);local=mapping_receipt['local_inputs']
    for key in ('plan_graph','iso_graph'):
        if sha(local[key]['path'])!=local[key]['sha256']:raise ValueError('current local adoption input changed '+key)
    if parent['native_local_graph']['sha256']!=local['iso_graph']['sha256']:raise ValueError('current plan adoption parent uses another local axis')
    axis=load(local['iso_graph']['path']);domains=locate(axis,comparison['native_axis_ownership'],local['iso_source']['sha256'],local['iso_graph']['sha256'])
    hashes=dict(parent_graph=sha(paths['parent_graph']),mapping=sha(mapping_path),attributes=sha(attributes_path),comparison=sha(paths['comparison']))
    graph,proof=adopt(load(paths['parent_graph']),axis,load(local['plan_graph']['path']),mapping,attributes,comparison,domains,policy,hashes)
    return graph,dict(proof=proof,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),native_local_graph=parent['native_local_graph'],
        verified_lower_parent=parent,mapping_path=str(mapping_path),attribute_scope_path=str(attributes_path),axis_annotation_domains=domains)


def implementation_hashes():
    from compare_mapped_plan_axis_diameters import implementation_hashes as comparison_hashes
    from attach_lower_floor_plan_attributes import implementation_hashes as parent_hashes
    result=comparison_hashes();result.update(parent_hashes())
    for name in (Path(__file__).name,'axis_local_DN_segment_domains.py'):result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'wave-plan-scope-adoption-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('current plan scope adoption implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('current plan scope adoption dependency changed')
    graph,proof=compute({key:item['path'] for key,item in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(key)!=value for key,value in proof.items()):
        raise ValueError('current plan scope adoption native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('current plan scope adoption canonical components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-graph','devices','comparison-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_graph=a.parent_graph,devices=a.devices,comparison=a.comparison_run/'DN-comparison.json',comparison_receipt=a.comparison_run/'DN-comparison-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'graph_with_edges.json';target.write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    (a.output/'wave-plan-scope-adoption-audit.json').write_bytes(encode(dict(proof,mode=MODE,inputs={key:dict(path=str(value.resolve()),sha256=sha(value)) for key,value in paths.items()},
        implementation_sha256=implementation_hashes(),output_graph_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(retained=proof['proof']['retained_historical_attributes'],added_partial=proof['proof']['added_partial_attributes'],whole_values_added=0),flush=True)


if __name__=='__main__':main()
