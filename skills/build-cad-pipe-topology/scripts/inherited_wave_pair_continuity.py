"""Reconstruct same-system paired drawing breaks from real expert controls.

Preserve split-main ancestry, components and raw paths. A translated native
control can explain an off-centre wave; no global contact tolerance is enlarged.
"""
import argparse,copy,csv,hashlib,math
from collections import Counter
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_line_path_evidence import LAYERS
from native_path_coverage_audit import audit as line_audit
from reconstruct_native_block_branches import projected_coverage
from wave_omission_candidates import block_fingerprint,screen
from crossview_equipment_branch_inventory import index_graph
from confirm_wave_drawing_convention import STATEMENT
from edge_endpoint_semantics import reconcile
from reconcile_pending_main_continuity import validate_references

MODE='native_inherited_wave_pair_continuity_v1'


def contact(doc,edge,point,system):
    hits=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer!=LAYERS[system]:continue
        for end in (line.dxf.start,line.dxf.end):
            if math.dist(list(end)[:2],point)<=.05:hits.append((line,end))
    if len(hits)!=1 or hits[0][0].dxf.handle not in edge.get('source_handles',[]):raise ValueError('wave endpoint needs one real native pipe end')
    line,end=hits[0]
    if not all(math.isfinite(v) for p in (line.dxf.start,line.dxf.end) for v in p):raise ValueError('nonfinite native wave pipe')
    if sum(math.dist(point,q)<=.05 for path in edge['attribute_paths'] for q in (path[0],path[-1]))!=1:raise ValueError('wave contact is not one actual source path endpoint')
    return dict(source_line_handle=line.dxf.handle,XYZ=list(end),line_XYZ=[list(line.dxf.start),list(line.dxf.end)])


def wave_feature(doc,handle,point,xyz,u,block_name,fingerprint):
    wave=doc.entitydb.get(handle)
    if (wave is None or wave not in doc.modelspace() or wave.dxftype()!='INSERT' or wave.dxf.name!=block_name
        or block_fingerprint(doc.blocks[wave.dxf.name])!=fingerprint):raise ValueError('wave instance or native block differs')
    parts=list(wave.virtual_entities())
    if len(parts)!=1 or parts[0].dxftype()!='LWPOLYLINE' or len(parts[0])!=3 or parts[0].closed:raise ValueError('unsupported transformed wave')
    part=parts[0];vertices=[list(p) for p in part.vertices_in_wcs()];normal=list(part.dxf.get('extrusion',(0,0,1)))
    if abs(normal[0])>.00001 or abs(normal[1])>.00001 or abs(abs(normal[2])-1)>.00001:raise ValueError('unsupported wave plane')
    v=[-u[1],u[0]];features=[]
    for p,entry in zip(vertices,part.get_points('xyb')):
        if not all(math.isfinite(x) for x in p):raise ValueError('nonfinite transformed wave')
        delta=[p[0]-point[0],p[1]-point[1]]
        features.append([sum(delta[i]*u[i] for i in (0,1)),sum(delta[i]*v[i] for i in (0,1)),p[2]-xyz[2],float(entry[2])*normal[2]])
    return dict(wave_handle=handle,source_insert_XYZ=list(wave.dxf.insert),native_vertices_XYZ=vertices,
        source_linear_pose={k:wave.dxf.get(k,d) for k,d in [('rotation',0),('xscale',1),('yscale',1),('zscale',1)]},
        native_plane=normal,relative_pipe_frame=features,centre_to_pipe_end_xy=math.dist(vertices[1][:2],point))


def pair_geometry(doc,edges,points,waves,system,block_name,fingerprint):
    gap=math.dist(*points)
    if not .05<gap<=350:raise ValueError('paired omission pipe-end span outside calibrated scope')
    u=[(points[1][i]-points[0][i])/gap for i in (0,1)]
    contacts=[contact(doc,e,p,system) for e,p in zip(edges,points)]
    features=[wave_feature(doc,h,p,c['XYZ'],u,block_name,fingerprint) for h,p,c in zip(waves,points,contacts)]
    # A missing native graph segment is not a drawing omission. Preserve
    # ordinary opposite-service crossings, but reject another same-service pipe
    # occupying this interval before using an abbreviated drawing convention.
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer!=LAYERS[system]:continue
        spans=[]
        for p in (line.dxf.start,line.dxf.end):
            delta=[p[i]-points[0][i] for i in (0,1)];along=sum(delta[i]*u[i] for i in (0,1));across=abs(delta[0]*u[1]-delta[1]*u[0]);spans.append((along,across))
        if max(x[1] for x in spans)<=.05 and min(gap,max(x[0] for x in spans))-max(0,min(x[0] for x in spans))>.05:
            raise ValueError('unexplained native same-system pipe occupies the omission')
    return dict(gap_native_units=gap,pipe_end_Z_delta=contacts[1]['XYZ'][2]-contacts[0]['XYZ'][2],contacts=contacts,waves=features)


