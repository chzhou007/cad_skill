"""Reuse native endpoint/metric readers for already mapped bounded mains.

Screen the whole current bounded cohort. Keep the old mappings and DN values;
only a source-witnessed complete horizontal centreline may be added.
"""
import argparse,copy,importlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from native_main_endpoint_extent import qualify
from native_main_interval_metrics import coalesced_scope
from native_replay_session import verify_once
from qualified_crossview_provider_inventory import verify_output as verify_inventory
from rebuild_anchor_bounded_main_batch import verify_output as verify_bounded
from native_current_junction_reader import make_reader
from crossview_equipment_branch_inventory import native_tee
from match_source_checked_crossview_paths import selected_snapshot
from batch_native_path_coverage import collect as coverage
from native_plan_projection_lengths import unit_evidence,lengths
from noncompound_main_extent_guard import barriers,check as check_carrier
from source_readability import read_source
from compound_carrier_fragment_scope import qualify as qualify_fragment
MODE='native_bounded_main_complete_extents_v1'


def scope(plan,axis,value,angles):
    row=dict(kind='same_floor_T_to_T_main',mapping_id=value['mapping_id'],
        floor=value['floor'],system=value['system'],plan_edges=value['plan_edges'],
        iso_edges=[value['axis_edge_id']],plan_start=value['plan_Ts'][0],
        plan_end=value['plan_Ts'][1],iso_start=value['axis_Ts'][0],iso_end=value['axis_Ts'][1])
    if value.get('DN_status')!='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild' or value.get('whole_axis_DN_selected')is not True:
        raise ValueError('existing qualified whole-main DN required')
    edge=next(e for e in plan['edges']if e['edge_id']==row['plan_edges'][0])
    if value['plan_DN_record']['nominal_mm']!=value['nominal_mm'] or value['plan_DN_record']['scope_paths']!=edge['attribute_paths']:
        raise ValueError('existing DN source scope differs')
    if edge.get('source_flexible_joints'):
        raise ValueError('inline flexible assembly retains unknown interior length')
    projected=plan;binding=None
    if len(edge['attribute_paths'])>1:projected,binding=coalesced_scope(plan,row)
    result=qualify(projected,axis,row,value['nominal_mm'],value['plan_horizontal_projection'],angles)
    if result['complete_horizontal_centerline_route_mm']is None:
        raise ValueError('native metric does not complete the T-to-T centreline')
    return row,result,binding


