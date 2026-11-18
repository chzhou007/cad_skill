"""Add plan projection evidence from mutually checked source correspondences.

Preserves previously confirmed attributes; local DN observations never become
accepted edge-wide values and unallocated route totals are not duplicated.
"""
import argparse,copy,json,math,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_source_checked_crossview_paths import verify_output as verify_mapping,selected_snapshot
from attach_crossview_plan_attributes import verify_output as verify_parent
from native_plan_projection_lengths import unit_evidence,lengths
from source_checked_plan_path_coverage import audit as audit_paths
from native_line_path_evidence import _on,LAYERS
from source_readability import read_source
from confirmed_detail_projection import projection as checked_projection,has_detail_scope,ALLOCATION as DETAIL_ALLOCATION


def metric_context(doc,policy,plan,mapping):
    detail_scopes=[has_detail_scope(plan,r) for r in mapping['records']]
    allow_detail=policy.get('allow_confirmed_detail_topology_only',False)
    if any(detail_scopes) and allow_detail is not True:raise ValueError('detail mapping requires explicit nonmetric policy')
    units=(dict(status='not_applied_to_confirmed_detail_drawing',physical_units_applied=False) if detail_scopes and all(detail_scopes) else unit_evidence(doc,policy))
    return units,allow_detail


def native_local_diameters(doc,plan,record,coverage):
    edges={e['edge_id']:e for e in plan['edges']};witnesses={w['source_handle'] for r in coverage['edges'] if r['edge_id'] in record['plan_edges'] for s in r['segments'] for w in s['witnesses'] if w['scope']=='modelspace'};observations=[]
    for eid in record['plan_edges']:
        for obs in (edges[eid].get('pipe_diameter') or {}).get('observations',[]):
            h=(obs.get('text') or {}).get('handle');entity=doc.entitydb.get(h);line=doc.entitydb.get(obs.get('source_line_handle'))
            if (entity is None or entity not in doc.modelspace() or entity.dxftype()!='TEXT' or entity.plain_text()!=obs['text']['text']
                or line is None or line.dxftype()!='LINE' or line.dxf.handle not in witnesses or line.dxf.layer!=LAYERS[record['system']]
                or obs.get('status')!='native_source_local_observation'):raise ValueError('plan DN observation no longer has native route evidence')
            match=re.fullmatch(r'DN(\d+(?:\.\d+)?)(?:\((\d+(?:\.\d+)?)\))?',entity.plain_text())
            if not match or float(match[1])!=obs['nominal_mm'] or not _on(obs['point'],list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05):raise ValueError('local DN source value/position differs')
            observations.append(dict(nominal_mm=obs['nominal_mm'],text=entity.plain_text(),handle=h,source_line_handle=line.dxf.handle,point=obs['point'],
                plan_edge=eid,scope='local_source_observation',accepted=False,parenthesized_source_value=match[2],physical_length_from_parentheses=False))
    return dict(nominal_mm=None,status='native_local_plan_annotation_not_edgewide' if observations else 'plan_diameter_scope_unresolved',
        plan_candidate=observations[0] if len(observations)==1 else None,plan_observations=observations,axis_observation=None,selected_physical_diameter=False)