def same_geometry(target,control,reflection=1):
    if abs(target['gap_native_units']-control['gap_native_units'])>.05 or abs(target['pipe_end_Z_delta']-control['pipe_end_Z_delta'])>.05:return False
    for a,b in zip(target['waves'],control['waves']):
        for x,y in zip(a['relative_pipe_frame'],b['relative_pipe_frame']):
            expected=[y[0],y[1]*reflection,y[2],y[3]*reflection]
            if any(abs(v-w)>(1e-8 if i==3 else .05) for i,(v,w) in enumerate(zip(x,expected))):return False
    return True


def control_evidence(doc,graph,confirmation,issue,source_hash,confirmation_hash,block_name,fingerprint):
    expert=graph.get('expertWaveOmissionRepair',{});convention=graph.get('expertWaveDrawingConvention',{})
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash or expert.get('source_sha256')!=source_hash
        or issue.get('sourceHashes',{}).get('main_dxf')!=source_hash or issue.get('issue',{}).get('label')!=expert.get('issue')
        or issue['issue'].get('note')!=expert.get('expert_note') or confirmation.get('statement')!=STATEMENT
        or confirmation.get('full_graph_accepted') is not False or convention.get('confirmation_sha256')!=confirmation_hash
        or convention.get('full_graph_accepted') is not False):raise ValueError('real expert wave controls and clarification required')
    simple=lambda row:frozenset(row.get('wave_handles',row.get('source_wave_handles',[])))
    declared={simple(row):row['system'] for row in confirmation['wave_pairs']}
    if declared!={simple(row):row['system'] for row in convention['pairs']}:raise ValueError('expert clarification scope changed')
    original={simple(row):row['system'] for row in expert['steps']};allowed=dict(original)
    if set(original)&set(declared):raise ValueError('overlapping expert wave controls')
    allowed.update(declared);results=[]
    for key,system in allowed.items():
        hits=[]
        for edge in graph['edges']:
            meta=edge.get('source_wave_omission',{});handles=meta.get('wave_handles',meta.get('source_insert_handles',[]))
            if frozenset(handles)==key:hits.append((edge,meta,handles))
        if len(hits)!=1:raise ValueError('expert paired source paths missing or duplicate')
        edge,meta,handles=hits[0];points=meta.get('source_endpoints',meta.get('endpoints'))
        if (edge['system']!=system or len(edge['attribute_paths'])!=2 or edge.get('path_length_complete') is not False
            or meta.get('physical_length')!='unknown' or len(handles)!=2 or len(points or [])!=2):raise ValueError('expert control source paths or unknown length changed')
        if key in declared and (meta.get('confirmation_sha256')!=confirmation_hash or meta.get('scoped_expert_convention_confirmed') is not True):raise ValueError('calibrated control lacks actual expert clarification')
        if key in original and meta.get('expert_issue')!=expert['issue']:raise ValueError('original expert issue differs')
        coverage=projected_coverage(doc,graph,edge['edge_id'],source_hash)
        if any(s['status']!='single_source_line_covers' for p in coverage for s in p['coverage']['segments']):raise ValueError('expert control paths lack native coverage')
        for reverse in (False,True):
            ps=list(reversed(points)) if reverse else points;hs=list(reversed(handles)) if reverse else handles
            results.append(dict(control_edge=edge['edge_id'],system=system,source_wave_handles=hs,
                control_source_sha256=source_hash,control_confirmation_sha256=confirmation_hash,
                evidence_basis='original_expert_issue' if key in original else 'pictured_expert_drawing_convention',native_path_coverage=coverage,
                native=pair_geometry(doc,[edge,edge],ps,hs,system,block_name,fingerprint)))
    if {row['system'] for row in results}!={'supply','return'}:raise ValueError('both-service native control scope required')
    return results


