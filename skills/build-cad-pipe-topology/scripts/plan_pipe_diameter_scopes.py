"""Source-scoped plan DN: prove through-pipe inheritance and branch overrides.

The graph is immutable. Annotated feeder fragments are read-only frontiers,
never new physical nodes or whole-edge DN claims on the unselected feeder.
"""
import argparse,copy,json,logging,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from pipe_annotation_attributes import source_texts,parse_dn_annotation,direct_diameters,recognize_f_leaders,contact
from source_direct_dn_evidence import collect as direct_evidence,_projection
from native_dn_text_position import supported
from native_line_path_evidence import _on,LAYERS
from native_path_coverage_audit import audit as coverage_audit
from native_equipment_body import point_segment_distance
from nested_dn_screen import screen as nested_screen
from crossview_equipment_branch_inventory import index_graph,native_tee
from match_source_checked_crossview_paths import native_main_corridor
from diameter_tee_inheritance import infer
from ezdxf.disassemble import recursive_decompose

class Capture(logging.Handler):
    def __init__(self):super().__init__();self.messages=[]
    def emit(self,record):self.messages.append(record.getMessage())

def copied_metadata(doc,message):
    """Classify an ignored object, never an ignored visible entity/annotation."""
    m=re.fullmatch(r'copy process ignored (ACAD_PROXY_OBJECT|FIELD)\(#([0-9A-Fa-f]+)\) - this may cause problems in AutoCAD',message)
    if not m:raise ValueError('unclassified nested copy warning: '+message)
    kind,handle=m.groups();entity=doc.entitydb.get(handle)
    if entity is None or entity.dxftype()!=kind:raise ValueError('nested metadata warning source differs')
    if kind=='ACAD_PROXY_OBJECT':return dict(type=kind,handle=handle)
    # A native FIELD is not generally ignorable: it may evaluate a DN label.
    # Only a literal cached axis-number ATTRIB with the genuine ownership chain
    # and matching raw FIELD values is supported here. No expression evaluation.
    field_dict=doc.entitydb.get(entity.dxf.owner)
    if field_dict is None or field_dict.dxftype()!='DICTIONARY' or field_dict.get('TEXT') is not entity:raise ValueError('FIELD TEXT dictionary differs')
    extension=doc.entitydb.get(field_dict.dxf.owner)
    if extension is None or extension.dxftype()!='DICTIONARY' or extension.get('ACAD_FIELD') is not field_dict:raise ValueError('FIELD extension dictionary differs')
    owner=doc.entitydb.get(extension.dxf.owner)
    if owner is None or owner.dxftype()!='ATTRIB' or not owner.has_extension_dict or owner.get_extension_dict().dictionary is not extension:raise ValueError('FIELD visible owner differs')
    text=owner.dxf.text
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',text) or 'AXIS' not in owner.dxf.layer.upper():raise ValueError('FIELD is not a literal axis-number attribute')
    subclasses=entity.xtags.subclasses
    if len(subclasses)!=2 or subclasses[1][0].value!='AcDbField':raise ValueError('FIELD native schema unsupported')
    tags=list(subclasses[1]);codes={code:[t.value for t in tags if t.code==code] for code in (1,2,301)}
    if codes!={1:['_text',text],2:[text],301:[text]} or any(330<=t.code<=369 for t in tags):raise ValueError('FIELD expression/cache/reference unsupported')
    return dict(type=kind,handle=handle,owner_handle=owner.dxf.handle,visible_text=text,owner_layer=owner.dxf.layer,
        interpretation='literal_axis_number_cache_not_DN',field_expression_evaluated=False)

def guard_leader_bridges(doc,texts,paths,verified_strokes=()):
    """An unclassified long leader must not disappear outside a text radius."""
    for layer in {t['layer'] for t in texts if re.search(r'DN',t['text'],re.I)}:
        if layer in LAYERS.values():continue  # physical LINE is not a leader
        segments=[]
        for e in doc.modelspace().query('LINE LWPOLYLINE'):
            if e.dxf.layer!=layer or e.dxf.handle in verified_strokes:continue
            if e.dxftype()=='LINE':pts=[list(e.dxf.start)[:2],list(e.dxf.end)[:2]]
            else:
                if any(abs(p[4])>1e-9 for p in e.get_points()):raise ValueError('curved annotation leader needs dedicated attribution')
                pts=[list(p)[:2] for p in e.vertices_in_wcs()]
                if e.closed:pts=pts+pts[:1]
            segments.extend(zip(pts,pts[1:]))
        unseen=set(range(len(segments)))
        while unseen:
            component={unseen.pop()};queue=list(component)
            while queue:
                current=queue.pop();a,b=segments[current]
                neighbors={i for i in unseen if any(math.dist(p,q)<=.05 for p in (a,b) for q in segments[i])}
                unseen-=neighbors;component|=neighbors;queue.extend(neighbors)
            near=[t for t in texts if t['layer']==layer and re.search(r'DN',t['text'],re.I) and min(point_segment_distance(t['position'],*segments[i]) for i in component)<=3*t['height']]
            intersections=[contact(*segments[i],a,b) for i in component for path in paths for a,b in zip(path,path[1:]) if contact(*segments[i],a,b) is not None]
            if near and intersections:raise ValueError('unclassified annotation leader reaches DN scope; use the F/leader feature: '+json.dumps(dict(layer=layer,texts=[(t['handle'],t['text']) for t in near],segments=[segments[i] for i in sorted(component)],intersections=intersections),ensure_ascii=False))

