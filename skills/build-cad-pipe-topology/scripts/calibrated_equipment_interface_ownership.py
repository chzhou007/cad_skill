"""Source-calibrated logical ownership for paired plan terminal glyphs.

The rule uses independently confirmed controls, complete native glyphs, typed
pipe endpoints and unique equipment projection strips. It never locates a
physical equipment port or fills unshown pipe length.
"""
import argparse,collections,copy,csv,json,math,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_equipment_body import body_straight_segments
from cad_ceiling_native_rules import match_out_of_plane_symbol,on
from source_terminal_pair_inventory import candidate_pairs,LAYERS
from edge_endpoint_semantics import reconcile

def equipment(doc,graph):
    result={}
    for node in graph['nodes']:
        if node.get('node_type')!='equipment':continue
        insert=doc.entitydb.get(node.get('source_handle'))
        if not insert or insert not in doc.modelspace() or insert.dxftype()!='INSERT' or insert.dxf.name!=node.get('source_block'):raise ValueError('native equipment instance differs')
        segments,unsupported=body_straight_segments(insert)
        if not segments or unsupported:raise ValueError('incomplete native equipment body')
        points=[p for a,b in segments for p in (a,b)]
        box=[min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)]
        if math.dist([(box[0]+box[1])/2,(box[2]+box[3])/2],[node['x'],node['y']])>.05:raise ValueError('equipment body center differs')
        captions=[t.dxf.handle for t in doc.modelspace().query('TEXT MTEXT') if t.plain_text()==node['node_id']]
        result[node['node_id']]=dict(node=node,bounds=box,source_caption_handles=captions)
    return result

def native_interface(doc,node,edge):
    system=node.get('system');handle=node.get('source_handle');circle=doc.entitydb.get(handle);handles=node.get('source_handles',[])
    if (system not in LAYERS or edge.get('system')!=system or len(handles)!=5 or len(set(handles))!=5 or handle not in handles
        or not circle or circle not in doc.modelspace() or circle.dxftype()!='CIRCLE' or circle.dxf.layer!=LAYERS[system]
        or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.)):raise ValueError('native terminal circle scope differs')
    center=[circle.dxf.center.x,circle.dxf.center.y]
    if math.dist(center,[node['x'],node['y']])>.05:raise ValueError('native interface center differs')
    glyph=[]
    for item in handles:
        if item==handle:continue
        entity=doc.entitydb.get(item)
        if not entity or entity not in doc.modelspace() or entity.dxftype()!='LINE' or entity.dxf.layer!='空调立管、水平支管':raise ValueError('native terminal glyph differs')
        glyph.append(dict(handle=item,a=[entity.dxf.start.x,entity.dxf.start.y],b=[entity.dxf.end.x,entity.dxf.end.y]))
    matched=match_out_of_plane_symbol(dict(center=center,radius=circle.dxf.radius),glyph)
    if not matched or {x['handle'] for rows in matched for x in rows}!=set(handles)-{handle}:raise ValueError('complete calibrated terminal glyph not reproduced')
    hits=[];contacts=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer!=LAYERS[system]:continue
        if on(center,[line.dxf.start.x,line.dxf.start.y],[line.dxf.end.x,line.dxf.end.y],.05) is not None:contacts.append(line.dxf.handle)
        for a,b in ((line.dxf.start,line.dxf.end),(line.dxf.end,line.dxf.start)):
            if math.dist(center,[a.x,a.y])<=.05 and math.hypot(b.x-a.x,b.y-a.y)>.05:
                length=math.hypot(b.x-a.x,b.y-a.y);hits.append(dict(handle=line.dxf.handle,direction=[(b.x-a.x)/length,(b.y-a.y)/length],XYZ=[list(a),list(b)]))
    if len(hits)!=1 or set(contacts)!={hits[0]['handle']} or hits[0]['handle'] not in edge.get('source_handles',[]):raise ValueError('unique typed source pipe endpoint not reproduced')
    if not any(math.dist(center,path[0])<=.05 or math.dist(center,path[-1])<=.05 for path in edge.get('attribute_paths',[]) if len(path)>1):raise ValueError('graph pipe does not reach native terminal')
    return dict(node_id=node['node_id'],system=system,floor=node['floor'],point=center,circle_handle=handle,radius=circle.dxf.radius,
        glyph_handles=handles,edge_id=edge['edge_id'],pipe=hits[0],original_interface=copy.deepcopy(node))