def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('bounded extent input changed')
    checked();inventory=verify_once(paths['provider_inventory'].parent,verify_inventory)
    old=verify_once(paths['bounded_proof'].parent,verify_bounded)
    m=load(paths['viewer_manifest']);context=m['attributeValueContext']['anchor_bounded_mains']
    if sha(paths['bounded_proof'])!=context['source_bindings']['native_proof'] or not inventory['current_provider_artifact_replayed']:
        raise ValueError('current bounded provider differs from replayed source owner')
    floor=manifest['floor'];plan=load(paths['plan_graph']);old_plan=load(paths['previous_plan_graph']);axis=load(paths['axis_graph'])
    if manifest['inputs']['plan_graph']!=load(paths['provider_inventory'].parent/'provider-inventory.json')['inputs']['plan_graph_'+str(floor)]:
        raise ValueError('current plan not covered by native inventory owner')
    if m['attributeValueContext']['source_graph_sha256']!=sha(paths['raw_axis_graph']):raise ValueError('raw axis provider differs')
    if old['source_hashes']['plan_graph_'+str(floor)]!=sha(paths['previous_plan_graph']) or old['source_hashes']['axis_graph']!=sha(paths['axis_graph']):
        raise ValueError('bounded ancestor graph identity differs')
    values=context['records'];rows=[];pending=[]
    if len(values)!=context['axis_edges'] or len({v['axis_edge_id']for v in values})!=len(values):raise ValueError('bounded cohort identity repeats')
    for value in values:
        if value['floor']!=floor:raise ValueError('explicit single current cohort floor required')
        original=next(r for r in old['floors'][str(floor)]['records']if r['mapping_id']==value['mapping_id'])
        if original['plan_edges']!=value['plan_edges'] or original['iso_edges']!=[value['axis_edge_id']]:raise ValueError('old bounded correspondence changed')
        if selected_snapshot(plan,value['plan_edges'])!=selected_snapshot(old_plan,value['plan_edges']):
            raise ValueError('owner repair changed the selected bounded source scope')
        try:row,result,binding=scope(plan,axis,value,manifest['horizontal_directions_degrees'])
        except ValueError as e:pending.append(dict(axis_edge_id=value['axis_edge_id'],mapping_id=value['mapping_id'],reason=str(e)));continue
        rows.append((value,row,result,binding))
    pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source'])
    guard=barriers(pd,plan,sha(paths['plan_source']));units=unit_evidence(pd,load(paths['unit_policy']))
    hashes=dict(plan=dict(source_sha256=sha(paths['plan_source']),graph_sha256=sha(paths['plan_graph'])),iso=dict(source_sha256=sha(paths['axis_source']),graph_sha256=sha(paths['axis_graph'])))
    reader=make_reader(load(paths['current_T_policy']),hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    records=[];quarantined=[];raw={e['edge_id']:e for e in load(paths['raw_axis_graph'])['edges']}
    for value,row,result,binding in rows:
        carrier=[copy.deepcopy(c)for c in guard['corridors']if any(e['edge_id']in row['plan_edges']for e in c['edges'])]
        fragment=qualify_fragment(pd,plan,row,value,carrier,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
        carrier=fragment['corridors']
        if binding is not None:raise ValueError('touching-path candidate needs a separate native metric projection owner')
        native={}
        for view,doc,g,tee in(('plan',pd,plan,reader),('iso',ad,axis,native_tee)):
            h=hashes[view];p=coverage(doc,g,row[view+'_edges'],h['source_sha256'],h['graph_sha256'])
            if any(s['status']!='single_source_line_covers'for e in p['edges']for s in e['segments']):raise ValueError('complete extent lacks unique native source path')
            native[view]=dict(snapshot=selected_snapshot(g,row[view+'_edges']),path_coverage=p,
                junctions={n:tee(doc,g,n,h['source_sha256'],h['graph_sha256'])for n in(row[view+'_start'],row[view+'_end'])})
        eid=value['axis_edge_id'];identity=next(e for e in axis['edges']if e['edge_id']==eid)
        if any(raw[eid].get(k)!=identity.get(k)for k in('system','start_node_id','end_node_id','attribute_paths','equipment_inventory')):raise ValueError('raw axis bounded scope changed')
        metric=lengths(plan,native['plan']['path_coverage'],row,units)
        if abs(metric['value_mm']-value['plan_horizontal_projection']['value_mm'])>.0001:raise ValueError('fresh native metric differs from existing projection')
        result=qualify(plan,axis,row,value['nominal_mm'],metric,manifest['horizontal_directions_degrees'])
        record=dict(result,mapping=row,prior_bounded_scope=copy.deepcopy(value),native_source_evidence=native,
            source_hashes=hashes,compound_fragment_scope=fragment,installed_whole_edge_length_mm=None,human_accepted=False)
        if carrier:
            record.update(reason='compound_carrier_requires_its_member_identity_not_scalar_main_extent',carrier_evidence=carrier,
                candidate_T_to_T_projection_mm=record['complete_horizontal_centerline_route_mm'],complete_horizontal_centerline_route_mm=None,
                old_scalar_DN_is_observation_not_current_member_value=True)
            quarantined.append(record);pending.append(dict(axis_edge_id=eid,mapping_id=row['mapping_id'],reason=record['reason']))
        else:records.append(record)
    checked();return dict(mode=MODE,inputs=manifest['inputs'],records=records,quarantined_records=quarantined,pending=pending,
        counts=dict(screened_bounded_edges=len(values),complete_horizontal_centerlines=len(records),quarantined_scalar_DN_edges=len(quarantined),pending_extents=len(pending)),
        source_preflight=dict(plan=pp,iso=ap),current_provider_inventory_replayed=True,bounded_ancestor_native_replayed=True,
        selected_old_and_current_plan_scopes_exact=True,existing_correspondences_unchanged=True,DN_observations_preserved=True,
        local_graphs_mutated=False,source_paths_mutated=False,installed_lengths_assigned=0,net_pipe_cut_lengths_assigned=0,human_accepted=False)


def implementation_hashes():
    names=('qualified_crossview_provider_inventory','rebuild_anchor_bounded_main_batch','native_main_endpoint_extent','native_main_interval_metrics','native_current_junction_reader','native_plan_projection_lengths','noncompound_main_extent_guard','source_readability','batch_native_path_coverage','compound_carrier_fragment_scope','source_direct_dn_evidence','native_dn_text_position')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    r=compute(load(manifest));output.mkdir(parents=True);target=output/'bounded-main-extents.json';target.write_bytes(encode(r))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target))))
    return r


def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'bounded-main-extents.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes() or sha(m['path'])!=m['sha256'] or sha(target)!=receipt['output_sha256']:raise ValueError('bounded extent receipt, implementation or input changed')
    r=compute(load(m['path']))
    if encode(r)!=target.read_bytes():raise ValueError('independent native bounded extent replay differs')
    return r


def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