def catalog(doc,graph,ids,source_hash,graph_hash):
    texts=source_texts(doc,'plan',source_hash)
    for t in texts:
        if '\ufffd' in t['text'] or any(0xd800<=ord(c)<=0xdfff for c in t['text']):raise ValueError('unreadable modelspace annotation')
    nested=nested_screen(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=ids,nested_search_radius=1000),source_hash,graph_hash)
    for key in ('missing_blocks','xref_blocks','proxy_entities_in_blocks','proxy_entities_modelspace','array_inserts','cyclic_block_names'):
        if nested[key]:raise ValueError('visible annotation coverage unsupported '+key)
    # All nested DN is deliberately withheld here, including distant leaders:
    # the existing nested/F-specific feature owns those bindings.
    if nested['flattened_dn_text_entities']:raise ValueError('nested DN requires its source-specific attribution rule')
    handler=Capture();logger=logging.getLogger('ezdxf');logger.addHandler(handler);old=logger.propagate;logger.propagate=False
    notes=[]
    try:
        for root in doc.modelspace().query('INSERT'):
            for e in recursive_decompose([root]):
                if e.dxftype() in ('TEXT','MTEXT','ATTRIB'):
                    text=e.plain_text()
                    if '\ufffd' in text:raise ValueError('unreadable nested text')
                    if any(word in text for word in ('管径','公称','变径')):notes.append(dict(root_handle=root.dxf.handle,text=text))
    finally:logger.removeHandler(handler);logger.propagate=old
    metadata_warnings=[];field_warnings=[]
    for message in handler.messages:
        proof=copied_metadata(doc,message)
        if proof['type']=='FIELD':field_warnings.append(proof)
        else:metadata_warnings.append(proof['handle'])
    if notes or any(any(word in t['text'] for word in ('管径','公称','变径')) for t in texts):raise ValueError('general DN note requires explicit interpretation')
    unsupported=[]
    for e in doc.modelspace():
        if e.dxftype() in ('LEADER','MLEADER','MULTILEADER','ACAD_PROXY_ENTITY'):unsupported.append(e.dxftype())
        if e.dxftype()=='DIMENSION' and (re.search(r'DN|%%[cC]|管径',e.dxf.get('text','') or '',re.I) or e.dxf.dimtype&7 in (3,4)):unsupported.append('DN_or_diameter_dimension')
    if unsupported:raise ValueError('unsupported leader/dimension annotation '+str(sorted(set(unsupported))))
    layers={t['layer'] for t in texts};frames=recognize_f_leaders(doc,texts,[],graph['edges'],layers);f_handles={t['handle'] for frame in frames for t in frame['texts']}
    evidence=dict(status='readable_native_visible_annotation_scope',modelspace_texts=len(texts),nested=nested,
        ignored_metadata_copy_handles=sorted(set(metadata_warnings)),opaque_object_payloads_interpreted=False,
        F_text_handles=sorted(f_handles),whole_physical_parameter_completeness_claimed=False)
    if field_warnings:evidence['literal_axis_FIELD_metadata']=sorted(field_warnings,key=lambda r:r['handle'])
    return texts,evidence

