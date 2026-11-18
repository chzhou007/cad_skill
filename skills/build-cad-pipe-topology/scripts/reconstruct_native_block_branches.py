"""Reconstruct selected native block branches; preserve unknown omitted lengths.

Source paths, drawing markers, inline-symbol spans and display anchors remain
distinct.  A source block chain is not a physical port or cross-view mapping.
"""
import argparse,copy,csv,hashlib,json,math,shutil
from pathlib import Path
from source_readability import read_source
from native_path_coverage_audit import audit as audit_path
from native_device_circle_lines import collect as collect_circles
from native_nested_joint_evidence import collect as collect_joints,fingerprint
from native_equipment_body import point_segment_distance
from native_offset_circle_candidates import collect as collect_offsets
from repair_exploded_joint_ownership import _inventory

encode=lambda x:(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8')
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
value_sha=lambda x:hashlib.sha256(encode(x)).hexdigest()


def projected_coverage(doc,graph,eid,source_hash):
    """Explicitly hash each read-only path projection; never forge its identity."""
    edge=next(e for e in graph['edges'] if e['edge_id']==eid);rows=[]
    for index,path in enumerate(edge['attribute_paths']):
        projected=copy.deepcopy(graph)
        next(e for e in projected['edges'] if e['edge_id']==eid)['attribute_paths']=[copy.deepcopy(path)]
        projected_hash=value_sha(projected)
        coverage=audit_path(doc,projected,dict(source_sha256=source_hash,graph_sha256=projected_hash,edges=[eid]),source_hash,projected_hash)
        rows.append(dict(original_path_index=index,projection_graph_sha256=projected_hash,coverage=coverage['edges'][0]))
    return rows


def source_child(root,handle,typ):
    matches=[e for e in root.virtual_entities() if e.dxftype()==typ and getattr(e,'source_of_copy',None) is not None and e.source_of_copy.dxf.handle==handle]
    if len(matches)!=1:raise ValueError('native direct child missing or ambiguous')
    return matches[0]


def marker_records(root):
    rows=[]
    for e in root.virtual_entities():
        if e.dxftype()!='LWPOLYLINE' or e.dxf.layer!='DIM_SYMB':continue
        points=[list(p) for p in e.vertices_in_wcs()]
        if e.closed or len(points)!=6 or any(abs(float(v[4]))>1e-12 for v in e.get_points('xyseb')) or getattr(e,'source_of_copy',None) is None:raise ValueError('unsupported native omission marker')
        rows.append(dict(source_chain=[root.dxf.handle,e.source_of_copy.dxf.handle],points=points,
            center=[(min(p[axis] for p in points)+max(p[axis] for p in points))/2 for axis in (0,1)]))
    if len(rows)!=2:raise ValueError('omission branch requires exactly two native markers')
    return rows


def marker_distance(point,marker):
    return min(point_segment_distance(point,a[:2],b[:2]) for a,b in zip(marker['points'],marker['points'][1:]))


def inherited_offset_controls(paths,policy,source_hash):
    """Pin the historical scope, then recheck actual geometry inside probe()."""
    ids=policy.get('offset_edge_ids',[])
    if not isinstance(ids,list) or len(set(ids))!=len(ids):raise ValueError('invalid inherited offset scope')
    if not ids:
        if any(paths.get(k) for k in ('offset_policy','offset_audit')):raise ValueError('offset controls supplied without explicit scope')
        return {}
    for key in ('offset_policy','offset_audit'):
        if not paths.get(key) or sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('stale inherited offset '+key)
    original=load(paths['offset_policy']);audit=load(paths['offset_audit'])
    if (original.get('source_sha256')!=source_hash or audit.get('source_sha256')!=source_hash
        or audit.get('policy_sha256')!=sha(paths['offset_policy']) or audit.get('status')!='source_evidence_repaired_unreviewed'
        or original.get('joint_block')!=policy['joint_block'] or original.get('block_fingerprint_sha256')!=policy['joint_fingerprint_sha256']):raise ValueError('inherited offset source/definition differs')
    controls={}
    for eid in ids:
        choices=[r for r in original['corrections'] if r['to_edge']==eid];old=[r for r in audit['changes'] if r['to_edge']==eid]
        if len(choices)!=1 or len(old)!=1 or choices[0]['device_name']!=old[0]['device_name']:raise ValueError('historical offset edge scope ambiguous')
        controls[eid]=dict(offset_evidence=old[0]['offset_circle_evidence'],component_name=old[0]['device_name'],
            historical_joint_evidence=old[0]['joint_evidence'],max_radius_ratio=original['max_radius_ratio'],
            control_policy_sha256=sha(paths['offset_policy']),control_audit_sha256=sha(paths['offset_audit']))
    return controls


def probe(doc,graph,inventory,eid,policy,hashes):
    edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']};edge=edges[eid]
    equipment=edge.get('device_label');node=nodes.get(equipment,{})
    if (node.get('node_type')!='equipment' or equipment not in (edge.get('start_node_id'),edge.get('end_node_id'))
        or edge.get('system') not in ('supply','return') or edge.get('source_native_block_branch')):raise ValueError('unsupported equipment branch')
    root=doc.entitydb.get(edge.get('source_insert_handle'))
    if not root or root.dxftype()!='INSERT' or root not in doc.modelspace():raise ValueError('selected native INSERT missing')
    captions=[e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text()==equipment]
    if len(captions)!=1:raise ValueError('native equipment caption missing or ambiguous')
    coverage=projected_coverage(doc,graph,eid,hashes['source_sha256'])
    missing=[(p['original_path_index'],s) for p in coverage for s in p['coverage']['segments'] if s['status']!='single_source_line_covers']
    if len(missing)!=1 or missing[0][1]['status']!='no_witness_in_scoped_search':raise ValueError('branch needs exactly one unsupported display-anchor span')
    path_index,span=missing[0];path=copy.deepcopy(edge['attribute_paths'][path_index]);anchor=[node['x'],node['y']]
    at_start=span['index']==0 and math.dist(path[0],anchor)<=.05
    at_end=span['index']==len(path)-2 and math.dist(path[-1],anchor)<=.05
    if at_start==at_end:raise ValueError('unwitnessed span is not a unique terminal display anchor')
    trimmed=path[1:] if at_start else path[:-1]
    if len(trimmed)<2:raise ValueError('display anchor has no retained source path')
    circle=collect_circles(doc,graph,dict(hashes,edges=[eid]),hashes['source_sha256'],hashes['graph_sha256'])
    joint_hashes=dict(hashes,circle_sha256=value_sha(circle))
    joints=collect_joints(doc,graph,inventory,circle,dict(joint_hashes,joint_block=policy['joint_block'],block_fingerprint_sha256=policy['joint_fingerprint_sha256'],edges=[eid]),joint_hashes)
    row=joints['edges'][0]
    offset=None;control=policy.get('_verified_offset_controls',{}).get(eid)
    if row['status']!='unique_source_symbol_evidence' and control:
        screen=collect_offsets(doc,graph,dict(hashes,edges=[eid],max_radius_ratio=control['max_radius_ratio']),hashes['source_sha256'],hashes['graph_sha256'])
        result=screen['edges'][0]
        if result['status']!='unique_offset_candidate' or result['candidates']!=[control['offset_evidence']]:raise ValueError('inherited offset geometry changed or ambiguous')
        c=result['candidates'][0]
        # Reuse the existing bounded-offset interpretation, retaining its actual
        # XY deviation. z_coincident refers only to Z, not circle-center equality.
        circle=dict(status='source_geometry_candidates_only',source_sha256=hashes['source_sha256'],graph_sha256=hashes['graph_sha256'],edges=[dict(edge_id=eid,system=edge['system'],source_insert_handle=root.dxf.handle,candidates=[dict(source_chain=c['source_line_chain'],source_relation='inherited_bounded_offset',circles=[dict(source_chain=c['source_circle_chain'],z_coincident=abs(c['line_endpoint'][2]-c['circle_center'][2])<=.05,line_endpoint_index=c['endpoint_index'])])])])
        joint_hashes=dict(hashes,circle_sha256=value_sha(circle))
        joints=collect_joints(doc,graph,inventory,circle,dict(joint_hashes,joint_block=policy['joint_block'],block_fingerprint_sha256=policy['joint_fingerprint_sha256'],edges=[eid]),joint_hashes)
        row=joints['edges'][0]
        if row['status']!='unique_source_symbol_evidence' or row['matches']!=[control['historical_joint_evidence']] or row['matches'][0]['component_name']!=control['component_name']:raise ValueError('inherited offset joint/assignment changed')
        offset=dict(source_geometry=screen,contact=c,control_policy_sha256=control['control_policy_sha256'],control_audit_sha256=control['control_audit_sha256'],
            interpretation='historical_bounded_offset_source_relation',physical_length_mm=None,physical_port_verified=False,human_accepted=False)
    if row['status']!='unique_source_symbol_evidence' or len(row['matches'])!=1:raise ValueError('native nested endpoint joint not unique')
    match=row['matches'][0]
    inner=source_child(root,match['inner_line_chain'][1],'LINE');circle_entity=source_child(root,match['circle_chain'][1],'CIRCLE')
    if circle_entity.dxf.layer!='空调平面':raise ValueError('endpoint circle is not a native equipment body circle')
    center=list(circle_entity.ocs().to_wcs(circle_entity.dxf.center));ends=[list(inner.dxf.start),list(inner.dxf.end)]
    source_end=offset['contact']['line_endpoint'] if offset else center
    endpoint=[p for p in ends if math.dist(p,source_end)<=.05]
    joint_end=[p for p in ends if math.dist(p,match['inner_contact'])<=.05]
    if len(endpoint)!=1 or len(joint_end)!=1 or endpoint[0]==joint_end[0]:raise ValueError('inner source line does not uniquely link joint and body circle')
    source_paths=copy.deepcopy(edge['attribute_paths']);source_paths[path_index]=trimmed
    omitted=None;outer_point=match['outer_contact'][:2]
    if len(source_paths)==1 and edge.get('connection_mode')=='direct_existing_cad_branch':
        if min(math.dist(outer_point,p) for p in (trimmed[0],trimmed[-1]))>.05:raise ValueError('trimmed direct branch misses native outer joint contact')
    elif len(source_paths)==2 and edge.get('connection_mode')=='omission_pair_stitched_at_main_marker':
        markers=marker_records(root)
        centered=[m for m in markers if math.dist(m['center'],anchor)<=.05]
        if len(centered)!=1:raise ValueError('display anchor is not the native main marker center')
        main=centered[0];remote=next(m for m in markers if m is not main)
        contact=trimmed[0] if at_start else trimmed[-1]
        if marker_distance(contact,main)>.05:raise ValueError('main source path does not end at its omission glyph')
        other=source_paths[1-path_index]
        remote_contacts=[p for p in (other[0],other[-1]) if marker_distance(p,remote)<=.05]
        joint_contacts=[p for p in (other[0],other[-1]) if math.dist(p,outer_point)<=.05]
        if len(remote_contacts)!=1 or len(joint_contacts)!=1 or remote_contacts[0]==joint_contacts[0]:raise ValueError('remote source path does not uniquely link marker and joint')
        omitted=dict(main_marker=main,remote_marker=remote,main_pipe_contact=contact,remote_pipe_contact=remote_contacts[0],
            physical_length_mm=None,physical_component=False,additional_physical_property=False)
    else:raise ValueError('unsupported branch path/connection mode')
    new_inner=[match['inner_contact'][:2],endpoint[0][:2]]
    if any(math.dist(a,new_inner[0])<=.05 and math.dist(b,new_inner[1])<=.05 or math.dist(b,new_inner[0])<=.05 and math.dist(a,new_inner[1])<=.05 for p in source_paths for a,b in zip(p,p[1:])):raise ValueError('inner source pipe already represented')
    source_paths.append(new_inner)
    # Independent graph T rays remain mandatory; importing lazily avoids an
    # import cycle when the inventory consumes this reconstruction later.
    from crossview_equipment_branch_inventory import native_tee
    other_id=edge['end_node_id'] if edge['start_node_id']==equipment else edge['start_node_id']
    tee=native_tee(doc,graph,other_id,hashes['source_sha256'],hashes['graph_sha256'])
    return dict(edge_id=eid,equipment_id=equipment,system=edge['system'],source_insert_handle=root.dxf.handle,
        native_caption_handle=captions[0].dxf.handle,source_geometry_scope='selected native block chain; original logical equipment identity retained',
        original_path_coverage=coverage,removed_display_anchor_span=span,source_paths=source_paths,native_circle_evidence=circle,
        native_joint_evidence=joints,native_tee_evidence=tee,omission=omitted,
        joint_symbol=dict(source_chain=match['joint_chain'],contacts=[match['outer_contact'],match['inner_contact']],graphic_span=match['graphic_span'],physical_length_mm=None),
        inner_source_line_chain=match['inner_line_chain'],equipment_circle_chain=match['circle_chain'],offset_contact=offset,physical_port_verified=False,human_accepted=False)


def reconstruct(doc,graph,inventory,policy,hashes):
    if any(policy.get(k)!=v for k,v in hashes.items()):raise ValueError('stale native block branch policy')
    if graph.get('crossViewAttributeFusion') or any(e.get('cross_view_attributes') for e in graph['edges']):raise ValueError('reconstruct local topology before cross-view attribute fusion')
    if graph.get('sourceNativeBlockBranchReconstruction'):raise ValueError('native block branches already reconstructed')
    _inventory(graph,inventory)
    selected=policy.get('edge_ids')
    if not isinstance(selected,list) or not selected or len(set(selected))!=len(selected):raise ValueError('invalid branch selections')
    if fingerprint(doc.blocks[policy['joint_block']])!=policy['joint_fingerprint_sha256']:raise ValueError('native joint fingerprint changed')
    by={e['edge_id']:e for e in graph['edges']};records=[];pending=[]
    if not set(selected)<=by.keys():raise ValueError('selected branch absent')
    for eid in selected:
        try:records.append(probe(doc,graph,inventory,eid,policy,hashes))
        except (ValueError,KeyError,TypeError) as exc:pending.append(dict(edge_id=eid,reason=str(exc)))
    if len(records)!=policy['expected_reconstructed_edges'] or {r['edge_id'] for r in pending}!=set(policy['expected_pending_edges']):raise ValueError('native branch reconstruction scope differs; inspect source diagnostics')
    if {r['edge_id'] for r in records if r['offset_contact']}!=set(policy.get('_verified_offset_controls',{})):raise ValueError('inherited offset scope not consumed exactly')
    # Existing component identities are conserved; reject shared endpoint chains.
    for key in ('inner_source_line_chain','equipment_circle_chain'):
        values=[tuple(r[key]) for r in records]
        if len(set(values))!=len(values):raise ValueError('multiple branches claim one native endpoint chain')
    joint_chains=[tuple(r['joint_symbol']['source_chain']) for r in records]
    if len(set(joint_chains))!=len(joint_chains):raise ValueError('multiple branches claim one native joint')
    out=copy.deepcopy(graph);edges={e['edge_id']:e for e in out['edges']}
    for r in records:
        e=edges[r['edge_id']];before=copy.deepcopy(e)
        for key in ('source_path_coverage','source_device_extension','source_block_equipment_attachment','source_omission_length_status'):
            e.pop(key,None)
        paths=r['source_paths'];length=sum(math.dist(a,b) for path in paths for a,b in zip(path,path[1:]))
        e.update(attribute_paths=paths,path_points=copy.deepcopy(paths[0]),path_length=length,source_path_length=length,drawing_path_length=length,
            path_length_complete=False,path_length_scope='native_pipe_paths_only_omission_joint_and_equipment_lengths_unknown',physical_length='unknown')
        # Replay coverage of every reconstructed path; no symbol spans count as
        # pipe length. This records hashes of projections, not an edited source.
        current=projected_coverage(doc,out,e['edge_id'],hashes['source_sha256'])
        if any(s['status']!='single_source_line_covers' for p in current for s in p['coverage']['segments']):raise ValueError('new native source paths lack unique coverage')
        r.update(original_edge=before,reconstructed_path_coverage=current,status='native_block_branch_paths_reconstructed_not_physical_ports',
            source_path_length=length,original_drawing_path_length=before.get('drawing_path_length',before.get('path_length')))
        e['source_native_block_branch']=dict(edge_id=e['edge_id'],equipment_id=r['equipment_id'],system=e['system'],source_sha256=hashes['source_sha256'],
            source_insert_handle=r['source_insert_handle'],inner_source_line_chain=r['inner_source_line_chain'],equipment_circle_chain=r['equipment_circle_chain'],
            omitted_length_mm=None,joint_length_mm=None,physical_port_verified=False,human_accepted=False,
            endpoint_snapshot=dict(start_node_id=e['start_node_id'],end_node_id=e['end_node_id'],system=e['system'],attribute_paths=copy.deepcopy(paths)))
    affected={r['edge_id'] for r in records};attachment=out.get('sourceBlockEquipmentAttachment')
    if attachment and any(m['edge_id'] in affected for m in attachment.get('mappings',[])):
        out['sourceBlockEquipmentAttachmentHistory']=copy.deepcopy(attachment)
        attachment['mappings']=[m for m in attachment['mappings'] if m['edge_id'] not in affected]
    out['sourceNativeBlockBranchReconstruction']=dict(status='native_block_source_paths_reconstructed_hil_pending',**hashes,records=records,pending=pending,
        equipment_and_components_conserved=True,physical_ports_verified=False,human_accepted=False)
    out['derivedEvidenceInvalidation']=dict(previous=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),reason='source paths rebuilt from native joint and omission evidence',
        affected_edges=sorted(affected),recompute=['source_comparison','source_lengths','diameter_inheritance','crossview_mapping','attribute_fusion','human_acceptance'])
    out.setdefault('metadata',{}).update(source_sha256=hashes['source_sha256'],hil_ready=False,graph_complete=False,review_status='unreviewed_after_native_block_branch_reconstruction')
    return out