def projected_candidates(pair,bodies,max_gap):
    a,b=pair;u=a['pipe']['direction'];v=[-u[1],u[0]]
    if a['floor']!=b['floor'] or {a['system'],b['system']}!={'supply','return'}:return [],'mixed_service_or_floor'
    if sum(x*y for x,y in zip(u,b['pipe']['direction']))<1-1e-8:return [],'pipe_approaches_not_parallel_in_same_direction'
    if max(abs(u[0]),abs(u[1]))<1-1e-8:return [],'non_orthogonal_plan_approach_outside_scope'
    dot=lambda p,w:p[0]*w[0]+p[1]*w[1];along=[dot(r['point'],u) for r in pair];across=[dot(r['point'],v) for r in pair];candidates=[]
    for identifier,body in bodies.items():
        node=body['node'];box=body['bounds']
        if node.get('floor')!=a['floor'] or node.get('identity_status')=='unresolved' or len(body['source_caption_handles'])!=1:continue
        corners=[(x,y) for x in box[:2] for y in box[2:]];normal=[dot(p,u) for p in corners];tangent=[dot(p,v) for p in corners]
        if any(x<min(tangent)-.05 or x>max(tangent)+.05 for x in across):continue
        if min(along)>max(normal)+.05:gap=max(along)-max(normal);face='positive_normal'
        elif max(along)<min(normal)-.05:gap=min(normal)-min(along);face='negative_normal'
        else:continue
        if gap<=max_gap:candidates.append(dict(equipment_id=identifier,equipment_handle=node['source_handle'],native_body_bounds=box,
            source_caption_handle=body['source_caption_handles'][0],normal_gap=gap,face=face,pipe_direction=u,strip_direction=v))
    return candidates,None

def calibration(doc,graph,policy):
    bodies=equipment(doc,graph);groups=collections.defaultdict(list);excluded=[];controls=[]
    for edge in graph['edges']:
        record=edge.get('confirmed_equipment_interface') or {}
        if record.get('confirmation',{}).get('confirmed_by')!='user':continue
        if record.get('source_sha256')!=policy['control_source_sha256']:raise ValueError('control source provenance differs')
        side=record.get('interface_side');owner=edge.get(str(side)+'_node_id')
        if side not in ('start','end') or owner not in bodies:raise ValueError('control equipment identity differs')
        groups[owner].append(native_interface(doc,record['original_interface'],edge))
    for owner,pair in groups.items():
        if len(pair)!=2 or {r['system'] for r in pair}!={'supply','return'}:raise ValueError('control must preserve both independent services')
        hits,reason=projected_candidates(pair,bodies,5000)
        if reason or len(hits)!=1:
            excluded.append(dict(equipment_id=owner,reason=reason or 'native_projection_strip_not_unique',candidates=hits));continue
        if hits[0]['equipment_id']!=owner:raise ValueError('calibration contradicts an expert-confirmed owner')
        spacing=math.dist(pair[0]['point'],pair[1]['point'])
        if not 100<=spacing<=600:raise ValueError('unsupported calibration spacing')
        controls.append(dict(equipment_id=owner,interfaces=pair,body_evidence=hits[0],spacing=spacing,confirmation='existing_explicit_user_confirmation'))
    if len(controls)<policy['minimum_controls'] or len({0 if abs(c['body_evidence']['pipe_direction'][0])>.99 else 1 for c in controls})<2:raise ValueError('insufficient independent control axes')
    margin=policy['normal_gap_margin_in_spacings']
    if isinstance(margin,bool) or not isinstance(margin,(int,float)) or not 0<=margin<=1:raise ValueError('unbounded calibration gap margin')
    return dict(status='source_calibrated_supported_projection_pattern',controls=controls,excluded_confirmed_patterns=excluded,
        spacings=sorted({round(c['spacing'],4) for c in controls}),maximum_gap_ratio=max(c['body_evidence']['normal_gap']/c['spacing'] for c in controls)+margin,
        physical_ports_verified=False,human_accepted=False)