def trim_frontier(graph,edge,tee,point=None):
    """Keep only a continuous source path from the selected T to a seed/limit."""
    nodes,_,_=index_graph(graph);p=[nodes[tee]['x'],nodes[tee]['y']];hits=[]
    for path in edge['attribute_paths']:
        if math.dist(path[0],p)<=.05:hits.append(copy.deepcopy(path))
        elif math.dist(path[-1],p)<=.05:hits.append(list(reversed(copy.deepcopy(path))))
    if len(hits)!=1:raise ValueError('frontier source path does not uniquely reach T')
    path=hits[0]
    if point is not None:
        places=[i for i,(a,b) in enumerate(zip(path,path[1:])) if _on(point,a,b,.05)]
        if len(places)!=1:raise ValueError('annotation cannot reach this T without an unproved gap/overlap')
        path=path[:places[0]+1]+[list(point)]
    else:path=path[:2]
    if len(path)<2 or math.dist(path[0],path[-1])<=.05:raise ValueError('empty annotation frontier')
    eid=edge['edge_id'];boundary='DN-READ-ONLY-'+eid;result=copy.deepcopy(edge)
    result.update(start_node_id=tee,end_node_id=None,start_boundary_id=None,end_boundary_id=boundary,attribute_paths=[path])
    return result,dict(boundary_id=boundary,system=edge['system'],floor=nodes[tee]['floor'],x=path[-1][0],y=path[-1][1],
        boundary_type='read_only_DN_annotation_scope_limit_not_physical_interface'),dict(edge_id=eid,original_endpoints=[edge['start_node_id'],edge['end_node_id']],selected_T=tee,
        projected_source_path=path,annotation_point=point,whole_original_edge_value_assigned=False)