def implementation_hashes():
    names=['reconstruct_native_block_branches.py','native_path_coverage_audit.py','native_device_circle_lines.py','native_nested_joint_evidence.py','native_junction_ray_evidence.py','native_equipment_body.py','native_offset_circle_candidates.py','repair_exploded_joint_ownership.py','crossview_equipment_branch_inventory.py','source_readability.py']
    return {n:sha(Path(__file__).with_name(n)) for n in names}


def compute(paths,policy):
    hashes={k+'_sha256':sha(paths[k]) for k in ('source','graph','inventory')}
    if any(policy.get(k)!=v for k,v in hashes.items()):raise ValueError('native branch input differs')
    graph=load(paths['graph']);doc,preflight=read_source(paths['source'])
    if graph.get('sourceConfirmedGapJoints'):
        from attach_confirmed_gap_joints import verify_output
        if verify_output(Path(paths['graph']).parent)['output_graph_sha256']!=hashes['graph_sha256']:raise ValueError('native block parent differs')
    with Path(paths['inventory']).open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
    if '_verified_offset_controls' in policy:raise ValueError('offset controls must be independently loaded from pinned historical inputs')
    runtime_policy=dict(policy,_verified_offset_controls=inherited_offset_controls(paths,policy,hashes['source_sha256']))
    return reconstruct(doc,graph,inventory,runtime_policy,hashes),preflight


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'native-block-branch-reconstruction-audit.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('stale native block branch implementation')
    for spec in receipt['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('stale native block branch input')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result,_=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=receipt['output_graph_sha256']:raise ValueError('native block branch replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['inventory']).read_bytes():raise ValueError('native block component CSV changed')
    return receipt


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','inventory','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    for key in ('offset-policy','offset-audit'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args();paths={key:getattr(args,key) for key in ('source','graph','inventory','policy')}
    for key in ('offset_policy','offset_audit'):
        if getattr(args,key) is not None:paths[key]=getattr(args,key)
    if args.output.exists():raise FileExistsError(args.output)
    result,preflight=compute(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'graph_with_edges.json').write_bytes(encode(result));shutil.copyfile(args.inventory,args.output/'edge_device_instances.csv')
    receipt=dict(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),
        parent_graph=dict(path=str(args.graph.resolve()),sha256=sha(args.graph)),output_graph_sha256=sha(args.output/'graph_with_edges.json'),source_preflight=preflight,human_accepted=False,hil_ready=False)
    (args.output/'native-block-branch-reconstruction-audit.json').write_bytes(encode(receipt))
    state=result['sourceNativeBlockBranchReconstruction'];print(json.dumps(dict(reconstructed=len(state['records']),pending=state['pending'],human_accepted=False)))

if __name__=='__main__':main()