def attach(parent,mapping,plan,coverage,units,diameters,source_hashes,mapping_hash,allow_detail=False):
    out=copy.deepcopy(parent);edges={e['edge_id']:e for e in out['edges']};proof=[];claimed=set()
    for record in mapping['records']:
        metric=checked_projection(plan,coverage,record,units,source_hashes,allow_detail=allow_detail)
        if selected_snapshot(parent,record['iso_edges'])!=record['iso_snapshot']:raise ValueError('selected axis local route changed before attribute attachment')
        for eid in record['iso_edges']:
            edge=edges[eid]
            if eid in claimed or 'cross_view_attributes' in edge:raise ValueError('mapping overlaps an existing or repeated attribute owner')
            claimed.add(eid);projection=copy.deepcopy(metric)
            projection.update(edge_value_mm=metric['value_mm'] if len(record['iso_edges'])==1 else None,
                allocation='whole_mapped_axis_edge_projection' if len(record['iso_edges'])==1 else 'route_total_only_not_allocated_to_each_axis_edge')
            if metric['value_mm'] is None:projection['allocation']=DETAIL_ALLOCATION
            vertical=[dict(path_index=pi,segment_index=si,points=[a,b],drawing_span_units=math.dist(a,b),physical_length_mm=None,inter_floor=False,
                classification='same_floor_drawing_stroke_not_inter_floor_proof')
                for pi,path in enumerate(edge.get('attribute_paths',[])) for si,(a,b) in enumerate(zip(path,path[1:])) if abs(a[0]-b[0])<=.05 and abs(a[1]-b[1])>.05]
            edge['cross_view_attributes']=dict(status='partial_plan_attributes_source_checked',mapping_id=record['mapping_id'],mapping_basis='native_source_and_main_branch_order',
                mapping_kind=record['kind'],mapping_evidence_sha256=mapping_hash,floor=record['floor'],system=record['system'],plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],
                source_hashes=source_hashes,horizontal_projection=projection,diameter=diameters[record['mapping_id']],axis_vertical_drawing_strokes=vertical,
                whole_edge_physical_length_mm=None,equipment_connector_length_mm=None,physical_ports_verified=False,human_accepted=False)
        proof.append(dict(mapping_id=record['mapping_id'],kind=record['kind'],system=record['system'],plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],plan_horizontal_projection_mm=metric['value_mm'],diameter_status=diameters[record['mapping_id']]['status']))
    out['sourceCheckedCrossViewAttributeFusion']=dict(status='source_checked_plan_projection_attributes_hil_pending',mapping_sha256=mapping_hash,records=proof,
        prior_attributes_preserved=True,expert_confirmation_claimed=False,physical_ports_verified=False,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_source_checked_crossview_attributes')
    return out,proof


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','parent_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('source attribute input differs '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':raise ValueError('source mapping receipt outside expected directory')
    mapping=verify_mapping(folder);mapping_receipt=load(paths['mapping_receipt']);parent_audit=verify_parent(Path(paths['parent_graph']).parent)
    if parent_audit['output_graph_sha256']!=sha(paths['parent_graph']) or parent_audit['parent_graph']['sha256']!=mapping['iso_graph_sha256']:raise ValueError('historical attributes and source mapping use different local axis graphs')
    if sha(paths['devices'])!=parent_audit['inputs']['devices']['sha256']:raise ValueError('canonical component inventory differs')
    inputs=mapping_receipt['inputs'];plan=load(inputs['plan_graph']['path']);doc,preflight=read_source(inputs['plan_source']['path'])
    ids=[eid for r in mapping['records'] for eid in r['plan_edges']]
    coverage=audit_paths(doc,plan,dict(source_sha256=mapping['source_sha256']['plan'],graph_sha256=mapping['plan_graph_sha256'],edges=ids),mapping['source_sha256']['plan'],mapping['plan_graph_sha256'])
    units,allow_detail=metric_context(doc,policy,plan,mapping)
    observations={r['mapping_id']:native_local_diameters(doc,plan,r,coverage) for r in mapping['records']}
    sources=dict(plan=mapping['source_sha256']['plan'],isometric=mapping['source_sha256']['iso'],plan_graph=mapping['plan_graph_sha256'],local_iso_graph=mapping['iso_graph_sha256'])
    graph,records=attach(load(paths['parent_graph']),mapping,plan,coverage,units,observations,sources,sha(paths['mapping']),allow_detail=allow_detail)
    proof=dict(records=records,source_preflight=preflight,metric_evidence=units,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])))
    if policy.get('diameter_evidence_sha256') or paths.get('diameter_evidence'):
        for key in ('diameter_evidence','diameter_receipt'):
            if key not in paths or sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('single-group plan DN evidence missing/stale '+key)
        from plan_pipe_diameter_scopes import verify_output as verify_DN
        from fuse_plan_DN_scopes import apply as fuse_DN
        directory=Path(paths['diameter_evidence']).resolve().parent
        if Path(paths['diameter_evidence']).resolve()!=directory/'plan-DN-scopes.json' or Path(paths['diameter_receipt']).resolve()!=directory/'plan-DN-scope-receipt.json':raise ValueError('plan DN evidence outside canonical stage')
        evidence=verify_DN(directory)
        if evidence['graph_sha256']!=mapping['plan_graph_sha256'] or evidence['source_sha256']!=mapping['source_sha256']['plan'] or evidence['local_graph_mutated'] is not False or evidence['human_accepted'] is not False:raise ValueError('plan DN scope differs from mapped source')
        graph,proof['plan_DN_scope_fusion']=fuse_DN(graph,mapping,plan,evidence,sha(paths['diameter_evidence']),policy.get('isometric_horizontal_directions_degrees',[]))
    return graph,proof


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('confirmed_detail_projection.py','attach_source_checked_plan_attributes.py','match_source_checked_crossview_paths.py','native_plan_projection_lengths.py','native_path_coverage_audit.py','source_checked_plan_path_coverage.py','source_reviewed_circle_branch_evidence.py','plan_pipe_diameter_scopes.py','fuse_plan_DN_scopes.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'source-attribute-fusion-audit.json')
    if audit.get('mode')=='batch_source_checked_mapping_groups':
        from attach_source_checked_plan_attribute_groups import verify_output as verify_groups
        return verify_groups(directory)
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale source attribute implementation')
    for spec in audit['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('source attribute dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};result,proof=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('source plan attribute replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('component inventory changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','parent-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--diameter-run',type=Path)
    args=parser.parse_args();paths=dict(mapping=args.mapping_run/'mapping.json',mapping_receipt=args.mapping_run/'source-mapping-receipt.json',parent_graph=args.parent_graph,devices=args.devices,policy=args.policy)
    if args.diameter_run:paths.update(diameter_evidence=args.diameter_run/'plan-DN-scopes.json',diameter_receipt=args.diameter_run/'plan-DN-scope-receipt.json')
    if args.output.exists():raise FileExistsError(args.output)
    graph,audit=compute(paths,load(args.policy));args.output.mkdir(parents=True);(args.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(args.devices,args.output/'edge_device_instances.csv')
    audit.update(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(args.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (args.output/'source-attribute-fusion-audit.json').write_bytes(encode(audit));print(json.dumps(dict(records=len(audit['records']),added_axis_edges=sum(len(r['iso_edges']) for r in audit['records']),human_accepted=False)))

if __name__=='__main__':main()