def group_evidence(doc,graph,group,texts,source_hash,graph_hash,F_handles,direct_collector=direct_evidence,path_auditor=coverage_audit,verified_nonpipe_annotation_strokes=()):
    nodes,edges,adj=index_graph(graph);branches=group['branches'];mains=set(group['main_edges']);taps={b['tee'] for b in branches};selected=mains|{b['edge_id'] for b in branches}
    if len(selected)!=len(mains)+len(branches) or len(taps)!=len(branches):raise ValueError('duplicate branch/T or overlapping scope')
    floor=group['floor'];junctions={}
    for branch in branches:
        e=edges[branch['edge_id']];n=nodes[branch['tee']]
        if n.get('floor')!=floor or n.get('review_required') is True or e['system']!=branch['system'] or {e['start_node_id'],e['end_node_id']}!={branch['tee'],branch['equipment_id']}:raise ValueError('branch scope/floor differs')
        junctions[branch['tee']]=native_tee(doc,graph,branch['tee'],source_hash,graph_hash)
    for system in ('supply','return'):
        by={b['equipment_id']:b['tee'] for b in branches if b['system']==system}
        if len(by)<3:raise ValueError('through-pipe scope needs at least three checked branch anchors')
        corridor,evidence=native_main_corridor(doc,graph,by,system,floor)
        between={e['edge_id'] for e in corridor['edges'] if {e['start_node_id'],e['end_node_id']}<=set(by.values())}
        if between!={eid for eid in mains if edges[eid]['system']==system} or len(between)!=len(by)-1:raise ValueError('through-pipe source corridor differs')
        for branch in [b for b in branches if b['system']==system]:
            rays=junctions[branch['tee']]['junctions'][0]['source_rays'];through=[r for r in rays if r['edge_id']!=branch['edge_id']]
            if len(through)!=2 or any(r.get('source_line_handle')!=evidence['source_line_handle'] for r in through):raise ValueError('branch cannot redefine the through-source LINE')
    from native_line_f_diameter_evidence import collect as collect_line_F
    line_F=collect_line_F(doc,graph,group['line_F_frames'],source_hash,graph_hash) if group.get('line_F_frames') else dict(frames=[])
    recognized_F_texts={h for frame in line_F['frames'] for h in frame['text_handles']}
    recognized_F_strokes={h for frame in line_F['frames'] for h in frame['stroke_handles']}
    scalar_texts=[t for t in texts if t['handle'] not in recognized_F_texts]
    seeds=group['seeds'];layers=sorted({t['layer'] for t in texts})
    if any(s['text_handle'] in F_handles for s in seeds):raise ValueError('F label needs its ordering feature before inheritance')
    direct=direct_collector(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=layers,selections=seeds),source_hash,graph_hash)
    observations={r['edge_id']:r for r in direct['observations']};projection=copy.deepcopy(graph);pe={e['edge_id']:e for e in projection['edges']};frontiers=[];frontier_ids=set()
    # Set iteration order varies across Python processes; it must not reorder
    # boundary evidence or the projection hash bound by native coverage.
    for tee in sorted(taps):
        for e in adj[tee]:
            if e['edge_id'] in selected:continue
            if e['start_node_id'] in taps and e['end_node_id'] in taps:raise ValueError('unselected main between checked Ts')
            observation=observations.get(e['edge_id']);cut,boundary,receipt=trim_frontier(graph,e,tee,observation['graph_projection'] if observation else None)
            pe[e['edge_id']].update(cut);projection.setdefault('boundary_anchors',[]).append(boundary);frontiers.append(receipt);frontier_ids.add(e['edge_id'])
    if not set(observations)<=mains|frontier_ids:raise ValueError('main seed outside checked source frontier')
    covered=sorted(selected|frontier_ids);projection_hash=__import__('hashlib').sha256(encode(projection)).hexdigest()
    coverage=path_auditor(doc,projection,dict(source_sha256=source_hash,graph_sha256=projection_hash,edges=covered),source_hash,projection_hash)
    if any(s['status']!='single_source_line_covers' for row in coverage['edges'] for s in row['segments']):raise ValueError('selected DN pipe path lacks unique native source coverage')
    paths=[path for eid in covered for path in pe[eid]['attribute_paths']]
    guard_leader_bridges(doc,scalar_texts,paths,recognized_F_strokes|set(verified_nonpipe_annotation_strokes))
    all_assigned,_=direct_diameters(scalar_texts,graph['edges'],set(),set(layers));originally_bound={r['text']['handle'] for r in all_assigned}|{r['source_text']['handle'] for r in direct['observations']}
    for t in scalar_texts:
        if re.search(r'DN',t['text'],re.I) and t['handle'] not in originally_bound and any(point_segment_distance(t['position'],a,b)<=3*t['height'] for path in paths for a,b in zip(path,path[1:])):raise ValueError('unattributed DN near scope cannot be treated as an absent change mark')
    # Every visible single DN on a checked path participates, including a new
    # branch annotation. Foreign/compound/ambiguous labels block this scope.
    assigned,pending=direct_diameters(scalar_texts,projection['edges'],set(),set(layers));allowed={o['source_text']['handle'] for o in observations.values()}
    for row in pending:
        if selected.intersection(row['candidate_edge_ids']):raise ValueError('ambiguous source DN overlaps selected paths')
    local={}
    for frame in line_F['frames']:
        for binding in frame['bindings']:
            if binding['edge_id'] in selected|frontier_ids:local.setdefault(binding['edge_id'],[]).append(binding)
    for row in assigned:
        if row['edge_id'] not in selected|frontier_ids:continue
        h=row['text']['handle'];native=doc.entitydb.get(h)
        if h in F_handles or native is None or not supported(native):raise ValueError('unsupported DN label transform/leader')
        if h in allowed:continue
        witness=next(r for r in coverage['edges'] if r['edge_id']==row['edge_id'])
        lines={w['source_handle'] for s in witness['segments'] for w in s['witnesses'] if _on(row['point'],s['start'],s['end'],.05)}
        if len(lines)!=1:raise ValueError('additional label native owner is ambiguous')
        extra=dict(text_handle=h,edge_id=row['edge_id'],source_line_handle=next(iter(lines)),expected_text=row['text']['text'])
        fresh=direct_collector(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=layers,selections=[extra]),source_hash,graph_hash)['observations'][0]
        local.setdefault(row['edge_id'],[]).append(fresh)
    for t in scalar_texts:
        if not re.search(r'DN',t['text'],re.I) or parse_dn_annotation(t['text']) is not None:continue
        probe=dict(t,text='DN1');a,p=direct_diameters([probe],projection['edges'],set(),set(layers))
        if any((selected|frontier_ids).intersection(row['candidate_edge_ids']) for row in a+p):raise ValueError('compound/system-qualified DN needs explicit scope attribution')
    all_main=copy.deepcopy(observations)
    for eid,items in local.items():
        if eid in mains|frontier_ids:
            if len({r['nominal_mm'] for r in items})!=1:raise ValueError('multiple DN values on an edge require subdivision')
            all_main[eid]=items[0]
    seed_rows=[dict(edge_id=eid,nominal_mm=o['nominal_mm'],evidence_id='source:'+o['source_text']['handle']) for eid,o in all_main.items()]
    if {edges[eid]['system'] for eid in all_main}!={'supply','return'}:raise ValueError('both services need independent main DN evidence')
    inferred=infer(projection,seed_rows,mains|frontier_ids,taps);by={r['edge_id']:r for r in inferred};results=[]
    for eid in sorted(mains):
        row=by[eid];results.append(dict(edge_id=eid,system=edges[eid]['system'],nominal_mm=row['nominal_mm'],status='direct_plan_DN' if row['status']=='direct' else 'T_inherited_plan_DN' if row['status']=='inherited_candidate' else row['status'],
            lineage=row['candidates'],scope_paths=edges[eid]['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False))
    for branch in branches:
        eid=branch['edge_id'];direct_branch=local.get(eid,[])
        if direct_branch:
            values={o['nominal_mm'] for o in direct_branch};value=next(iter(values)) if len(values)==1 else None;status='direct_branch_DN_override' if value is not None else 'conflict'
            lineage=[dict(nominal_mm=o['nominal_mm'],evidence=[dict(evidence_id='source:'+o['source_text']['handle'],edge_path=[eid])]) for o in direct_branch]
        else:
            arms=[e['edge_id'] for e in adj[branch['tee']] if e['edge_id']!=eid];values=[by[a]['nominal_mm'] for a in arms];value=values[0] if None not in values and len(set(values))==1 else None
            status='T_inherited_plan_DN' if value is not None else 'main_DN_conflict_or_unknown'
            lineage=[]
            for arm in arms:
                for candidate in by[arm]['candidates']:
                    lineage.append(dict(nominal_mm=candidate['nominal_mm'],evidence=[dict(ev,edge_path=ev['edge_path']+[eid]) for ev in candidate['evidence']]))
        results.append(dict(edge_id=eid,system=branch['system'],nominal_mm=value,status=status,lineage=lineage,scope_paths=edges[eid]['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False))
    return dict(group_id=group['group_id'],records=results,source_DN_observations=direct['observations'],additional_DN_observations=local,line_F_evidence=line_F,
        frontier_fragments=frontiers,read_only_projection_sha256=projection_hash,coverage=coverage,junctions=junctions,
        rule='through_SOURCE_LINE_first_branch_explicit_label_overrides_inheritance',outside_frontiers_traversed=False,graph_mutated=False,human_accepted=False)

def compute(paths,policy):
    for key in ('source','graph'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('DN scope input changed '+key)
    from normalize_plan_circle_paths import verify_output as verify_plan
    if verify_plan(Path(paths['graph']).parent)['output_graph_sha256']!=sha(paths['graph']):raise ValueError('DN plan local stage differs')
    doc,preflight=read_source(paths['source']);graph=load(paths['graph']);groups=policy['groups'];ids=[eid for group in groups for eid in group['main_edges']+[b['edge_id'] for b in group['branches']]]
    if len(ids)!=len(set(ids)) or not policy.get('expert_T_inheritance_rule'):raise ValueError('overlapping/missing explicit expert rule scope')
    texts,inventory=catalog(doc,graph,ids,sha(paths['source']),sha(paths['graph']))
    result=[group_evidence(doc,graph,g,texts,sha(paths['source']),sha(paths['graph']),set(inventory['F_text_handles'])) for g in groups]
    return dict(status='source_checked_plan_DN_scopes_human_pending',source_sha256=sha(paths['source']),graph_sha256=sha(paths['graph']),source_preflight=preflight,
        source_annotation_inventory=inventory,groups=result,records=[r for g in result for r in g['records']],local_graph_mutated=False,
        scope='native_floor_plan_drawn_pipe_paths_only_not_unshown_drops_or_equipment_connectors',expert_rule=policy['expert_T_inheritance_rule'],human_accepted=False)

def implementation_hashes():
    return {n:sha(Path(__file__).with_name(n)) for n in ('native_confirmed_equipment_pair_circle_evidence.py','plan_pipe_diameter_scopes.py','native_line_f_diameter_evidence.py','diameter_tee_inheritance.py','source_direct_dn_evidence.py','source_dn_annotation_risks.py','nested_dn_screen.py','native_path_coverage_audit.py','native_dn_text_position.py','pipe_annotation_attributes.py','crossview_equipment_branch_inventory.py','native_junction_ray_evidence.py','native_circle_rim_junction_evidence.py','match_source_checked_crossview_paths.py','source_readability.py')}

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'plan-DN-scope-receipt.json')
    if receipt.get('mode')=='calibrated_plan_DN_scopes':
        from plan_calibrated_DN_scopes import verify_output as verify_calibrated
        return verify_calibrated(directory)
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('stale plan DN scope implementation')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('plan DN dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'plan-DN-scopes.json').read_bytes() or sha(directory/'plan-DN-scopes.json')!=receipt['output_sha256']:raise ValueError('plan DN scope replay differs')
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();paths={k:getattr(args,k) for k in ('source','graph','policy')}
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(paths,load(args.policy));args.output.mkdir(parents=True);(args.output/'plan-DN-scopes.json').write_bytes(encode(result))
    receipt=dict(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(args.output/'plan-DN-scopes.json'),human_accepted=False)
    (args.output/'plan-DN-scope-receipt.json').write_bytes(encode(receipt));print(json.dumps(dict(source_plan_edges=len(result['records']),known_plan_DN=sum(r['nominal_mm'] is not None for r in result['records']),human_accepted=False)))

if __name__=='__main__':main()
