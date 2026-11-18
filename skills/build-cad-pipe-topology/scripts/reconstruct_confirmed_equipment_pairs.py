"""Reconstruct source- and Pair-bound equipment/branch/main connections."""
import argparse,collections,copy,csv,hashlib,json,math,subprocess,sys,tempfile
from pathlib import Path
from source_readability import read_source
from source_terminal_pair_inventory import scan,LAYERS
from native_equipment_body import body_straight_segments
from native_line_path_evidence import _on
from repair_confirmed_circle_junctions import pos,slice_path
from split_native_main_paths import split_main
from confirmed_equipment_interfaces import apply as attach_interfaces
from edge_endpoint_semantics import reconcile

DECISION='设备归属与两路同系统连接均成立'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
encode=lambda d:(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def prepare(doc,graph,reviewed,manifest,reply,policy,source_hash,graph_hash):
    if policy['source_sha256']!=source_hash or policy['graph_sha256']!=graph_hash or graph['metadata']['source_sha256']!=source_hash or manifest['source_sha256']!=source_hash:
        raise ValueError('current source or graph changed')
    qs={q['id']:(q,s['image']['sha256']) for s in reply['sections'] for q in s['questions']}
    if len(qs)!=sum(len(s['questions']) for s in reply['sections']):raise ValueError('duplicate reply question')
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    oldnodes={n['node_id']:n for n in reviewed['nodes']};oldedges={e['edge_id']:e for e in reviewed['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph IDs')
    inventory_policy=dict(policy['inventory_scope'],source_sha256=source_hash,graph_sha256=graph_hash)
    inventory=scan(doc,graph,inventory_policy,source_hash,graph_hash)
    inv={n['node_id']:n for n in inventory['equipment']};selections=policy['equipment'];connections=[];seen=set();questions=[]
    if not selections or len({s['equipment_id'] for s in selections})!=len(selections):raise ValueError('empty or duplicate equipment selection')
    if {s['equipment_id'] for s in selections}!={did for image in manifest['images'] for did in image['equipment']}:
        raise ValueError('one-to-one picture scope must be complete')
    for s in selections:
        did=s['equipment_id'];device=nodes[did];q,image=qs.get(s['question_id'],({},None))
        if did not in q.get('text','') or q.get('answer',{}).get('decision')!=DECISION:raise ValueError('missing scoped equipment reply')
        images=[x for x in manifest['images'] if did in x['equipment'] and x['sha256']==image]
        if len(images)!=1 or device!=oldnodes.get(did) or device.get('source_handle')!=s['equipment_handle']:raise ValueError('reviewed device or image scope changed')
        window=images[0]['window']
        visible=lambda p:window[0]<=p[0]<=window[1] and window[2]<=p[1]<=window[3]
        if not visible([device['x'],device['y']]):raise ValueError('device outside reviewed picture')
        source=doc.entitydb.get(s['equipment_handle'])
        if not source or source.dxftype()!='INSERT' or source not in doc.modelspace():raise ValueError('native equipment block missing')
        segments,unsupported=body_straight_segments(source)
        if unsupported or not segments:raise ValueError('equipment native body incomplete')
        points=[p for a,b in segments for p in (a,b)];box=[min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)]
        captions=[e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text().strip()==did and box[0]<=e.dxf.insert.x<=box[1] and box[2]<=e.dxf.insert.y<=box[3]]
        if len(captions)!=1:raise ValueError('native device caption missing or ambiguous')
        bindings=s['connections']
        if len(bindings)!=2 or {b['system'] for b in bindings}!={'supply','return'}:raise ValueError('equipment must retain independent supply/return')
        chosen={b['system']:b['interface_id'] for b in bindings}
        if not any(p['supply_node']==chosen['supply'] and p['return_node']==chosen['return'] and not p['terminal_pairing_ambiguous'] for p in inv[did]['pair_candidates']):
            raise ValueError('selected native paired glyphs not reproduced')
        for b in bindings:
            interface=nodes[b['interface_id']];branch=edges[b['edge_id']];main=edges[b['main_edge_id']]
            if interface!=oldnodes.get(b['interface_id']) or branch!=oldedges.get(b['edge_id']) or main!=oldedges.get(b['main_edge_id']):raise ValueError('selected reviewed source route changed')
            if b['interface_id'] in seen:raise ValueError('interface assigned twice')
            seen.add(b['interface_id']);system=b['system']
            if interface['system']!=system or branch['system']!=system or main['system']!=system:raise ValueError('mixed system pair')
            terminal_id=branch['end_node_id'] if branch['start_node_id']==interface['node_id'] else branch['start_node_id']
            terminal=nodes[terminal_id]
            if (terminal.get('subtype')!='unresolved_source_terminal'
                or sum(terminal_id in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1):raise ValueError('branch end is not an isolated unresolved terminal')
            if any(b['circle_handle'] in x.get('source_marker_handles',[]) for x in graph.get('boundary_anchors',[])):raise ValueError('confirmed non-node boundary protected')
            circle,line,native_main=[doc.entitydb.get(b[k]) for k in ('circle_handle','branch_handle','main_handle')]
            if (not circle or not circle.is_alive or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace()
                or any(not e or not e.is_alive or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=LAYERS[system] for e in (line,native_main))
                or b['branch_handle'] not in branch['source_handles'] or b['main_handle'] not in main['source_handles']):raise ValueError('native circle or typed pipes changed')
            if tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('unsupported circle OCS in this scoped paired reconstruction')
            center=[circle.dxf.center.x,circle.dxf.center.y];rim=[terminal['x'],terminal['y']]
            if not all(visible(p) for p in ([interface['x'],interface['y']],center,rim)):raise ValueError('connection outside reviewed picture')
            if abs(math.dist(center,rim)-circle.dxf.radius)>.05 or min(math.dist(rim,[v.x,v.y]) for v in (line.dxf.start,line.dxf.end))>.05:
                raise ValueError('branch no longer reaches the native circle rim')
            a,c=([v.x,v.y] for v in (line.dxf.start,line.dxf.end));u=[c[i]-a[i] for i in (0,1)]
            ma,mb=([v.x,v.y] for v in (native_main.dxf.start,native_main.dxf.end));v=[mb[i]-ma[i] for i in (0,1)]
            cross=lambda x,y:x[0]*y[1]-x[1]*y[0]
            denominator=cross(u,v)
            if abs(denominator)<1e-8:raise ValueError('branch and main do not form distinct rays')
            t=cross([ma[i]-a[i] for i in (0,1)],v)/denominator;anchor=[a[i]+t*u[i] for i in (0,1)]
            if abs(cross([center[i]-a[i] for i in (0,1)],u))/math.hypot(*u)>.05:raise ValueError('circle not on branch axis')
            offset=math.dist(center,anchor);limit=b['maximum_circle_main_offset_drawing_units']
            if not math.isfinite(limit) or limit<0 or limit>circle.dxf.radius*.02 or offset>limit+.00001 or not _on(anchor,ma,mb,.05):
                raise ValueError('native main offset outside explicit small-circle scope')
            s_pos=pos(main['path'],anchor);total=sum(math.dist(x,y) for x,y in zip(main['path'],main['path'][1:]))
            if not .05<s_pos<total-.05:raise ValueError('landing point not inside the proven main')
            neighbours=[slice_path(main['path'],0,s_pos)[-2],slice_path(main['path'],s_pos,total)[1]]
            for p in neighbours:
                hits=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS[system] and _on(anchor,[e.dxf.start.x,e.dxf.start.y],[e.dxf.end.x,e.dxf.end.y],.05) and _on(p,[e.dxf.start.x,e.dxf.start.y],[e.dxf.end.x,e.dxf.end.y],.05)]
                if len(hits)!=1 or hits[0] not in main['source_handles']:raise ValueError('native main ray missing or ambiguous')
            directions=[]
            for p in neighbours+[rim]:
                delta=[p[i]-anchor[i] for i in (0,1)];length=math.hypot(*delta)
                if length<=.05:raise ValueError('zero T ray')
                direction=[x/length for x in delta]
                if any(sum(x*y for x,y in zip(direction,other))>math.cos(math.radians(.1)) for other in directions):raise ValueError('T requires three distinct native rays')
                directions.append(direction)
            connections.append(dict(b,equipment_id=did,equipment_handle=s['equipment_handle'],interface_handle=interface['source_handle'],
                terminal_id=terminal_id,source_handle=b['circle_handle'],point=anchor,source_circle_center=center,source_rim=rim,
                circle_layer=circle.dxf.layer,circle_layer_matches_lines=circle.dxf.layer==LAYERS[system],
                actual_circle_main_offset=offset,question_id=q['id'],answer=q['answer'],pair_sha256=image,native_caption_handle=captions[0].dxf.handle,
                native_circle_center_wcs=list(circle.dxf.center),native_branch_endpoints_wcs=[list(line.dxf.start),list(line.dxf.end)],
                native_main_endpoints_wcs=[list(native_main.dxf.start),list(native_main.dxf.end)],native_z_is_not_floor_evidence=True))
        questions.append(dict(question_id=q['id'],question=q['text'],answer=q['answer']))
    # This ordering check reproduces the selected one-to-one picture layout;
    # the explicit replies, not rank or proximity, authorize the bindings.
    order=sorted(selections,key=lambda s:nodes[s['equipment_id']]['x'])
    for system in ('supply','return'):
        xs=[nodes[next(b['interface_id'] for b in s['connections'] if b['system']==system)]['x'] for s in order]
        if any(b<=a for a,b in zip(xs,xs[1:])):raise ValueError('selected interface order differs from the reviewed layout')
    return connections,questions

def rebuild(doc,graph,rows,connections,questions,policy,source_hash,graph_hash):
    out=copy.deepcopy(graph);result_rows=copy.deepcopy(rows);edges={e['edge_id']:e for e in out['edges']};nodes={n['node_id']:n for n in out['nodes']}
    groups=collections.defaultdict(list);audit=[]
    for c in connections:groups[c['main_edge_id']].append(c)
    for mid,cuts in groups.items():
        main=edges.pop(mid);children,result_rows,tees=split_main(doc,main,result_rows,cuts,graph_hash,prefix='EQUIP')
        for child in children:
            if child['edge_id'] in edges:raise ValueError('new main edge ID collision')
            edges[child['edge_id']]=child
        for c,tee in tees:
            if tee in nodes:raise ValueError('new T ID collision')
            branch=edges[c['edge_id']];terminal=nodes.pop(c['terminal_id']);side='start' if branch['start_node_id']==c['terminal_id'] else 'end'
            branch[side+'_node_id']=tee;branch.pop(side+'_port_id',None)
            branch['path']=([c['point']]+branch['path']) if side=='start' else (branch['path']+[c['point']]);branch['path_points']=copy.deepcopy(branch['path'])
            proof=dict(c,confirmation_basis='explicit_equipment_pair_reply',source_sha256=source_hash,input_graph_sha256=graph_hash,
                physical_port_verified=False,physical_length='unknown',circle_main_offset_is_physical_length=False)
            branch['source_confirmed_equipment_pair_circle']=proof;branch['path_length_complete']=False
            branch['path_length_scope']='source_drawn_pipe_only_confirmed_circle_and_equipment_connector_unknown'
            nodes[tee]=dict(node_id=tee,node_type='tee',subtype='physical_tee',system=c['system'],floor=terminal['floor'],x=c['point'][0],y=c['point'][1],label=tee,
                source_handles=[c['circle_handle'],c['main_handle'],c['branch_handle']],source_confirmed_equipment_pair_circle=proof)
            audit.append(dict(equipment_id=c['equipment_id'],system=c['system'],tee=tee,circle_handle=c['circle_handle'],branch_edge=branch['edge_id'],
                retired_terminal=c['terminal_id'],main_source_edge=mid,main_child_edges=[e['edge_id'] for e in children],
                source_circle_center=c['source_circle_center'],topology_anchor=c['point'],actual_circle_main_offset=c['actual_circle_main_offset']))
    out['nodes']=list(nodes.values());out['edges']=list(edges.values());out,_=reconcile(out)
    geometry_hash=hashlib.sha256(encode(out)).hexdigest();ip=dict(policy['inventory_scope'],source_sha256=source_hash,graph_sha256=geometry_hash)
    inventory=scan(doc,out,ip,source_hash,geometry_hash)
    ap=dict(source_sha256=source_hash,graph_sha256=geometry_hash,connections=[{k:c[k] for k in ('equipment_id','equipment_handle','interface_id','interface_handle','edge_id','system')} for c in connections],
        confirmation=dict(confirmed_by='user',question='Scoped batch equipment interface ownership and same-system main contacts',answer=DECISION,records=questions,reply_sha256=policy['reply_sha256']))
    out,attachment=attach_interfaces(out,ap,inventory,source_hash,geometry_hash)
    for record in audit:
        incident=[e for e in out['edges'] if record['tee'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=3 or any(e['system']!=record['system'] for e in incident):raise ValueError('rebuilt equipment T invariant failed')
    expected=collections.Counter((r['device_name'],r['source_handle'],r['equipment_type']) for r in rows)
    if expected!=collections.Counter((r['device_name'],r['source_handle'],r['equipment_type']) for r in result_rows):raise ValueError('component source identity changed')
    for e in out['edges']:
        assigned=[r for r in result_rows if r['edge_id']==e['edge_id']]
        if collections.Counter(r['device_name'] for r in assigned)!=collections.Counter(e.get('equipment_names',[])):raise ValueError('component assignment not conserved')
    out['confirmedEquipmentPairReconstruction']=dict(source_sha256=source_hash,input_graph_sha256=graph_hash,records=audit,
        questions=questions,supply_return_independent=True,physical_ports_verified=False,physical_lengths_complete=False)
    out['derivedEvidenceInvalidation']=dict(input_graph_sha256=graph_hash,
        reason='confirmed equipment ownership and main landing points changed node/edge semantics and segmentation',
        recompute=['source_comparison','source_coverage','diameter_inheritance','segment_dimensions','cross_view_mapping','human_acceptance'],
        previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),historical_annotations_preserved=True)
    return out,result_rows,dict(records=audit,attachment=attachment,geometry_intermediate_sha256=geometry_hash,hil_ready=False)

def implementation_hashes():
    return [sha(Path(__file__).with_name(n)) for n in ('reconstruct_confirmed_equipment_pairs.py','split_native_main_paths.py',
        'repair_confirmed_circle_junctions.py','confirmed_equipment_interfaces.py','source_terminal_pair_inventory.py','edge_endpoint_semantics.py','native_line_path_evidence.py','native_equipment_body.py')]

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'equipment-pair-reconstruction-audit.json')
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale equipment pair implementation')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale equipment pair input')
    if sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256']:raise ValueError('stale equipment output graph')
    with tempfile.TemporaryDirectory() as folder:
        out=Path(folder)/'replay';cmd=[sys.executable,'-X','utf8',str(Path(__file__))]
        for key,item in audit['inputs'].items():cmd+=['--'+key.replace('_','-'),item['path']]
        subprocess.run(cmd+['--output',str(out)],check=True,stdout=subprocess.DEVNULL)
        for name in ('graph_with_edges.json','assigned_edge_device_instances.csv'):
            if sha(directory/name)!=sha(out/name):raise ValueError('equipment pair reconstruction replay differs')
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','reviewed-graph','manifest','reply','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();policy=load(a.policy);keys=('source','graph','devices','reviewed_graph','manifest','reply')
    for key in keys:
        if sha(getattr(a,key))!=policy[key+'_sha256']:raise ValueError('changed '+key)
    manifest=load(a.manifest)
    if manifest['graph_sha256']!=sha(a.reviewed_graph):raise ValueError('reviewed graph mismatch')
    for item in manifest['images']:
        if sha(a.manifest.parent/item['image'])!=item['sha256']:raise ValueError('reviewed equipment Pair changed')
    if a.output.exists():raise ValueError('output exists')
    doc,preflight=read_source(a.source);graph=load(a.graph)
    with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    connections,questions=prepare(doc,graph,load(a.reviewed_graph),manifest,load(a.reply),policy,sha(a.source),sha(a.graph))
    out,rows,audit=rebuild(doc,graph,rows,connections,questions,policy,sha(a.source),sha(a.graph))
    a.output.mkdir(parents=True);gp=a.output/'graph_with_edges.json';gp.write_bytes(encode(out))
    with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    audit.update(output_graph_sha256=sha(gp),implementation_sha256=implementation_hashes(),source_preflight=preflight['status'],
        inputs={key:dict(path=str(getattr(a,key).resolve()),sha256=sha(getattr(a,key))) for key in keys+('policy',)})
    (a.output/'equipment-pair-reconstruction-audit.json').write_bytes(encode(audit))
    print(json.dumps(dict(equipment=len(policy['equipment']),connections=len(connections),nodes=len(out['nodes']),edges=len(out['edges']),components=len(rows),hil_ready=False)))

if __name__=='__main__':main()
