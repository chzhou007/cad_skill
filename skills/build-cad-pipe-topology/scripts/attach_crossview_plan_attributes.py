"""Attach native plan projection evidence to a separately verified axis layer."""
import argparse,copy,hashlib,json,math,re,shutil
from pathlib import Path
from confirm_crossview_paths import verify_output as verify_mapping,load,sha,encode,snapshot
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence,lengths

def diameter_candidates(plan_doc,iso_doc,plan_graph,mapping_record,spec,coverage):
    system=mapping_record['system'];edges={e['edge_id']:e for e in plan_graph['edges']}
    if len(mapping_record['plan_edges'])!=1:raise ValueError('diameter candidate evidence needs explicit single-edge scope')
    edge=edges[mapping_record['plan_edges'][0]];p=plan_doc.entitydb.get(spec['plan_text_handle']);i=iso_doc.entitydb.get(spec['iso_text_handle']);line=iso_doc.entitydb.get(spec['iso_pipe_handle'])
    if any(not e or e not in doc.modelspace() or e.dxftype()!='TEXT' or e.plain_text()!=spec[key] for e,doc,key in ((p,plan_doc,'plan_text'),(i,iso_doc,'iso_text'))):raise ValueError('native diameter observations changed')
    parse=lambda text:float(re.fullmatch(r'DN(\d+(?:\.\d+)?)(?:\(\d+(?:\.\d+)?\))?',text).group(1))
    pv,iv=parse(p.plain_text()),parse(i.plain_text())
    if pv<=0 or iv<=0 or edge.get('diameter_candidate_mm')!=pv or edge.get('diameter_candidate_status')!='source_scoped_inheritance_candidate_not_accepted':raise ValueError('unaccepted plan inheritance candidate differs')
    if not line or line.dxftype()!='LINE' or line not in iso_doc.modelspace() or line.dxf.layer!=('空调冷冻水供水' if system=='supply' else '空调冷冻水回水'):raise ValueError('native axis observation service differs')
    witnesses={w['source_handle'] for e in coverage['edges'] if e['edge_id'] in mapping_record['iso_edges'] for s in e['segments'] for w in s['witnesses'] if 'source_handle' in w}
    if line.dxf.handle not in witnesses:raise ValueError('axis observation pipe is outside the mapped source route')
    a,b=line.dxf.start,line.dxf.end;point=i.dxf.insert;dx=b.x-a.x;dy=b.y-a.y;den=dx*dx+dy*dy
    if den<=.0025:raise ValueError('axis observation pipe is degenerate')
    t=max(0,min(1,((point.x-a.x)*dx+(point.y-a.y)*dy)/den));distance=math.hypot(point.x-a.x-t*dx,point.y-a.y-t*dy)
    limit=spec.get('maximum_annotation_distance_drawing_units')
    if not isinstance(limit,(int,float)) or isinstance(limit,bool) or not 0<limit<=300 or distance>limit:raise ValueError('axis annotation is outside the scoped observation window')
    # An explicit nearby observation is preserved, not accepted as a DN binding.
    return dict(nominal_mm=None,status='candidate_disagreement_unresolved' if pv!=iv else 'candidate_agreement_not_assignment',
        plan_candidate=dict(nominal_mm=pv,text=p.plain_text(),handle=p.dxf.handle,point=list(p.dxf.insert),lineage=edge.get('diameter_candidate_lineage'),accepted=False),
        axis_observation=dict(nominal_mm=iv,text=i.plain_text(),handle=i.dxf.handle,point=list(i.dxf.insert),nearby_pipe_handle=line.dxf.handle,attribution='candidate_only'),
        selected_physical_diameter=False)