def inspect_pairs(doc,graph,controls,policy,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);specs=policy.get('pairs',[]);used=[];result=[]
    if not specs or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('explicit current native wave scope required')
    for spec in specs:
        nids=spec.get('nodes',[]);waves=spec.get('wave_handles',[])
        if len(nids)!=2 or len(waves)!=2 or len(set(nids))!=2 or len(set(waves))!=2:raise ValueError('two separate native endpoints and marks required')
        used.extend(nids);ns=[nodes[nid] for nid in nids]
        if (any(n.get('subtype')!='unresolved_source_terminal' or n.get('node_type')!='virtual_equipment' or len(adj[n['node_id']])!=1 for n in ns)
            or ns[0]['system']!=ns[1]['system'] or ns[0]['system'] not in LAYERS or ns[0]['floor']!=ns[1]['floor']):raise ValueError('wave terminals must be same-service same-floor degree one')
        es=[adj[nid][0] for nid in nids];system=ns[0]['system'];points=[[n['x'],n['y']] for n in ns]
        if es[0]['edge_id']==es[1]['edge_id'] or any(e['system']!=system or len(e['attribute_paths'])!=1 for e in es):raise ValueError('paired source paths are not independent')
        if spec.get('retained_edge') not in {e['edge_id'] for e in es}:raise ValueError('explicit retained source edge required')
        gap=math.dist(*points)
        if not math.isfinite(gap) or not .05<gap<=350:raise ValueError('wave pair span outside the independently calibrated source domain')
        u=[(points[1][i]-points[0][i])/gap for i in (0,1)]
        for index,(edge,p) in enumerate(zip(es,points)):
            path=edge['attribute_paths'][0];oriented=path if math.dist(p,path[0])<=.05 else list(reversed(path))
            if math.dist(p,oriented[0])>.05:raise ValueError('source path does not reach wave terminal')
            q=oriented[1];length=math.dist(p,q)
            if not math.isfinite(length) or length<=.05:raise ValueError('wave source endpoint has no nonempty outward ray')
            out=[(p[i]-q[i])/length for i in (0,1)]
            if sum(out[i]*u[i] for i in (0,1))*(1 if index==0 else -1)<.9999:raise ValueError('source paths do not face across their drawing break')
        native=pair_geometry(doc,es,points,waves,system,policy['block_name'],policy['block_fingerprint'])
        matches=[dict(control=row,reflection=reflection) for row in controls if row['system']==system for reflection in (1,-1) if same_geometry(native,row['native'],reflection)]
        if not matches:raise ValueError('paired native geometry lacks an independently confirmed control')
        # Check uniqueness against the raw source, including displaced marks.
        for side,p in enumerate(points):
            hits=[]
            for wave in doc.modelspace().query('INSERT'):
                if wave.dxf.name!=policy['block_name']:continue
                if math.dist(list(wave.dxf.insert)[:2],p)>max(w['centre_to_pipe_end_xy'] for w in native['waves'])+1:continue
                candidate=wave_feature(doc,wave.dxf.handle,p,native['contacts'][side]['XYZ'],u,policy['block_name'],policy['block_fingerprint'])
                trial=copy.deepcopy(native);trial['waves'][side]=candidate
                if any(same_geometry(trial,m['control']['native'],m['reflection']) for m in matches):hits.append(wave.dxf.handle)
            if hits!=[waves[side]]:raise ValueError('native wave identity ambiguous at calibrated offset')
        coverage=line_audit(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[e['edge_id'] for e in es]),source_hash,graph_hash)
        if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):raise ValueError('wave source pipe path lacks native coverage')
        result.append(dict(nodes=nids,wave_handles=waves,system=system,floor=ns[0]['floor'],edge_ids=[e['edge_id'] for e in es],
            retained_edge=spec['retained_edge'],native=native,matching_controls=matches,native_path_coverage=coverage,
            drawing_convention='long_pipe_drawing_break_no_additional_physical_property',physical_length_mm=None,human_accepted=False))
    if len(used)!=len(set(used)):raise ValueError('wave terminal reused')
    return result


