"""Reapply existing metric readers to every newly qualified cycle interval.

DN conflict does not block an independently witnessed complete centreline.
Touching arrays are a reading subdivision; a real gap stays unknown.
"""
import argparse,copy,importlib,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from native_plan_projection_lengths import unit_evidence,lengths
from native_main_interval_metrics import touching_projection,coalesced_scope
from native_main_endpoint_extent import endpoint_relation
from attach_anchored_floor_main_attributes import horizontal_domain
from native_replay_session import verify_once
MODE='native_cycle_gate_plan_centerline_batch_v1'

def qualify(plan,axis,row,units,angles):
    if units.get('status')!='native_mm_units_corroborated_not_pipe_dimension_assignment' or row.get('classification')!='horizontal_only':raise ValueError('qualified floor-plan units and pure horizontal interval required')
    if len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('one-to-one native interval required')
    coverage=row['native_path_evidence']['plan'];eid=row['plan_edges'][0]
    source=next(e for e in plan['edges']if e['edge_id']==eid)
    if source.get('source_flexible_joints')or source.get('source_view_context')or source.get('source_wave_omission'):raise ValueError('inline, omitted or detail span needs its existing specific metric owner')
    binding=None
    try:projection=lengths(plan,coverage,row,units);reader='original_native_plan_projection'
    except ValueError:
        projection=touching_projection(plan,coverage,row,units);reader='original_exact_touching_projection'
    try:pr=endpoint_relation(plan,eid,row['floor'],row['system'])
    except ValueError:
        private,binding=coalesced_scope(plan,row)
        pr=endpoint_relation(private,eid,row['floor'],row['system'])
    ar=endpoint_relation(axis,row['iso_edges'][0],row['floor'],row['system'])
    ae=next(e for e in axis['edges']if e['edge_id']==row['iso_edges'][0]);reading=dict(ae)
    if ar['path_orientation']=='end_to_start':reading['attribute_paths']=[list(reversed(ae['attribute_paths'][0]))]
    horizontal_domain(dict(axis,edges=[reading]),row,angles)
    value=projection['value_mm'];pieces=projection['pieces']
    if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0 or not pieces or abs(sum(p['length_mm']for p in pieces)-value)>.0001:raise ValueError('finite source centreline pieces required')
    return dict(mapping_id=row['mapping_id'],axis_edge_id=ae['edge_id'],plan_edge_id=eid,floor=row['floor'],system=row['system'],
        axis_nodes=[ae['start_node_id'],ae['end_node_id']],axis_attribute_paths=copy.deepcopy(ae['attribute_paths']),
        plan_nodes=[source['start_node_id'],source['end_node_id']],plan_attribute_paths=copy.deepcopy(source['attribute_paths']),
        complete_horizontal_centerline_mm=value,projection=projection,metric_reader=reader,
        endpoint_relations=dict(plan=pr,iso=ar),plan_subdivision_reading_projection=binding,
        nominal_mm=None,DN_status='unknown_pending_plan_DN_scope_resolution',
        component_profiles=copy.deepcopy(row['component_profiles']),physical_installed_length_mm=None,net_pipe_cut_length_mm=None,
        source_paths_mutated=False,unknown_length_filled_with_zero=False,DN_used_for_matching=False,human_accepted=False)

def compute(manifest):
    from rebuild_anchored_cycle_gate_batch import verify_output,MODE as PARENT_MODE
    from source_readability import read_source
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in manifest['inputs'].items()):raise ValueError('cycle metric input changed')
    checked();parent=verify_once(paths['cycle_proof'].parent,verify_output)
    if parent.get('mode')!=PARENT_MODE or encode(parent)!=paths['cycle_proof'].read_bytes():raise ValueError('native cycle correspondence parent differs')
    floor=manifest['floor']
    if type(floor)is not int or str(floor)not in parent['floors']:raise ValueError('explicit proved floor required')
    for key,parentkey in [('plan_graph','plan_graph_'+str(floor)),('axis_graph','axis_graph'),('plan_source','plan_source_'+str(floor))]:
        if sha(paths[key])!=parent['inputs'][parentkey]['sha256']:raise ValueError('metric uses another current graph or source')
    plan,axis=load(paths['plan_graph']),load(paths['axis_graph']);doc,preflight=read_source(paths['plan_source']);units=unit_evidence(doc,load(paths['unit_policy']))
    records=[];pending=[];rows=parent['floors'][str(floor)]['records']
    for row in rows:
        try:records.append(qualify(plan,axis,row,units,manifest['horizontal_directions_degrees']))
        except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],plan_edges=row['plan_edges'],iso_edges=row['iso_edges'],reason=str(exc)))
    checked()
    return dict(mode=MODE,records=records,pending=pending,inputs=manifest['inputs'],units=units,source_preflight=preflight,
        counts=dict(source_intervals=len(rows),complete_horizontal_centerlines=len(records),pending_metrics=len(pending)),
        cycle_correspondences_independently_replayed=True,original_metric_readers_reused=True,
        local_graphs_changed=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False)

def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in ('rebuild_anchored_cycle_gate_batch','native_plan_projection_lengths','native_main_interval_metrics','native_main_endpoint_extent','attach_anchored_floor_main_attributes','source_readability')})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest_path))
    if code!=implementation_hashes():raise ValueError('cycle metric code changed')
    output.mkdir(parents=True);p=output/'cycle-gate-plan-lengths.json';p.write_bytes(encode(r))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=code,output_sha256=sha(p))))
    return r

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'cycle-gate-plan-lengths.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('cycle metric receipt, code or input changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('cycle metric independent native replay differs')
    return r

def main():
    parser=argparse.ArgumentParser()
    for n in ('manifest','output','verify-output'):parser.add_argument('--'+n,type=Path)
    a=parser.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:parser.error('manifest and new output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
