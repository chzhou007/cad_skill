"""Batch a calibrated paired wave-to-main convention, preserving source scopes.

Wave presence alone never accepts a remote destination. Both service lanes,
native shape, outward direction, gap/chord ratios and the calibrated main
carriers must agree. Split every affected main once and conserve components.
"""
import argparse
import collections
import copy
import csv
import importlib
import math
from pathlib import Path

from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,service_route
from native_line_path_evidence import LAYERS
from inherited_wave_pair_continuity import contact,wave_feature
from wave_omission_candidates import block_fingerprint
from split_native_main_paths import split_main
from repair_confirmed_circle_junctions import pos
from edge_endpoint_semantics import reconcile

MODE='source_calibrated_paired_wave_main_cohort_v1'


def bind_control(paths,policy):
    for key,path in paths.items():
        if sha(path)!=policy['inputs'][key]['sha256']:raise ValueError('wave cohort input changed '+key)
    raw,definition,receipt=(load(paths[k]) for k in ('reply','definitions','receipt'))
    def find(d):
        matches=[(q,s['image']) for group in ('sections','followup_sections') for s in d[group] for q in s['questions'] if q['id']==policy['question_id']]
        if len(matches)!=1:raise ValueError('wave calibration question missing or repeated')
        return matches[0]
    q,image=find(raw);original,original_image=find(definition)
    if image!=original_image or any(q.get(k)!=original.get(k) for k in ('text','options','source_evidence')):
        raise ValueError('wave calibration question differs from pinned definition')
    matched=[r for r in receipt['records'] if r['question_id']==q['id']]
    if (receipt['input']['sha256']!=sha(paths['reply']) or len(matched)!=1 or matched[0]['explicit_answer']!=q.get('answer')
        or q['answer']['decision']!=policy['confirmed_decision'] or q['answer']['decision'] not in q['options']
        or q['answer'].get('source_pair_sha256')!=sha(paths['pair']) or image['sha256']!=sha(paths['pair'])
        or matched[0]['pair_sha256']!=sha(paths['pair']) or matched[0]['source_evidence']!=q['source_evidence']
        or q['source_evidence']['source_graph_sha256']!=sha(paths['reviewed_graph'])):
        raise ValueError('explicit original wave-main Pair answer required')
    reviewed=load(paths['reviewed_graph']);current=load(paths['graph'])
    if any(g.get('metadata',{}).get('source_sha256')!=sha(paths['source']) for g in (reviewed,current)):
        raise ValueError('reviewed/current wave source differs')
    did=policy['control_equipment']
    for system in ('supply','return'):
        before=service_route(reviewed,did,system);after=service_route(current,did,system)
        if before!=after:raise ValueError('reviewed wave control route changed')
        old_edges=index_graph(reviewed)[1];new_edges=index_graph(current)[1]
        for eid in before['edges']:
            if old_edges[eid]['attribute_paths']!=new_edges[eid]['attribute_paths']:raise ValueError('reviewed source branch changed')
    return dict(question_id=q['id'],explicit_answer=q['answer'],pair_sha256=sha(paths['pair']),
        reviewed_graph_sha256=sha(paths['reviewed_graph']),control_equipment=did)


def forward_hits(doc,point,outward,system):
    hits=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer!=LAYERS[system]:continue
        a,b=list(line.dxf.start),list(line.dxf.end);w=[b[i]-a[i] for i in (0,1)]
        den=outward[0]*w[1]-outward[1]*w[0]
        if abs(den)<1e-9:continue
        delta=[a[i]-point[i] for i in (0,1)]
        t=(delta[0]*w[1]-delta[1]*w[0])/den;fraction=(delta[0]*outward[1]-delta[1]*outward[0])/den
        if t<=.05 or not 0<fraction<1:continue
        direction=[v/math.hypot(*w) for v in w]
        if abs(sum(x*y for x,y in zip(direction,outward)))>math.sin(math.radians(1)):continue
        hits.append(dict(source_handle=line.dxf.handle,point=[point[i]+t*outward[i] for i in (0,1)],
            distance=t,Z=a[2]+fraction*(b[2]-a[2]),main_direction=direction))
    return sorted(hits,key=lambda r:(r['distance'],r['source_handle']))