def reconstruct(graph,devices,proofs,source_hash,graph_hash):
    out=copy.deepcopy(graph);rows=copy.deepcopy(devices);nodes,edges,_=index_graph(out);old_edges={e['edge_id']:copy.deepcopy(e) for e in out['edges']};mapping={};retired_nodes=[];steps=[]
    allowed={'edge_id','start_node_id','end_node_id','edge_type','system','start_floor','end_floor','path','attribute_paths','path_length','source_handles','equipment_counts','equipment_names','path_points','endpoint_semantics','start_port_id','end_port_id','split_source_edge'}
    for proof in proofs:
        ids=proof['edge_ids'];keep=proof['retained_edge'];other=next(eid for eid in ids if eid!=keep);keep_node=proof['nodes'][ids.index(keep)];other_node=proof['nodes'][ids.index(other)];a=edges[keep];b=edges[other]
        if set(a)-allowed or set(b)-allowed:raise ValueError('unhandled source edge fields in wave reconstruction')
        outer=lambda edge,nid:edge['end_node_id'] if edge['start_node_id']==nid else edge['start_node_id']
        start,end=outer(a,keep_node),outer(b,other_node)
        if start==end or start not in nodes or end not in nodes or start in proof['nodes'] or end in proof['nodes']:raise ValueError('wave reconstruction collapses a loop')
        orient=lambda edge,nid:copy.deepcopy(edge['path_points'] if edge['start_node_id']==nid else list(reversed(edge['path_points'])))
        merged=copy.deepcopy(a);merged.pop('split_source_edge',None)
        merged.update(start_node_id=start,end_node_id=end,path=orient(a,start)+orient(b,other_node),path_points=orient(a,start)+orient(b,other_node),
            attribute_paths=copy.deepcopy(a['attribute_paths']+b['attribute_paths']),path_length=a['path_length']+b['path_length'],path_length_complete=False,
            path_length_scope='source_drawn_pipe_only_inherited_wave_omission_length_unknown',connection_mode='source_inherited_wave_omission_unreviewed',
            source_handles=sorted(set(a['source_handles']+b['source_handles'])),equipment_names=a['equipment_names']+b['equipment_names'],
            equipment_counts=dict(Counter(a['equipment_counts'])+Counter(b['equipment_counts'])))
        for side,nid,edge in [('start',start,a),('end',end,b)]:
            old='start' if edge['start_node_id']==nid else 'end';merged.pop(side+'_port_id',None)
            if edge.get(old+'_port_id'):merged[side+'_port_id']=edge[old+'_port_id']
        typed,_=reconcile(dict(nodes=list(nodes.values()),edges=[merged]));merged=typed['edges'][0]
        merged['source_wave_omission']=dict(wave_handles=proof['wave_handles'],source_endpoints=[c['XYZ'][:2] for c in proof['native']['contacts']],
            drawing_convention='long_pipe_drawing_break',connectivity='continuous_same_pipe',physical_component=False,additional_physical_property=False,
            physical_length='unknown',calibration_scope='replayed_native_pair_against_real_expert_controls',human_accepted=False)
        merged['source_wave_constituents']=[dict(edge_id=eid,input_graph_sha256=graph_hash,edge_snapshot_sha256=hashlib.sha256(encode(old_edges[eid])).hexdigest(),edge_snapshot=old_edges[eid]) for eid in (keep,other)]
        edges[keep]=merged;del edges[other];mapping[other]=keep;retired_nodes.extend(proof['nodes'])
        for nid in proof['nodes']:del nodes[nid]
        steps.append(dict(proof,retired_edge=other,retired_nodes=proof['nodes']))
    retired=set(mapping)|set(retired_nodes)
    def stale(value):
        if isinstance(value,str):return value in retired
        if isinstance(value,dict):return any(k in retired or stale(v) for k,v in value.items())
        if isinstance(value,list):return any(stale(v) for v in value)
        return False
    for key,value in out.items():
        if key not in ('nodes','edges') and stale(value):raise ValueError('retired object referenced by current root '+key)
    for node in nodes.values():
        if stale(node):raise ValueError('retired object referenced by surviving node')
    for eid,edge in edges.items():
        if eid not in {p['retained_edge'] for p in proofs} and stale(edge):raise ValueError('retired object referenced by unrelated edge')
    for row in rows:row['edge_id']=mapping.get(row['edge_id'],row['edge_id'])
    if Counter(d['device_name'] for d in devices)!=Counter(d['device_name'] for d in rows) or len({d['device_name'] for d in rows})!=len(rows):raise ValueError('component identity lost or duplicated')
    for eid,edge in edges.items():
        ds=[row for row in rows if row['edge_id']==eid]
        if Counter(d['device_name'] for d in ds)!=Counter(edge.get('equipment_names',[])) or Counter(d['equipment_type'] for d in ds)!=Counter(edge.get('equipment_counts',{})):raise ValueError('wave component assignment not conserved')
    if any(row['edge_id'] not in edges for row in rows):raise ValueError('orphan wave component')
    out['nodes']=list(nodes.values());out['edges']=list(edges.values());out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False)
    out['sourceInheritedWavePairContinuity']=dict(mode=MODE,source_sha256=source_hash,input_graph_sha256=graph_hash,records=steps,edge_id_mapping=mapping,
        retired_node_snapshots=[n for n in graph['nodes'] if n['node_id'] in retired_nodes],
        dependent_mapping_attributes_and_HIL_invalidated=True,unpaired_continuations_inferred=False,physical_lengths_assigned=0,human_accepted=False)
    validate_references(out)
    return out,rows


