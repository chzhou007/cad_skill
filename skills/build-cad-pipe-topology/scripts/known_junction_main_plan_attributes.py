"""Plan DN/XY for source-replayed direct mains, with component DN kept separate."""
import argparse
import copy
import math
import re
from pathlib import Path

from confirm_crossview_paths import encode,load,sha
from match_known_junction_direct_mains import verify_output as verify_mapping,MODE as MAPPING_MODE
from plan_pipe_diameter_scopes import catalog,guard_leader_bridges
from qualified_inline_DN_evidence import collect as component_labels
from pipe_annotation_attributes import direct_diameters,parse_dn_annotation
from source_direct_dn_evidence import collect as scalar_evidence
from native_equipment_body import point_segment_distance
from native_line_path_evidence import LAYERS,_on
from through_source_DN_inheritance import infer
from native_plan_projection_lengths import unit_evidence,lengths
from anchored_floor_main_plan_attributes import inline_projection
from source_readability import read_source

MODE='known_junction_main_plan_DN_XY_v1'


def read_diameters(doc,graph,scope,origin,source_hash,graph_hash,junctions):
    texts,inventory=catalog(doc,graph,sorted(scope),source_hash,graph_hash)
    qualified=None;strokes=[]
    if origin.get('source_sha256')!=source_hash:raise ValueError('Annotation origin belongs to another source')
    if origin.get('qualified_component_DN'):
        spec=copy.deepcopy(origin['qualified_component_DN'])
        if spec.get('source_sha256')!=source_hash:raise ValueError('Component DN origin source differs')
        # Rebind only the input graph for an actual native re-read. No previous
        # component ownership or accepted result is copied onto the child.
        spec['graph_sha256']=graph_hash
        qualified=component_labels(doc,graph,spec,source_hash,graph_hash)
        consumed=set(qualified['consumed_DN_text_handles'])
        texts=[t for t in texts if t['handle'] not in consumed]
        strokes=qualified['consumed_leader_handles']
    edges={e['edge_id']:e for e in graph['edges']};paths=[p for eid in scope for p in edges[eid]['attribute_paths']]
    guard_leader_bridges(doc,texts,paths,strokes)
    layers={t['layer'] for t in texts}
    assigned,pending=direct_diameters(texts,graph['edges'],set(),layers)
    if any(scope.intersection(r['candidate_edge_ids']) for r in pending):raise ValueError('Ambiguous visible pipe DN in selected direct mains')
    unparsed=[dict(t,text='DN1') for t in texts if re.search('DN',t['text'],re.I) and parse_dn_annotation(t['text']) is None]
    ua,up=direct_diameters(unparsed,graph['edges'],set(),layers)
    if any(scope.intersection(r['candidate_edge_ids']) for r in ua+up):raise ValueError('Unparsed pipe DN requires its dedicated native reader')
    bound={r['text']['handle'] for r in assigned}
    for text in texts:
        if re.search('DN',text['text'],re.I) and text['handle'] not in bound and any(point_segment_distance(text['position'],a,b)<=3*text['height'] for p in paths for a,b in zip(p,p[1:])):
            raise ValueError('Unattributed visible DN near selected main')
    observations=[]
    for row in assigned:
        if row['edge_id'] not in scope:continue
        if row['text']['handle'] in inventory['F_text_handles']:
            raise ValueError('Selected main has an ordered F label; use the existing native F reader')
        edge=edges[row['edge_id']];point=row['point']
        native=[doc.entitydb.get(h) for h in edge.get('source_handles',[])]
        hits=[e for e in native if e is not None and e.dxftype()=='LINE' and e in doc.modelspace()
              and e.dxf.layer==LAYERS[edge['system']] and _on(point,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
        if len(hits)!=1:raise ValueError('Scalar annotation lacks one native selected pipe LINE')
        spec=dict(text_handle=row['text']['handle'],edge_id=edge['edge_id'],source_line_handle=hits[0].dxf.handle,expected_text=row['text']['text'])
        proof=scalar_evidence(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,
            text_layers=sorted(layers),selections=[spec]),source_hash,graph_hash)['observations'][0]
        observations.append(dict(edge_id=edge['edge_id'],nominal_mm=proof['nominal_mm'],evidence_id='source:'+spec['text_handle'],source_evidence=proof))
    inherited=infer(graph,[{k:o[k] for k in ('edge_id','nominal_mm','evidence_id')} for o in observations],scope,junctions,source_hash,graph_hash)
    return inherited,dict(source_annotation_inventory=inventory,qualified_component_DN=qualified,
        direct_pipe_observations=observations,qualified_component_values_used_as_pipe_seeds=False,
        scalar_mode_only_F_overlap_rejected=True)


def metric_rows(graph,mapping,units,diameters):
    dn={r['edge_id']:r for r in diameters['records']};coverage=mapping['native_path_evidence']['plan']
    lines=coverage.get('native_LINE_paths');inline={r['edge_id']:r for r in coverage.get('native_inline_paths',{}).get('records',[])}
    rows=[]
    for record in mapping['records']:
        eid=record['plan_edges'][0]
        metric=inline_projection(graph,inline[eid],record,units) if eid in inline else lengths(graph,lines,record,units)
        rows.append(dict(mapping_id=record['mapping_id'],kind=record['kind'],floor=record['floor'],system=record['system'],
            plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],diameter=copy.deepcopy(dn[eid]),horizontal_projection=metric,
            whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,physical_ports_verified=False,human_accepted=False))
    return rows