def screen(doc,graph,model):
    bodies=equipment(doc,graph);degree=collections.defaultdict(list);interfaces=[];unsupported=[]
    for edge in graph['edges']:
        for key in ('start_node_id','end_node_id'):
            if edge.get(key):degree[edge[key]].append(edge)
    for node in graph['nodes']:
        if node.get('subtype')!='out_of_plane_interface':continue
        if len(degree[node['node_id']])!=1:raise ValueError('source interface has nonterminal graph degree')
        try:interfaces.append(native_interface(doc,node,degree[node['node_id']][0]))
        except ValueError as exc:unsupported.append(dict(node_id=node['node_id'],reason=str(exc)))
    by_id={r['node_id']:r for r in interfaces};pairs=[]
    for spacing in model['spacings']:
        source=[dict(node_id=r['node_id'],system=r['system'],x=r['point'][0],y=r['point'][1]) for r in interfaces]
        pairs+=candidate_pairs(source,spacing,.05)
    frequency=collections.Counter(n for p in pairs for n in (p['supply_node'],p['return_node']));rows=[]
    for spec in pairs:
        pair=[by_id[spec['supply_node']],by_id[spec['return_node']]];spacing=math.dist(pair[0]['point'],pair[1]['point'])
        candidates,reason=projected_candidates(pair,bodies,model['maximum_gap_ratio']*spacing)
        candidate=candidates[0] if len(candidates)==1 and all(frequency[r['node_id']]==1 for r in pair) else None
        rows.append(dict(interfaces=pair,spacing=spacing,candidates=candidates,proposed_owner=candidate,
            status='unique_calibrated_native_projection_candidate' if candidate else 'source_comparison_pending',reason=reason))
    claims=collections.Counter(row['proposed_owner']['equipment_id'] for row in rows if row['proposed_owner'])
    selected=[]
    for row in rows:
        owner=row['proposed_owner']
        if owner and claims[owner['equipment_id']]!=1:row.update(proposed_owner=None,status='multiple_pairs_claim_equipment_pending')
        elif owner:
            current=[e for e in graph['edges'] if owner['equipment_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
            if current:row.update(proposed_owner=None,status='equipment_already_connected_pending')
            else:selected.append(row)
    used={r['node_id'] for row in selected for r in row['interfaces']}
    return dict(status='calibrated_equipment_ownership_screen',pairs=rows,selected=selected,unsupported_interfaces=unsupported,
        unbound_interfaces=[r for r in interfaces if r['node_id'] not in used],equipment_count=len(bodies),graph_mutated=False,human_accepted=False)

def apply(graph,evidence,model,policy,source_hash,graph_hash):
    selected=evidence['selected']
    if len(selected)!=policy['expected_equipment_bindings']:raise ValueError('unexpected calibrated ownership scope; inspect source screen')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};retired=set();records=[]
    for row in selected:
        owner=row['proposed_owner'];did=owner['equipment_id']
        for interface in row['interfaces']:
            nid=interface['node_id'];edge=edges[interface['edge_id']];side='start' if edge.get('start_node_id')==nid else 'end'
            if edge.get(side+'_node_id')!=nid or nid in retired:raise ValueError('interface ownership changed')
            if edge.get('confirmed_equipment_interface') or edge.get('source_layout_equipment_interface'):raise ValueError('existing equipment ownership requires reconciliation')
            if any(g.get('node_id')==nid for g in graph.get('sourceTerminalGlyphs',[])):raise ValueError('source terminal display migration required')
            original=copy.deepcopy(nodes[nid]);edge[side+'_node_id']=did;edge.pop(side+'_port_id',None)
            record=dict(equipment_id=did,edge_id=edge['edge_id'],system=edge['system'],interface_side=side,original_interface=original,
                source_sha256=source_hash,input_graph_sha256=graph_hash,calibration_control_graph_sha256=policy['control_graph_sha256'],
                body_evidence=owner,native_interface=interface,status='source_calibrated_logical_ownership',physical_port_verified=False,
                interface_to_equipment_length_known=False,human_accepted=False,
                endpoint_snapshot=dict(start_node_id=edge['start_node_id'],end_node_id=edge['end_node_id'],equipment_source_handle=nodes[did]['source_handle'],equipment_xy=[nodes[did]['x'],nodes[did]['y']],system=edge['system'],attribute_paths=copy.deepcopy(edge['attribute_paths'])))
            edge['source_layout_equipment_interface']=record;edge['drawing_path_length']=edge.get('path_length');edge['path_length_complete']=False
            edge['physical_length_status']='unknown_interface_to_equipment_length';edge['path_length_scope']='source_drawn_pipe_only'
            retired.add(nid);records.append(record)
        nodes[did]['connection_status']='source_calibrated_logical_interfaces_physical_ports_unknown'
    out['nodes']=[n for n in out['nodes'] if n['node_id'] not in retired]
    out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in retired and p.get('node_id') not in retired]
    out,changes=reconcile(out)
    out['sourceLayoutEquipmentOwnership']=dict(status='native_calibrated_logical_ownership_source_checked',source_sha256=source_hash,input_graph_sha256=graph_hash,
        control_graph_sha256=policy['control_graph_sha256'],records=records,retired_interface_ids=sorted(retired),calibration=model,
        equipment_instances_conserved=True,supply_return_independent=True,physical_ports_verified=False,human_accepted=False)
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),reason='source-calibrated device endpoint ownership reconstructed; source paths unchanged',recompute=['equipment_ownership','crossview_mapping','diameter_inheritance','length_fusion','source_comparison','human_acceptance'],historical_annotations_preserved=True)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_source_calibrated_equipment_ownership')
    return out,records,changes

