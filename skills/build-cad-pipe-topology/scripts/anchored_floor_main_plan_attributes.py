"""Replayed whole-floor main DN scopes and source-drawn plan XY lengths.

Every visible scalar/F annotation is examined before through-only inheritance.
Conflicts remain unknown; inline marker spans never become pipe lengths.
"""
import argparse,copy,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from match_anchored_floor_main_network import verify_output as verify_mapping,implementation_hashes as mapping_hashes,MODE as MAPPING_MODE
from native_inline_joint_path_coverage import verify_output as verify_inline
from native_path_coverage_audit import audit as audit_paths
from plan_pipe_diameter_scopes import catalog,guard_leader_bridges
from pipe_annotation_attributes import direct_diameters,parse_dn_annotation
from native_equipment_body import point_segment_distance
from native_line_path_evidence import LAYERS,_on
from native_line_f_diameter_evidence import collect as collect_F
from source_direct_dn_evidence import collect as collect_scalar
from through_source_DN_inheritance import infer
from native_plan_projection_lengths import unit_evidence,lengths

MODE='anchored_floor_main_plan_DN_XY_attributes_v1'


def observe_annotations(doc,graph,scope,frames,source_hash,graph_hash):
    texts,inventory=catalog(doc,graph,sorted(scope),source_hash,graph_hash)
    F=collect_F(doc,graph,frames,source_hash,graph_hash) if frames else dict(frames=[])
    consumed={h for f in F['frames'] for h in f['text_handles']};strokes={h for f in F['frames'] for h in f['stroke_handles']}
    scalar=[t for t in texts if t['handle'] not in consumed];layers={t['layer'] for t in scalar};edges={e['edge_id']:e for e in graph['edges']}
    paths=[p for eid in scope for p in edges[eid]['attribute_paths']];guard_leader_bridges(doc,scalar,paths,strokes)
    assigned,pending=direct_diameters(scalar,graph['edges'],set(),layers)
    if any(scope.intersection(r['candidate_edge_ids']) for r in pending):raise ValueError('ambiguous visible DN overlaps full main scope')
    unparsed=[dict(t,text='DN1') for t in scalar if re.search('DN',t['text'],re.I) and parse_dn_annotation(t['text']) is None]
    ua,up=direct_diameters(unparsed,graph['edges'],set(),layers)
    if any(scope.intersection(r['candidate_edge_ids']) for r in ua+up):raise ValueError('compound/system-qualified DN needs its dedicated source domain')
    bound={r['text']['handle'] for r in assigned};observations=[]
    for t in scalar:
        if re.search('DN',t['text'],re.I) and t['handle'] not in bound and any(point_segment_distance(t['position'],a,b)<=3*t['height'] for p in paths for a,b in zip(p,p[1:])):
            raise ValueError('unattributed visible DN near full main paths')
    for row in assigned:
        if row['edge_id'] not in scope:continue
        edge=edges[row['edge_id']];point=row['point'];native=[doc.entitydb.get(h) for h in edge.get('source_handles',[])]
        hits=[e for e in native if e is not None and e.dxftype()=='LINE' and e in doc.modelspace() and e.dxf.layer==LAYERS[edge['system']] and _on(point,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
        if len(hits)!=1:raise ValueError('native scalar DN source LINE is not unique')
        spec=dict(text_handle=row['text']['handle'],edge_id=edge['edge_id'],source_line_handle=hits[0].dxf.handle,expected_text=row['text']['text'])
        proof=collect_scalar(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=sorted(layers),selections=[spec]),source_hash,graph_hash)['observations'][0]
        observations.append(dict(evidence_id='source:'+spec['text_handle'],edge_id=edge['edge_id'],nominal_mm=proof['nominal_mm'],kind='native_scalar',source_evidence=proof))
    for frame in F['frames']:
        for binding in frame['bindings']:
            if binding['edge_id'] in scope:observations.append(dict(evidence_id='source:'+binding['source_text']['handle'],edge_id=binding['edge_id'],nominal_mm=binding['nominal_mm'],kind='native_ordered_F',source_evidence=copy.deepcopy(binding)))
    return observations,dict(source_annotation_inventory=inventory,line_F_evidence=F,visible_DN_texts=[t for t in texts if re.search('DN',t['text'],re.I)],
        scalar_scope_annotations=[r['source_evidence']['source_text']['handle'] for r in observations if r['kind']=='native_scalar'],annotation_scope_complete_under_declared_native_mode=True)


def inline_projection(graph,proof,record,units):
    if len(record['plan_edges'])!=1 or record['plan_edges'][0]!=proof.get('edge_id'):raise ValueError('inline metric mapping scope differs')
    edge=next(e for e in graph['edges'] if e['edge_id']==proof['edge_id'])
    if proof.get('status')!='native_pipe_and_inline_joint_chain_source_checked' or proof.get('original_attribute_paths')!=edge['attribute_paths'] or proof.get('joint_spans_excluded_from_pipe_length') is not True:
        raise ValueError('independently replayed original inline paths required')
    if proof.get('physical_length_mm') is not None or not proof.get('joints'):raise ValueError('inline span cannot supply physical length')
    pieces=[];seen=set()
    for row in proof['native_path_proofs']:
        pi=row['original_path_index']
        if isinstance(pi,bool) or not isinstance(pi,int) or pi in seen or not 0<=pi<len(edge['attribute_paths']):raise ValueError('inline source path index differs')
        seen.add(pi);path=edge['attribute_paths'][pi];audit=copy.deepcopy(row['coverage']);segments=audit['edges'][0]['segments']
        if len(segments)!=len(path)-1 or any(s['index']!=i or [s['start'],s['end']]!=path[i:i+2] for i,s in enumerate(segments)):
            raise ValueError('inline audit does not cover every original source segment')
        allowed=[]
        for segment in segments:
            if segment['status']=='single_source_line_covers':allowed.append(segment);continue
            a,b=segment['start'],segment['end'];matches=[j for j in proof['joints'] if any(math.dist(a,x[:2])<=.05 and math.dist(b,y[:2])<=.05 for x,y in (j['contact_points_wcs'],list(reversed(j['contact_points_wcs']))))]
            if segment['status']!='no_witness_in_scoped_search' or len(matches)!=1:raise ValueError('unknown inline metric gap is not a qualified marker span')
        audit['edges'][0]['segments']=allowed
        if not allowed:continue
        private=dict(graph,edges=[dict(edge,attribute_paths=[path])]);metric=lengths(private,audit,record,units)
        for piece in metric['pieces']:piece['path_index']=pi;pieces.append(piece)
    if seen!=set(range(len(edge['attribute_paths']))) or not pieces:raise ValueError('inline path coverage incomplete')
    if len({(r['plan_edge'],r['path_index'],r['segment_index']) for r in pieces})!=len(pieces):raise ValueError('inline metric segment counted twice')
    return dict(status='native_plan_pipe_XY_inline_interiors_unknown',value_mm=sum(r['length_mm'] for r in pieces),pieces=pieces,
        installed_whole_edge_length_mm=None,unshown_connection_length_mm=None,inline_joint_interior_length_mm=None,joint_graphic_spans_added=False,
        scope='native source-drawn floor-plan pipe XY only; all inline marker spans excluded')


def preserve_known_main_values(snapshot,rows,floor):
    by={r['plan_edges'][0]:r for r in rows};known={}
    for edge in snapshot['edges']:
        attr=edge.get('cross_view_attributes',{})
        if attr.get('floor')==floor and attr.get('mapping_kind')=='main_between_equipment_branches':
            known[attr['plan_edges'][0]]=(attr['diameter']['plan_drawn_nominal_mm'],attr['horizontal_projection']['value_mm'])
        for attr in edge.get('plan_segment_attributes',[]):
            if attr.get('floor')==floor and attr.get('whole_local_edge'):known[attr['plan_edges'][0]]=(attr['nominal_mm'],attr['horizontal_projection']['value_mm'])
    comparisons=[]
    for eid,(dn,mm) in known.items():
        current=by.get(eid)
        if not current or current['diameter']['nominal_mm']!=dn or not math.isclose(current['horizontal_projection']['value_mm'],mm,abs_tol=.0001,rel_tol=0):
            raise ValueError('previously known main DN or XY length changed '+eid)
        comparisons.append(dict(plan_edge=eid,nominal_mm=dn,plan_XY_mm=mm,current_values_identical=True))
    return comparisons


def frontier_annotation_domain(graph,eid,Ts,observations):
    """Read only the T-contiguous source piece, never cross an unaudited joint."""
    edge=next(e for e in graph['edges'] if e['edge_id']==eid);nodes={n['node_id']:n for n in graph['nodes']}
    ends=[edge[k] for k in ('start_node_id','end_node_id') if edge[k] in Ts]
    if len(ends)!=1:raise ValueError('one checked T required for annotation frontier')
    node=nodes[ends[0]];point=[node['x'],node['y']]
    selected=[(i,p) for i,p in enumerate(edge['attribute_paths']) if min(math.dist(point,p[0]),math.dist(point,p[-1]))<=.05]
    if len(selected)!=1:raise ValueError('annotation frontier has no unique T-contiguous source path')
    pi,path=selected[0];seeds=[r for r in observations if r['edge_id']==eid]
    if not seeds:raise ValueError('unlabelled annotation frontier')
    for row in seeds:
        proof=row['source_evidence'];projection=proof.get('graph_projection')
        if row['kind']!='native_scalar' or projection is None or not any(_on(projection,a,b,.05) for a,b in zip(path,path[1:])):
            raise ValueError('annotation seed requires unverified frontier span or another reader')
    private=copy.deepcopy(graph);target=next(e for e in private['edges'] if e['edge_id']==eid);target['attribute_paths']=[copy.deepcopy(path)]
    return private,dict(edge_id=eid,T_node_id=ends[0],original_path_index=pi,scope_points=copy.deepcopy(path),
        excluded_original_path_indices=[i for i in range(len(edge['attribute_paths'])) if i!=pi],
        scope='native_T_contiguous_annotation_feed_only_not_whole_frontier_edge',whole_frontier_DN_verified=False,
        whole_frontier_physical_length_mm=None,original_graph_mutated=False)


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','F_origin','metric_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('floor main attribute input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':raise ValueError('noncanonical floor main correspondence')
    mapping=verify_mapping(folder)
    if mapping.get('mode')!=MAPPING_MODE:raise ValueError('source-checked complete floor main mapping required')
    inputs=load(paths['mapping_receipt'])['local_inputs'];sp=Path(inputs['plan_source']['path']);gp=Path(inputs['plan_graph']['path'])
    if sha(gp)!=mapping['plan_graph_sha256'] or sha(sp)!=mapping['source_sha256']['plan']:raise ValueError('current floor source mapping version differs')
    doc,preflight=read_source(sp);graph=load(gp);mains={r['plan_edges'][0] for r in mapping['records']};frontiers=set(policy.get('annotation_feed_frontiers',[]));by_edge={e['edge_id']:e for e in graph['edges']};Ts=set(mapping['evidence']['structure']['node_mapping'])
    if frontiers&mains or not frontiers<=set(by_edge) or any(sum(by_edge[e][k] in Ts for k in ('start_node_id','end_node_id'))!=1 for e in frontiers):raise ValueError('annotation frontier must stop outside the checked T network')
    scope=mains|frontiers;origin=load(paths['F_origin'])
    if origin.get('source_sha256')!=sha(sp) or origin.get('graph_sha256')!=sha(gp):raise ValueError('historical F configuration belongs to another local source')
    frames=[f for g in origin.get('groups',[]) for f in g.get('line_F_frames',[])]
    observations,annotation=observe_annotations(doc,graph,scope,frames,sha(sp),sha(gp))
    reading_graph=copy.deepcopy(graph);frontier_proofs=[]
    for eid in sorted(frontiers):
        reading_graph,domain=frontier_annotation_domain(reading_graph,eid,Ts,observations)
        proof=audit_paths(doc,reading_graph,dict(source_sha256=sha(sp),graph_sha256=sha(gp),edges=[eid]),sha(sp),sha(gp))
        if any(s['status']!='single_source_line_covers' for row in proof['edges'] for s in row['segments']):raise ValueError('DN frontier seed-to-T domain lacks native LINE coverage')
        frontier_proofs.append(dict(domain,coverage=proof))
    inherited=infer(reading_graph,[{k:r[k] for k in ('edge_id','nominal_mm','evidence_id')} for r in observations],scope,mapping['evidence']['native_T_proofs']['plan'],sha(sp),sha(gp))
    for row in inherited['records']:
        if row['edge_id'] in frontiers:row['partial_frontier_domain']=next(p for p in frontier_proofs if p['edge_id']==row['edge_id'])
    dn={r['edge_id']:r for r in inherited['records']};metric_policy=load(paths['metric_policy']);units=unit_evidence(doc,metric_policy)
    inline_path=Path(load(paths['mapping_receipt'])['inputs']['plan_inline']['path']);inline=verify_inline(inline_path.parent)
    if inline['source_sha256']!=sha(sp) or inline['graph_sha256']!=sha(gp):raise ValueError('inline paths belong to another plan graph')
    joint_by={r['edge_id']:r for r in inline['records']};coverage={}
    for eid in sorted(mains):
        if eid in joint_by:continue
        proof=mapping['evidence']['main_path_coverage']['plan'][eid]['evidence']
        if any(s['status']!='single_source_line_covers' for row in proof['edges'] for s in row['segments']):raise ValueError('DN propagation path lacks complete native LINE/inline coverage')
        coverage[eid]=proof
    rows=[]
    for mapped in mapping['records']:
        eid=mapped['plan_edges'][0]
        metric=inline_projection(graph,joint_by[eid],mapped,units) if eid in joint_by else lengths(graph,coverage[eid],mapped,units)
        rows.append(dict(mapping_id=mapped['mapping_id'],floor=mapped['floor'],system=mapped['system'],plan_edges=mapped['plan_edges'],iso_edges=mapped['iso_edges'],
            diameter=copy.deepcopy(dn[eid]),horizontal_projection=metric,inline_interiors_unknown=eid in joint_by,
            installed_whole_edge_length_mm=None,physical_ports_verified=False,human_accepted=False))
    protected=mapping['evidence'].get('preserved_floor_attributes')
    if not protected or sha(protected['source_snapshot']['path'])!=protected['source_snapshot']['sha256']:raise ValueError('preserved floor attribute snapshot changed')
    prior=preserve_known_main_values(load(protected['source_snapshot']['path']),rows,mapping['floor'])
    result=dict(mode=MODE,status='source_checked_floor_main_plan_attributes_unresolved_DN_retained',floor=mapping['floor'],mapping_sha256=sha(paths['mapping']),
        source_sha256=dict(plan=sha(sp),iso=mapping['source_sha256']['iso']),graph_sha256=dict(plan=sha(gp),iso=mapping['iso_graph_sha256']),source_preflight=preflight,
        records=rows,source_annotation_evidence=annotation,direct_observations=observations,DN_inheritance=inherited,annotation_feed_domains=frontier_proofs,unit_evidence=units,preserved_main_value_comparisons=prior,
        known_DN_records=sum(r['diameter']['nominal_mm'] is not None for r in rows),unresolved_DN_records=sum(r['diameter']['nominal_mm'] is None for r in rows),
        inline_length_incomplete_records=sum(r['inline_interiors_unknown'] for r in rows),local_graphs_mutated=False,physical_values_fused=False,human_accepted=False,hil_ready=False)
    for key in ('mapping','mapping_receipt','F_origin','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('attribute dependency changed during native replay '+key)
    if sha(gp)!=mapping['plan_graph_sha256'] or sha(sp)!=mapping['source_sha256']['plan']:raise ValueError('plan input changed during attributes')
    return result


def implementation_hashes():
    result=mapping_hashes()
    for name in ('anchored_floor_main_plan_attributes.py','through_source_DN_inheritance.py','native_plan_projection_lengths.py','plan_pipe_diameter_scopes.py','native_line_f_diameter_evidence.py','source_direct_dn_evidence.py','pipe_annotation_attributes.py','native_equipment_body.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'floor-main-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('floor main attribute implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('floor main attribute dependency changed')
    paths={k:r['path'] for k,r in receipt['inputs'].items()};expected=compute(paths,load(paths['policy']))
    if encode(expected)!=(directory/'attributes.json').read_bytes() or sha(directory/'attributes.json')!=receipt['output_sha256']:raise ValueError('floor main attribute native replay differs')
    return expected


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','F-origin','metric-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',F_origin=a.F_origin,metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'attributes.json';target.write_bytes(encode(result))
    (a.output/'floor-main-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(records=len(result['records']),known_DN=result['known_DN_records'],unresolved_DN=result['unresolved_DN_records'],inline_lengths_incomplete=result['inline_length_incomplete_records']),flush=True)
if __name__=='__main__':main()