def collect(doc,graph,policy):
    nodes,edges,adj=index_graph(graph)
    fingerprint=block_fingerprint(doc.blocks[policy['wave_block']])
    if fingerprint!=policy['wave_fingerprint']:raise ValueError('calibrated native wave block changed')
    waves=[]
    for entity in doc.modelspace().query('INSERT'):
        if entity.dxf.name!=policy['wave_block']:continue
        parts=list(entity.virtual_entities())
        if len(parts)!=1 or parts[0].dxftype()!='LWPOLYLINE' or len(parts[0])!=3:continue
        waves.append((entity,list(parts[0].vertices_in_wcs())[1]))
    rows=[];pending=[]
    for device in graph['nodes']:
        if device.get('node_type')!='equipment' or device.get('floor')!=policy['floor']:continue
        for system in ('supply','return'):
            trace=service_route(graph,device['node_id'],system)
            if trace['status']=='unique_graph_service_to_T':continue
            if trace['status']!='unresolved_interface_or_other_equipment' or len(trace['edges'])!=1:
                pending.append(dict(equipment_id=device['node_id'],system=system,reason='unproved_local_equipment_service'));continue
            nid=trace['at_node'];node=nodes[nid];edge=edges[trace['edges'][0]];point=[node['x'],node['y']]
            if node.get('node_type')!='virtual_equipment' or len(adj[nid])!=1 or node.get('system')!=system:continue
            # INSERT bases need not coincide with the native curve centre.
            # This bounded candidate search never changes pipe snapping.
            matching=[w for w,center in waves if math.dist(list(center)[:2],point)<=1.0]
            if len(matching)!=1:
                pending.append(dict(equipment_id=device['node_id'],system=system,reason='native_wave_not_unique'));continue
            endpoint=contact(doc,edge,point,system)
            ends=[p[:2] for p in endpoint['line_XYZ']];tail=max(ends,key=lambda p:math.dist(point,p))
            length=math.dist(point,tail);outward=[(point[i]-tail[i])/length for i in (0,1)]
            feature=wave_feature(doc,matching[0].dxf.handle,point,endpoint['XYZ'],outward,policy['wave_block'],fingerprint)
            chord=math.dist(feature['native_vertices_XYZ'][0],feature['native_vertices_XYZ'][-1])
            hits=forward_hits(doc,point,outward,system)
            if not hits or (len(hits)>1 and abs(hits[0]['distance']-hits[1]['distance'])<=.05):
                pending.append(dict(equipment_id=device['node_id'],system=system,reason='main_ray_missing_or_competing'));continue
            hit=hits[0]
            owners=[e for e in graph['edges'] if e['system']==system and hit['source_handle'] in e.get('source_handles',[])
                and any(on_path(hit['point'],p) for p in e.get('attribute_paths',[]))]
            if len(owners)!=1:
                pending.append(dict(equipment_id=device['node_id'],system=system,reason='main_owner_not_unique'));continue
            rows.append(dict(equipment_id=device['node_id'],system=system,terminal=nid,branch_edge=edge['edge_id'],
                branch_contact=endpoint,wave=feature,wave_chord=chord,outward=outward,
                target=hit,main_edge=owners[0]['edge_id'],gap_chord_ratio=hit['distance']/chord,
                native_source_Z_delta=endpoint['XYZ'][2]-hit['Z']))
    return rows,pending


def on_path(point,path):
    try:pos(path,point,tol=.05);return True
    except ValueError:return False