def check_result(data):
    if data.get('mode')!=MODE or data.get('status')!='native_direct_main_plan_DN_XY_source_checked_not_fused' or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','human_accepted')):
        raise ValueError('Unsupported direct-main plan attribute state')
    rows=data['records'];ids=set();axis=set()
    if not rows:raise ValueError('Missing direct-main attributes')
    for row in rows:
        if len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1 or ids.intersection(row['plan_edges']) or axis.intersection(row['iso_edges']):
            raise ValueError('Repeated or unsupported direct-main attribute writer')
        if row.get('whole_axis_DN_selected') is not False or row.get('whole_axis_physical_length_mm') is not None or row.get('human_accepted') is not False or row.get('physical_ports_verified') is not False:
            raise ValueError('Plan evidence cannot promote whole-axis physical values or review')
        dn=row['diameter'];metric=row['horizontal_projection']
        if dn.get('edge_id')!=row['plan_edges'][0] or dn.get('system')!=row['system'] or dn.get('human_accepted') is not False or metric.get('installed_whole_edge_length_mm') is not None:
            raise ValueError('Plan diameter or length scope differs')
        for value in (dn['nominal_mm'],metric['value_mm']):
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):
                raise ValueError('Unknown parameters stay null; known DN/XY must be finite and positive')
        ids.update(row['plan_edges']);axis.update(row['iso_edges'])
    return dict(status='pending',source_replay='passed',mapped_plan_attribute_scopes=len(rows),
        known_DN_scopes=sum(r['diameter']['nominal_mm'] is not None for r in rows),
        measured_plan_XY_scopes=sum(r['horizontal_projection']['value_mm'] is not None for r in rows),
        inline_interior_length_unknown=sum(r['horizontal_projection'].get('status')=='native_plan_pipe_XY_inline_interiors_unknown' for r in rows),
        whole_axis_physical_values_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Complete-parent fusion, source comparison, viewer and HIL remain separate'])


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','annotation_origin','metric_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('Direct-main attribute dependency changed: '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':raise ValueError('Canonical direct-main receipt required')
    mapping=verify_mapping(folder)
    if mapping['mode']!=MAPPING_MODE:raise ValueError('Native direct-main mapping owner required')
    local=load(paths['mapping_receipt'])['local_inputs'];sp=local['plan_source'];gp=local['plan_graph']
    if sha(sp['path'])!=mapping['source_sha256']['plan'] or sha(gp['path'])!=mapping['plan_graph_sha256']:
        raise ValueError('Direct-main plan source or graph differs')
    graph=load(gp['path']);doc,preflight=read_source(sp['path'])
    scope={r['plan_edges'][0] for r in mapping['records']}
    inherited,annotation=read_diameters(doc,graph,scope,load(paths['annotation_origin']),sp['sha256'],gp['sha256'],mapping['native_T_evidence']['plan'])
    units=unit_evidence(doc,load(paths['metric_policy']));rows=metric_rows(graph,mapping,units,inherited)
    data=dict(mode=MODE,status='native_direct_main_plan_DN_XY_source_checked_not_fused',records=rows,
        source_sha256=sp['sha256'],graph_sha256=gp['sha256'],mapping_sha256=sha(paths['mapping']),
        source_preflight=preflight,diameter_inheritance=inherited,annotation_evidence=annotation,metric_evidence=units,
        local_graphs_mutated=False,physical_values_fused=False,human_accepted=False)
    check_result(data)
    for key in ('mapping','mapping_receipt','annotation_origin','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('Attribute input changed during native replay')
    for item in local.values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Local source input changed during attributes')
    return data


def implementation_hashes():
    from match_known_junction_direct_mains import implementation_hashes as parent_hashes
    from anchored_floor_main_plan_attributes import implementation_hashes as metric_hashes
    import qualified_inline_DN_evidence
    result=parent_hashes();result.update(metric_hashes())
    result[Path(__file__).name]=sha(__file__)
    result['qualified_inline_DN_evidence.py']=sha(qualified_inline_DN_evidence.__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'known-main-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('Direct-main attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Direct-main attribute input changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};data=compute(paths,load(paths['policy']))
    if encode(data)!=(directory/'attributes.json').read_bytes() or sha(directory/'attributes.json')!=receipt['output_sha256']:
        raise ValueError('Direct-main attribute independent native replay differs')
    return data


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','annotation-origin','metric-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',
        annotation_origin=a.annotation_origin,metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    data=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'attributes.json';target.write_bytes(encode(data))
    (a.output/'known-main-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={key:dict(path=str(value.resolve()),sha256=sha(value)) for key,value in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(check_result(data),flush=True)


if __name__=='__main__':main()