def compute(paths,policy):
    for key in ('source','graph','devices','control_source','control_graph','control_confirmation','control_issue','control_image'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('inherited wave dependency changed '+key)
    from calibrated_ownership_scope_composition import verify_ownership_output
    from reconstruct_sideview_equipment_ownership import verify_output as verify_control
    if Path(paths['devices']).resolve()!=Path(paths['graph']).resolve().parent/'assigned_edge_device_instances.csv':raise ValueError('canonical parent component table required')
    parent=verify_ownership_output(Path(paths['graph']).parent);control_parent=verify_control(Path(paths['control_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['graph']) or control_parent['output_graph_sha256']!=sha(paths['control_graph']):raise ValueError('native wave parents differ')
    doc,preflight=read_source(paths['source']);control_doc,control_preflight=read_source(paths['control_source'])
    graph=load(paths['graph']);control=load(paths['control_graph']);confirmation=load(paths['control_confirmation']);issue=load(paths['control_issue'])
    if confirmation['image_sha256']!=sha(paths['control_image']):raise ValueError('expert wave photo changed')
    controls=control_evidence(control_doc,control,confirmation,issue,sha(paths['control_source']),sha(paths['control_confirmation']),policy['control_block_name'],policy['block_fingerprint'])
    proofs=inspect_pairs(doc,graph,controls,policy,sha(paths['source']),sha(paths['graph']))
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;devices=list(reader)
    result,rows=reconstruct(graph,devices,proofs,sha(paths['source']),sha(paths['graph']))
    return result,rows,fields,dict(source_preflight=preflight,control_preflight=control_preflight,expert_control_pairs=len(controls)//2,pairs=len(proofs),
        nodes_before=len(graph['nodes']),nodes_after=len(result['nodes']),edges_before=len(graph['edges']),edges_after=len(result['edges']),components=len(rows))


def implementation_hashes():
    from calibrated_ownership_scope_composition import implementation_hashes as parent_hashes
    from reconstruct_sideview_equipment_ownership import implementation_hashes as control_hashes
    result=parent_hashes();result.update(control_hashes())
    for name in (Path(__file__).name,'wave_omission_candidates.py','confirm_wave_drawing_convention.py','native_path_coverage_audit.py',
        'reconstruct_native_block_branches.py','native_line_path_evidence.py','crossview_equipment_branch_inventory.py','reconcile_pending_main_continuity.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def csv_bytes(fields,rows):
    import io
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
    return ('\ufeff'+stream.getvalue()).encode('utf8')


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inherited-wave-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inherited wave implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('inherited wave input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result,rows,fields,proof=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=receipt['output_graph_sha256'] or proof!=receipt['proof']:
        raise ValueError('inherited wave native reconstruction differs')
    if csv_bytes(fields,rows)!=(directory/'assigned_edge_device_instances.csv').read_bytes():raise ValueError('inherited wave component output differs')
    return receipt


def main():
    parser=argparse.ArgumentParser()
    keys=('source','graph','devices','control-source','control-graph','control-confirmation','control-issue','control-image','policy')
    for key in keys+('output',):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={key.replace('-','_'):getattr(a,key.replace('-','_')) for key in keys}
    if a.output.exists():raise FileExistsError(a.output)
    result,rows,fields,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'graph_with_edges.json';target.write_bytes(encode(result))
    (a.output/'assigned_edge_device_instances.csv').write_bytes(csv_bytes(fields,rows))
    (a.output/'inherited-wave-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_graph_sha256=sha(target),proof=proof,human_accepted=False,hil_ready=False)))
    print(dict(pairs=proof['pairs'],nodes=proof['nodes_after'],edges=proof['edges_after'],components=proof['components'],physical_lengths_assigned=0),flush=True)


if __name__=='__main__':main()