def same_wave(candidate,control,contact_tolerance=.05):
    if abs(candidate['gap_chord_ratio']-control['gap_chord_ratio'])>.01:return False
    a=candidate['wave']['relative_pipe_frame'];b=control['wave']['relative_pipe_frame']
    scale=candidate['wave_chord']/control['wave_chord']
    if not .999<=scale<=1.001:return False
    # Keep source XYZ separately. Plane shape is compared after removing its
    # constant offset from the pipe endpoint; no physical elevation is inferred.
    return any(all(abs(p[0]-q[0])<=contact_tolerance and abs(p[1]-sign*q[1])<=contact_tolerance
        and abs((p[2]-a[1][2])-(q[2]-b[1][2]))<=1e-4
        and abs(p[3]-sign*q[3])<=1e-6 for p,q in zip(a,b)) for sign in (1,-1))


def qualify(rows,policy):
    controls={r['system']:r for r in rows if r['equipment_id']==policy['control_equipment']}
    if set(controls)!={'supply','return'} or any(controls[s]['target']['source_handle']!=policy['control_main_handles'][s] for s in controls):
        raise ValueError('native control does not reproduce the explicit paired-main answer')
    contact_tolerance=max(.05,2*max(r['wave']['centre_to_pipe_end_xy'] for r in controls.values())+.05)
    if contact_tolerance>1.0:raise ValueError('control curve offset exceeds supported local source envelope')
    groups=collections.defaultdict(dict)
    for row in rows:
        if row['system'] in groups[row['equipment_id']]:raise ValueError('duplicate equipment service candidate')
        groups[row['equipment_id']][row['system']]=row
    accepted=[];pending=[]
    for did,pair in sorted(groups.items()):
        if set(pair)!={'supply','return'} or any(not same_wave(pair[s],controls[s],contact_tolerance)
            or pair[s]['wave']['centre_to_pipe_end_xy']>contact_tolerance
            or not min(0,controls[s]['native_source_Z_delta'])-.05<=pair[s]['native_source_Z_delta']<=max(0,controls[s]['native_source_Z_delta'])+.05
            or pair[s]['main_edge']!=controls[s]['main_edge'] for s in pair):
            pending.append(dict(equipment_id=did,reason='paired_native_wave_gap_or_calibrated_carrier_differs'));continue
        supply,ret=pair['supply'],pair['return'];cs,cr=controls['supply'],controls['return']
        if sum(x*y for x,y in zip(supply['outward'],ret['outward']))<.9999:
            pending.append(dict(equipment_id=did,reason='paired_service_rays_disagree'));continue
        u=supply['outward'];v=[-u[1],u[0]];cu=cs['outward'];cv=[-cu[1],cu[0]]
        offset=[ret['target']['point'][i]-supply['target']['point'][i] for i in (0,1)]
        reference=[cr['target']['point'][i]-cs['target']['point'][i] for i in (0,1)]
        projected=[sum(x*y for x,y in zip(offset,axis))/supply['wave_chord'] for axis in (u,v)]
        expected=[sum(x*y for x,y in zip(reference,axis))/cs['wave_chord'] for axis in (cu,cv)]
        if math.dist(projected,expected)>.01:
            pending.append(dict(equipment_id=did,reason='paired_main_lane_geometry_differs'));continue
        accepted.extend([supply,ret])
    return accepted,pending