def attach(axis,mapping,plan,units,observations,source_hashes):
    out=copy.deepcopy(axis);edges={e['edge_id']:e for e in out['edges']};records=[]
    for index,record in enumerate(mapping['records'],1):
        metric=lengths(plan,mapping['evidence']['local']['plan']['coverage'],record,units);mapping_id=f'CV-{index:04d}'
        axis_rows={e['edge_id']:e for e in mapping['evidence']['local']['iso']['coverage']['edges']}
        for eid in record['iso_edges']:
            edge=edges[eid]
            if edge.get('system')!=record['system'] or snapshot(axis,record['iso_edges'])!=record['iso_snapshot']:raise ValueError('mapped axis local topology changed')
            if 'cross_view_attributes' in edge:raise ValueError('existing cross-view attributes need reconciliation')
            row=axis_rows[eid];vertical=[dict(segment_index=s['index'],points=[s['start'],s['end']],drawing_span_units=s['drawing_length'],physical_length_mm=None,
                inter_floor=False) for s in row['segments'] if abs(s['start'][0]-s['end'][0])<=.05 and abs(s['start'][1]-s['end'][1])>.05]
            edge['cross_view_attributes']=dict(mapping_id=mapping_id,status='partial_plan_attributes_source_checked',floor=record['floor'],system=record['system'],
                plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],source_hashes=source_hashes,
                horizontal_projection=dict(metric,edge_value_mm=metric['value_mm'] if len(record['iso_edges'])==1 else None,
                    allocation='whole_mapped_axis_edge_projection' if len(record['iso_edges'])==1 else 'route_total_only_not_allocated_to_each_axis_edge'),
                diameter=copy.deepcopy(observations[record['system']]),axis_vertical_drawing_strokes=vertical,
                whole_edge_physical_length_mm=None,equipment_connector_length_mm=None,physical_ports_verified=False,human_accepted=False)
        records.append(dict(mapping_id=mapping_id,system=record['system'],equipment_id=record['equipment_id'],plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],
            plan_horizontal_projection_mm=metric['value_mm'],diameter_status=observations[record['system']]['status'],whole_edge_physical_length_mm=None))
    out['crossViewAttributeFusion']=dict(status='partial_plan_projection_attributes_native_checked',source_hashes=source_hashes,records=records,
        local_graphs_remain_separate=True,metric_evidence=units,complete=False,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_cross_view_attribute_evidence')
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(axis.get('derivedEvidenceInvalidation')),
        reason='cross-view parameter evidence added; paths and local connectivity unchanged',recompute=['source_comparison','human_acceptance'],historical_annotations_preserved=True)
    return out,records

def compute(mapping_run,policy_path,devices):
    mapping=verify_mapping(mapping_run);receipt=load(Path(mapping_run)/'mapping-receipt.json');policy=load(policy_path)
    for key in ('plan_source','iso_source','plan_graph','iso_graph'):
        if policy[key+'_sha256']!=receipt['inputs'][key]['sha256']:raise ValueError('stale projection policy '+key)
    if sha(devices)!=receipt['inputs']['iso_devices']['sha256']:raise ValueError('canonical axis components differ from mapping')
    plan_source=receipt['inputs']['plan_source']['path'];iso_source=receipt['inputs']['iso_source']['path'];plan=load(receipt['inputs']['plan_graph']['path']);axis=load(receipt['inputs']['iso_graph']['path'])
    pd,_=read_source(plan_source);ad,_=read_source(iso_source);units=unit_evidence(pd,policy)
    observations={r['system']:diameter_candidates(pd,ad,plan,r,policy['diameter_observations'][r['system']],mapping['evidence']['local']['iso']['coverage']) for r in mapping['records']}
    source_hashes=dict(plan=sha(plan_source),isometric=sha(iso_source),plan_graph=receipt['inputs']['plan_graph']['sha256'],local_iso_graph=receipt['inputs']['iso_graph']['sha256'])
    out,records=attach(axis,mapping,plan,units,observations,source_hashes)
    return out,dict(records=records,parent_graph=receipt['inputs']['iso_graph'],mapping_sha256=sha(Path(mapping_run)/'mapping.json'),metric_evidence=units)

def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('attach_crossview_plan_attributes.py','native_plan_projection_lengths.py')}

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'attribute-fusion-audit.json')
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale cross-view fusion implementation')
    for name,item in audit['inputs'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale attribute fusion input '+name)
    inputs=audit['inputs'];mapping_run=Path(inputs['mapping_receipt']['path']).parent
    out,proof=compute(mapping_run,inputs['policy']['path'],inputs['devices']['path'])
    if (encode(out)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256']
        or (directory/'edge_device_instances.csv').read_bytes()!=Path(inputs['devices']['path']).read_bytes() or proof['records']!=audit['records']):raise ValueError('cross-view attribute native replay differs')
    return audit

def main():
    p=argparse.ArgumentParser()
    for name in ('mapping-run','policy','devices','parent-report','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--check-parent',action='store_true');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    out,audit=compute(a.mapping_run,a.policy,a.devices)
    inputs=dict(mapping_receipt=a.mapping_run/'mapping-receipt.json',mapping=a.mapping_run/'mapping.json',policy=a.policy,devices=a.devices,parent_report=a.parent_report)
    a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(out));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in inputs.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),hil_ready=False)
    (a.output/'attribute-fusion-audit.json').write_bytes(encode(audit))
    if a.check_parent:
        import sys
        owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
        sys.path.insert(0,str(owner));from source_comparison_gate import check
        result=check(load(a.parent_report),audit['output_graph_sha256'],a.output,a.output/'graph_with_edges.json')
        (a.output/'source-comparison-gate.json').write_bytes(encode(result))
        if result['errors']:raise ValueError('cross-view attribute source comparison failed: '+str(result['errors']))
    print(json.dumps(dict(status='partial_plan_attributes_attached',mapped_axis_edges=sum(len(r['iso_edges']) for r in audit['records']),records=audit['records'],hil_ready=False)))

if __name__=='__main__':main()
