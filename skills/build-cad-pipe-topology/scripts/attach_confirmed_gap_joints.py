"""Attach explicitly reviewed inline joints without measuring drawing gaps."""
import argparse,copy,csv,hashlib,json,math,subprocess,sys,tempfile
from pathlib import Path
from native_path_coverage_audit import audit as audit_coverage
from screen_missing_gap_joints import screen
from repair_exploded_joint_ownership import _inventory
from source_readability import read_source

DECISION='金属软接，两侧连通'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
digest=lambda value:hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode('utf8')).hexdigest()

def implementation_hashes():
    return [sha(Path(__file__).with_name(name)) for name in ('attach_confirmed_gap_joints.py',
        'screen_missing_gap_joints.py','native_path_coverage_audit.py','repair_native_flexible_joints.py',
        'repair_exploded_joint_ownership.py','native_line_path_evidence.py')]

def repair(doc,graph,rows,reviewed,manifest,reply,policy,source_hash,graph_hash):
    if (policy['source_sha256']!=source_hash or policy['graph_sha256']!=graph_hash
        or graph['metadata'].get('source_sha256') not in (None,source_hash) or manifest['source_sha256']!=source_hash):
        raise ValueError('changed source or current graph')
    _inventory(graph,rows)
    questions={q['id']:(q,s['image']['sha256']) for s in reply['sections'] for q in s['questions']}
    if len(questions)!=sum(len(s['questions']) for s in reply['sections']):raise ValueError('duplicate reply question')
    candidates={r['handle']:r for r in manifest['records']}
    current={e['edge_id']:e for e in graph['edges']};past={e['edge_id']:e for e in reviewed['edges']}
    if len(current)!=len(graph['edges']) or len(past)!=len(reviewed['edges']):raise ValueError('duplicate graph edges')
    selections=policy['selections'];prepared=[];answers={}
    if not selections or len({s['insert_handle'] for s in selections})!=len(selections):raise ValueError('empty or duplicate joint selection')
    for sel in selections:
        handle=sel['insert_handle'];q,image=questions.get(sel['question_id'],({},None))
        if handle not in q.get('text','') or q.get('answer',{}).get('decision')!=DECISION or image!=manifest['image_sha256']:
            raise ValueError('missing explicit reply to the reviewed joint Pair')
        row=candidates[handle];eid=row['edge'];edge=current[eid];old=past[eid]
        # Only coverage receipts changed after the reviewed snapshot. Never
        # carry a reply onto a changed route, component inventory or endpoint.
        if {k:v for k,v in edge.items() if k!='source_path_coverage'}!={k:v for k,v in old.items() if k!='source_path_coverage'}:
            raise ValueError('reviewed joint edge changed')
        a=edge.get('source_path_coverage',{});b=old.get('source_path_coverage',{})
        if any(a.get(k)!=b.get(k) for k in ('source_sha256','unverified_segment_indices','unverified_drawing_length')):
            raise ValueError('reviewed gap coverage changed')
        paths=edge['attribute_paths']
        if len(paths)!=1:raise ValueError('joint edge has multiple source paths')
        hits=[i for i,(a,b) in enumerate(zip(paths[0],paths[0][1:])) if all(math.dist(x,y)<=.05 for x,y in zip((a,b),row['gap_endpoints']))]
        if len(hits)!=1 or hits[0] not in edge['source_path_coverage']['unverified_segment_indices']:
            raise ValueError('reviewed gap moved')
        prepared.append(dict(edge_id=eid,segment_index=hits[0],insert_handle=handle));answers[handle]=copy.deepcopy(q)
    cp=dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[s['edge_id'] for s in prepared])
    coverage=audit_coverage(doc,graph,cp,source_hash,graph_hash)
    hashes=dict(source_sha256=source_hash,graph_sha256=graph_hash,coverage_sha256=digest(coverage),inventory_sha256=digest(rows))
    calibration=dict(policy['calibration'],**hashes,selections=prepared)
    native=screen(doc,coverage,graph,rows,calibration,hashes)
    out=copy.deepcopy(graph);outrows=copy.deepcopy(rows);edges={e['edge_id']:e for e in out['edges']};records=[]
    for candidate in native['records']:
        handle=candidate['insert_handle'];witnesses=[w['source_handle'] for n in candidate['adjacent_source_segments'] for w in n['source_witnesses']]
        if set(witnesses)!=set(candidates[handle]['source_line_handles']):raise ValueError('native adjacent source lines changed')
        ins=doc.entitydb[handle];pos=ins.ocs().to_wcs(ins.dxf.insert);name='金属软接-PAIR-'+handle
        if any(r['device_name']==name or r.get('source_top_handle')==handle for r in outrows):raise ValueError('joint already assigned')
        edge=edges[candidate['edge_id']]
        slot=next((x for x in edge.get('equipment_inventory',[]) if x['equipment_type']=='金属软接'),None)
        if slot is None:
            slot=dict(equipment_type='金属软接',count=0,device_names=[]);edge.setdefault('equipment_inventory',[]).append(slot)
        slot['device_names'].append(name);slot['count']+=1
        proof=dict(candidate,question_id=answers[handle]['id'],answer=answers[handle]['answer'],
            reviewed_pair_sha256=manifest['image_sha256'],input_graph_sha256=graph_hash,
            status='user_confirmed_inline_joint_logical_continuity',physical_length='unknown',parameter_status='unknown_not_zero')
        edge.setdefault('source_confirmed_gap_joints',[]).append(proof)
        outrows.append(dict(device_name=name,equipment_type='金属软接',type_code='MFJ',x=str(pos.x),y=str(pos.y),
            assignment_x=str(pos.x),assignment_y=str(pos.y),source_kind='block_insert',source_block_name=ins.dxf.name,
            source_top_handle=handle,owner_equipment='',system_hint=edge['system'],edge_id=edge['edge_id'],edge_distance='0',
            assignment_status='assigned',assignment_basis='explicit_pair_confirmed_gap_joint'))
        records.append(proof)
    _inventory(out,outrows)
    out['sourceConfirmedGapJoints']=dict(source_sha256=source_hash,input_graph_sha256=graph_hash,records=records,
        logical_connectivity_confirmed=True,source_paths_and_lengths_unchanged=True,physical_length='unknown')
    out['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_component_change')
    out['derivedEvidenceInvalidation']=dict(reason='confirmed gap-joint component inventory changed',
        recompute=['component_conservation','source_comparison','cross_view_mapping','human_acceptance'],source_paths_unchanged=True)
    return out,outrows,dict(records=records,coverage=coverage,native_candidate_screen=native,hil_ready=False)

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'confirmed-gap-joint-audit.json')
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale gap-joint implementation')
    if sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256']:raise ValueError('stale gap-joint output graph')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale gap-joint input')
    with tempfile.TemporaryDirectory() as temp:
        out=Path(temp)/'replay';command=[sys.executable,'-X','utf8',str(Path(__file__))]
        for key,item in audit['inputs'].items():command+=['--'+key.replace('_','-'),item['path']]
        subprocess.run(command+['--output',str(out)],check=True,stdout=subprocess.DEVNULL)
        for name in ('graph_with_edges.json','edge_device_instances.csv'):
            if sha(directory/name)!=sha(out/name):raise ValueError('gap-joint replay differs: '+name)
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','reviewed-graph','manifest','image','reply','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--check-parent',action='store_true',help='Independently replay the parent source-comparison gate and consume only these confirmed joint candidates')
    a=p.parse_args();policy=load(a.policy);names=('source','graph','devices','reviewed_graph','manifest','image','reply')
    for key in names:
        if policy[key+'_sha256']!=sha(getattr(a,key)):raise ValueError('changed '+key)
    manifest=load(a.manifest)
    if manifest['graph_sha256']!=sha(a.reviewed_graph) or manifest['image_sha256']!=sha(a.image):raise ValueError('reviewed Pair identity mismatch')
    if a.output.exists():raise ValueError('output exists')
    doc,proof=read_source(a.source)
    with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    out,rows,audit=repair(doc,load(a.graph),rows,load(a.reviewed_graph),manifest,load(a.reply),policy,sha(a.source),sha(a.graph))
    a.output.mkdir(parents=True)
    gp=a.output/'graph_with_edges.json';gp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    fields=list(dict.fromkeys(fields+[k for row in rows for k in row]))
    with (a.output/'edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    audit.update(inputs={key:dict(path=str(getattr(a,key).resolve()),sha256=sha(getattr(a,key))) for key in names+('policy',)},
        output_graph_sha256=sha(gp),source_preflight=proof['status'],implementation_sha256=implementation_hashes())
    (a.output/'confirmed-gap-joint-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if a.check_parent:
        owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
        sys.path.insert(0,str(owner))
        from source_comparison_gate import check
        parent_report=load(Path(policy['parent_task_root'])/'source-comparison-report.json')
        result=check(parent_report,sha(gp),a.output,gp)
        (a.output/'source-comparison-gate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        if result['errors']:raise ValueError('confirmed gap-joint comparison failed: '+str(result['errors']))
        stage=dict(status='source_confirmed_gap_joint_components_with_parent_comparison',graph_sha256=sha(gp),
            audit_sha256=sha(a.output/'confirmed-gap-joint-audit.json'),inventory_sha256=sha(a.output/'edge_device_instances.csv'),
            parent_graph_sha256=sha(a.graph),source_comparison_sha256=sha(a.output/'source-comparison-gate.json'),hil_ready=False)
        (a.output/'confirmed-gap-joint-stage.json').write_text(json.dumps(stage,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(joints=len(audit['records']),components=len(rows),nodes=len(out['nodes']),edges=len(out['edges']),hil_ready=False)))

if __name__=='__main__':main()