def compute(paths,policy):
    for key in ('source','graph','devices','control_source','control_graph'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('stale ownership input '+key)
    graph=load(paths['graph']);control=load(paths['control_graph'])
    for g,key in ((graph,'source'),(control,'control_source')):
        if g.get('metadata',{}).get('source_sha256')!=policy[key+'_sha256']:raise ValueError('graph source differs')
    if graph.get('sourceEquipmentIdentityResolution'):
        from resolve_rotated_equipment_labels import verify_output
        if verify_output(Path(paths['graph']).parent)['output_graph_sha256']!=sha(paths['graph']):raise ValueError('identity parent differs')
    from reconstruct_confirmed_equipment_pairs import verify_output as verify_controls
    if control.get('confirmedEquipmentPairReconstruction') and verify_controls(Path(paths['control_graph']).parent)['output_graph_sha256']!=sha(paths['control_graph']):raise ValueError('confirmed control graph differs')
    doc,preflight=read_source(paths['source']);control_doc,control_preflight=read_source(paths['control_source'])
    model=calibration(control_doc,control,policy);evidence=screen(doc,graph,model)
    return graph,model,evidence,dict(source_preflight=preflight,control_preflight=control_preflight)

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'calibrated-equipment-ownership-audit.json')
    if audit['implementation_sha256']!=sha(Path(__file__)):raise ValueError('stale calibrated ownership implementation')
    for key,item in audit['inputs'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale calibrated ownership input '+key)
    paths={k:v['path'] for k,v in audit['inputs'].items() if k!='policy'};policy=load(audit['inputs']['policy']['path'])
    graph,model,evidence,_=compute(paths,policy);out,records,_=apply(graph,evidence,model,policy,sha(paths['source']),sha(paths['graph']))
    if encode(out)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or records!=audit['records']:raise ValueError('native calibrated ownership replay differs')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('component audit changed')
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','control-source','control-graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--screen-only',action='store_true');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    paths={key:getattr(a,key) for key in ('source','graph','devices','control_source','control_graph')};policy=load(a.policy)
    graph,model,evidence,proof=compute(paths,policy);a.output.mkdir(parents=True);(a.output/'source-screen.json').write_bytes(encode(dict(calibration=model,evidence=evidence,**proof)))
    if not a.screen_only:
        out,records,changes=apply(graph,evidence,model,policy,sha(a.source),sha(a.graph));(a.output/'graph_with_edges.json').write_bytes(encode(out));shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
        paths['policy']=a.policy
        audit=dict(**proof,records=records,endpoint_type_changes=changes,parent_graph=dict(path=str(a.graph.resolve()),sha256=sha(a.graph)),
            inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=sha(Path(__file__)),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
        (a.output/'calibrated-equipment-ownership-audit.json').write_bytes(encode(audit))
    print(json.dumps(dict(controls=len(model['controls']),selected_equipment=len(evidence['selected']),unbound_interfaces=len(evidence['unbound_interfaces']),screen_only=a.screen_only,human_accepted=False)))

if __name__=='__main__':main()