def reconstruct(doc,graph,devices,proofs,source_hash,graph_hash,control):
    if not proofs:raise ValueError('empty calibrated wave cohort')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']}
    rows=copy.deepcopy(devices);groups=collections.defaultdict(list);records=[];parents=[];retired=[]
    for proof in proofs:groups[proof['main_edge']].append(proof)
    for eid,group in sorted(groups.items()):
        parent=edges[eid];reading=copy.deepcopy(parent)
        if reading.get('physical_length') not in (None,'unknown'):raise ValueError('known physical main length needs explicit subdivision')
        reading.pop('physical_length',None)
        cuts=[dict(point=p['target']['point'],source_handle=p['wave']['wave_handle']) for p in group]
        children,rows,landings=split_main(doc,reading,rows,cuts,graph_hash,prefix='WAVE')
        by_wave={c['source_handle']:tee for c,tee in landings}
        for child in children:
            inherited={k:child.pop(k) for k in ('source_expert_riser_connections','source_drafting_erratum') if k in child}
            if inherited:child['inherited_parent_source_scope']=dict(parent_edge_id=eid,evidence=inherited,scope='historical_parent_not_reassigned_to_every_child')
            child['physical_length']='unknown';child['path_length_complete']=False
            edges[child['edge_id']]=child
        # Historical circle/riser features stay active on their actual child,
        # rather than disappearing or being duplicated onto all new children.
        for connection in parent.get('source_expert_riser_connections',[]):
            owners=[c for c in children if on_path(connection['center'],c['path'])]
            if len(owners)!=1:raise ValueError('old source riser connection needs unique child ownership')
            owners[0].setdefault('source_expert_riser_connections',[]).append(copy.deepcopy(connection))
        erratum=parent.get('source_drafting_erratum')
        if erratum:
            owners=[c for c in children if all(on_path(p,c['path']) for p in erratum['source_endpoints'])]
            if len(owners)!=1:raise ValueError('old source erratum scope needs unique child ownership')
            owners[0]['source_drafting_erratum']=copy.deepcopy(erratum)
        parents.append(dict(edge_id=eid,child_edges=[e['edge_id'] for e in children],original_edge=copy.deepcopy(parent)))
        for proof in group:
            tee=by_wave[proof['wave']['wave_handle']];branch=edges[proof['branch_edge']];terminal=proof['terminal']
            node=nodes[terminal];p=[node['x'],node['y']];target=proof['target']['point']
            side=next(s for s in ('start','end') if branch[s+'_node_id']==terminal)
            old=copy.deepcopy(branch);branch[side+'_node_id']=tee;branch.pop(side+'_port_id',None)
            if math.dist(branch['path'][0 if side=='start' else -1],p)>.05:raise ValueError('native branch display frontier changed')
            branch['path']=([target]+branch['path']) if side=='start' else (branch['path']+[target])
            branch['path_points']=copy.deepcopy(branch['path'])
            branch.update(path_length_complete=False,physical_length='unknown',path_length_scope='source_drawn_branch_only_wave_main_extension_physical_length_unknown')
            record=dict(proof,tee_id=tee,original_branch=old,original_terminal=copy.deepcopy(node),
                calibrated_control=copy.deepcopy(control),connection_basis='explicit_expert_control_and_matching_paired_native_wave_cohort',
                omitted_span_physical_length_mm=None,other_system_connected=False,human_accepted=False)
            branch['source_wave_main_junction']=dict(tee_id=tee,equipment_id=proof['equipment_id'],main_parent=eid,
                evidence_wave=proof['wave']['wave_handle'],physical_gap_length_mm=None)
            nodes[tee]=dict(node_id=tee,node_type='tee',subtype='physical_tee',floor=node['floor'],system=node['system'],
                x=target[0],y=target[1],label=tee,source_handles=[proof['target']['source_handle'],proof['branch_contact']['source_line_handle']],
                wave_cohort_connection=True,human_accepted=False)
            retired.append(nodes.pop(terminal));records.append(record)
    retired_ids={n['node_id'] for n in retired};out['nodes']=list(nodes.values());out['edges']=list(edges.values())
    out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in retired_ids]
    out,changes=reconcile(out)
    for record in records:
        incident=[e for e in out['edges'] if record['tee_id'] in (e['start_node_id'],e['end_node_id'])]
        if len(incident)!=3 or {e['system'] for e in incident}!={record['system']}:raise ValueError('rebuilt wave T must have three same-service edges')
    old_instances=collections.Counter((r.get('device_name'),r.get('source_top_handle')) for r in devices)
    if old_instances!=collections.Counter((r.get('device_name'),r.get('source_top_handle')) for r in rows):raise ValueError('native component instances changed')
    if {n['node_id'] for n in graph['nodes'] if n.get('node_type')=='equipment'}!={n['node_id'] for n in out['nodes'] if n.get('node_type')=='equipment'}:
        raise ValueError('physical equipment lost')
    out['sourceWaveMainCohort']=dict(mode=MODE,source_sha256=source_hash,input_graph_sha256=graph_hash,records=records,
        main_splits=parents,retired_terminal_snapshots=retired,endpoint_type_changes=changes,
        calibrated_control=control,dependent_inventory_mapping_attributes_and_HIL_invalidated=True,
        physical_lengths_assigned=0,supply_return_independent=True,human_accepted=False)
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=graph.get('derivedEvidenceInvalidation'),
        reason='calibrated paired wave-main cohort rebuild; all incident mains split together',
        recompute=['branch_inventory','crossview_mapping','DN_inheritance','length_scopes','component_audit','source_comparison','human_acceptance'],historical_annotations_preserved=True)
    return out,rows


def compute(paths,policy):
    control=bind_control(paths,policy)
    from attach_reviewed_interface_owners import verify_output as verify_parent
    parent=verify_parent(Path(paths['graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['graph']):raise ValueError('current local owner graph differs')
    doc,readable=read_source(paths['source']);graph=load(paths['graph'])
    if graph.get('sourceWaveMainCohort'):raise ValueError('wave cohort already applied')
    candidates,pending=collect(doc,graph,policy);proofs,unresolved=qualify(candidates,policy)
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    if sha(paths['devices'])!=sha(Path(paths['graph']).with_name('assigned_edge_device_instances.csv')):
        raise ValueError('current canonical component inventory differs')
    out,assigned=reconstruct(doc,graph,rows,proofs,sha(paths['source']),sha(paths['graph']),control)
    return out,fields,assigned,dict(source_preflight=readable,control=control,candidates=candidates,pending=pending+unresolved,
        connections=len(proofs),equipment=len({p['equipment_id'] for p in proofs}),physical_lengths_assigned=0,human_accepted=False)


def implementation_hashes():
    names=('split_native_main_paths','repair_confirmed_circle_junctions','inherited_wave_pair_continuity','wave_omission_candidates',
        'crossview_equipment_branch_inventory','edge_endpoint_semantics','attach_reviewed_interface_owners')
    return dict({n:sha(importlib.import_module(n).__file__) for n in names},entry=sha(__file__))


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'wave-main-cohort-audit.json')
    if audit['mode']!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('wave cohort implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('wave cohort input changed')
    paths={k:v['path'] for k,v in audit['inputs'].items() if k!='policy'}
    graph,fields,rows,proof=compute(paths,load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or proof!=audit['proof']:
        raise ValueError('wave cohort native independent replay differs')
    with (directory/'assigned_edge_device_instances.csv').open(encoding='utf-8-sig',newline='') as stream:
        if list(csv.DictReader(stream))!=rows:raise ValueError('wave cohort canonical component assignment differs')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','reviewed_graph','devices','reply','receipt','definitions','pair','policy','output','verify-output'):
        parser.add_argument('--'+key.replace('_','-'),type=Path)
    args=parser.parse_args()
    if args.verify_output:verify_output(args.verify_output);print('wave main cohort independently replayed',flush=True);return
    keys=('source','graph','reviewed_graph','devices','reply','receipt','definitions','pair')
    if not args.policy or not args.output or not all(getattr(args,k) for k in keys):parser.error('fixed native/control/current inputs required')
    if args.output.exists():raise FileExistsError(args.output)
    paths={k:getattr(args,k) for k in keys};graph,fields,rows,proof=compute(paths,load(args.policy))
    args.output.mkdir(parents=True);(args.output/'graph_with_edges.json').write_bytes(encode(graph))
    with (args.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    (args.output/'wave-main-cohort-audit.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(p.resolve()),sha256=sha(p)) for k,p in dict(paths,policy=args.policy).items()},
        implementation_sha256=implementation_hashes(),output_graph_sha256=sha(args.output/'graph_with_edges.json'),proof=proof,human_accepted=False)))
    print(dict(connections=proof['connections'],equipment=proof['equipment'],pending=len(proof['pending']),nodes=len(graph['nodes']),edges=len(graph['edges'])),flush=True)


if __name__=='__main__':main()
