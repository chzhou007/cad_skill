"""Correct selected graph floor labels on source-witnessed main continuations.

Requires matching native plan/axis captions, an explicit plan floor title and
same-system component agreement after scoped riser barriers. No pipe, port,
physical length or cross-view path correspondence is created.
"""
import argparse,collections,copy,hashlib,json,math
from pathlib import Path
from native_path_coverage_audit import audit as audit_coverage
from source_readability import read_source


def repair(doc, plan, graph, policy, hashes, tol=.05):
    for k in ('source_sha256','plan_source_sha256','graph_sha256'):
        if policy.get(k)!=hashes.get(k):raise ValueError('source/graph mismatch: '+k)
    title=policy['plan_title'];text=plan.entitydb.get(title.get('handle'))
    if (not text or text not in plan.modelspace() or text.dxftype()!='TEXT'
            or text.plain_text()!=title.get('text') or text.dxf.layer!=title.get('layer')):
        raise ValueError('native plan floor title changed')
    target=policy['target_floor']
    if isinstance(target,bool) or not isinstance(target,int) or title.get('floor')!=target:
        raise ValueError('invalid floor calibration')
    prefixes={1:'一层',2:'二层',3:'三层',4:'四层',5:'五层',6:'六层',7:'七层',8:'八层',9:'九层',10:'十层'}
    if not (text.plain_text().startswith(str(target)+'层') or
            target in prefixes and text.plain_text().startswith(prefixes[target])):
        raise ValueError('plan title does not state the selected floor')
    anchors=policy.get('caption_anchors',[])
    if len(anchors)<2 or len({a['equipment_id'] for a in anchors})!=len(anchors):
        raise ValueError('multiple independent native captions required')
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph identity')
    captions=[]
    for anchor in anchors:
        ident=anchor['equipment_id'];n=nodes.get(ident)
        if not n or n.get('node_type') not in ('equipment','physical_equipment') or n.get('floor')!=target:
            raise ValueError('caption graph equipment mismatch')
        for key,drawing in [('axis_text_handle',doc),('plan_text_handle',plan)]:
            e=drawing.entitydb.get(anchor[key])
            if not e or e not in drawing.modelspace() or e.dxftype()!='TEXT' or e.plain_text()!=ident:
                raise ValueError('native equipment caption changed')
            if sum(x.plain_text()==ident for x in drawing.modelspace().query('TEXT MTEXT'))!=1:
                raise ValueError('native equipment caption is not unique')
        captions.append(copy.deepcopy(anchor))
    selected=policy.get('nodes',[])
    if not selected or len({n['node_id'] for n in selected})!=len(selected):raise ValueError('invalid node selection')
    cp=policy['coverage_policy']
    coverage=audit_coverage(doc,graph,cp,hashes['source_sha256'],hashes['graph_sha256'],tol)
    covered={r['edge_id']:r for r in coverage['edges']}
    barriers=policy.get('riser_barrier_edges',[])
    if not isinstance(barriers,dict) or not barriers or not set(barriers)<=set(edges):raise ValueError('invalid riser barriers')
    if set(covered)!=({eid for n in selected for eid in n['main_edge_ids']}|set(barriers)):
        raise ValueError('source main coverage scope mismatch')
    # Reproduce the explicitly scoped long native vertical drawing spans.
    # They bound this search without certifying physical risers or length.
    min_span=policy.get('minimum_barrier_drawing_span')
    if isinstance(min_span,bool) or not isinstance(min_span,(int,float)) or min_span<=tol:raise ValueError('invalid native barrier span')
    for eid,handle in barriers.items():
        spans=covered[eid]['segments']
        if (not spans or any(s['status']!='single_source_line_covers' for s in spans)
                or not any(abs(s['start'][0]-s['end'][0])<=tol and abs(s['start'][1]-s['end'][1])>=min_span
                    and s['witnesses'][0]['source_handle']==handle for s in spans)):
            raise ValueError('barrier is not a witnessed long vertical source span')
    changes=[];g=copy.deepcopy(graph);gn={n['node_id']:n for n in g['nodes']}
    for item in selected:
        ident=item['node_id'];n=nodes.get(ident);main_ids=item['main_edge_ids']
        if (not n or n.get('node_type') not in ('tee','physical_junction')
                or n.get('floor')!=item['expected_floor'] or item['expected_floor']==target
                or len(main_ids)!=2 or len(set(main_ids))!=2):raise ValueError('selected floor node changed')
        system=edges[main_ids[0]].get('system')
        if system not in ('supply','return'):raise ValueError('unknown main system')
        incident=[e for e in edges.values() if ident in (e['start_node_id'],e['end_node_id'])]
        if len(incident)!=3 or any(e['system']!=system for e in incident):raise ValueError('mixed or non-tee incidence')
        source_paths=[];rays=[];p=[n['x'],n['y']]
        for eid in main_ids:
            e=edges[eid];r=covered[eid]
            if e['system']!=system or ident not in (e['start_node_id'],e['end_node_id']):raise ValueError('main incidence mismatch')
            other=e['end_node_id'] if e['start_node_id']==ident else e['start_node_id']
            if nodes[other].get('floor')!=target:raise ValueError('flanking source main floor conflict')
            if (not r['segments'] or any(s['status']!='single_source_line_covers' or len(s['witnesses'])!=1 for s in r['segments'])
                    or [s['witnesses'][0]['source_handle'] for s in r['segments']]!=item['source_line_sequences'][eid]):
                raise ValueError('main is not fully native source-witnessed')
            if any(abs(s['end'][0]-s['start'][0])<=tol and abs(s['end'][1]-s['start'][1])>tol for s in r['segments']):
                raise ValueError('vertical main segment requires independent elevation interpretation')
            touching=[s for s in r['segments'] if min(math.dist(s['start'],p),math.dist(s['end'],p))<=tol]
            if len(touching)!=1:raise ValueError('ambiguous source ray at selected node')
            s=touching[0];other=s['end'] if math.dist(s['start'],p)<=tol else s['start']
            length=math.dist(other,p)
            rays.append((s['witnesses'][0]['source_handle'],[(other[i]-p[i])/length for i in (0,1)]))
            source_paths.append(copy.deepcopy(r))
        if rays[0][0]!=rays[1][0] or sum(a*b for a,b in zip(rays[0][1],rays[1][1]))>-math.cos(math.radians(.1)):
            raise ValueError('selected main rays are not opposite spans of one source line')
        adj=collections.defaultdict(list)
        for e in edges.values():
            if e['system']==system and e['edge_id'] not in barriers:
                a,b=e['start_node_id'],e['end_node_id'];adj[a].append(b);adj[b].append(a)
        seen={ident};queue=collections.deque([ident])
        while queue:
            a=queue.popleft()
            # Do not pass through equipment to another service or other ports.
            if nodes[a]['node_type'] in ('equipment','physical_equipment','virtual_equipment'):continue
            for b in adj[a]:
                if b not in seen:seen.add(b);queue.append(b)
        if any(a['equipment_id'] not in seen for a in anchors):raise ValueError('floor captions not in the scoped same-system component')
        equipment=[nodes[x] for x in seen if nodes[x]['node_type'] in ('equipment','physical_equipment')]
        if any(n.get('floor')!=target for n in equipment):raise ValueError('component has competing equipment floor labels')
        # Captions corroborate floor metadata; they do not map devices/ports
        # or paths across views. The unselected third branch stays unverified.
        gn[ident]['floor']=target
        record={'node_id':ident,'from_floor':item['expected_floor'],'to_floor':target,
            'main_edge_ids':main_ids,'source_paths':source_paths,'caption_anchors':captions,
            'component_equipment_count':len(equipment),'third_branch_connectivity':'unchanged_not_newly_verified',
            'status':'source_main_caption_floor_label_reconciled','physical_floor_verified':False}
        changes.append(record)
    for e in g['edges']:
        for side in ('start','end'):
            nid=e[side+'_node_id']
            if any(c['node_id']==nid for c in changes):e['floor_'+side]=target
    g['sourceFloorLabelRepair']={'source_sha256':hashes['source_sha256'],
        'plan_source_sha256':hashes['plan_source_sha256'],'input_graph_sha256':hashes['graph_sha256'],
        'changes':changes,'physical_floor_verified':False,'crossview_path_mapping_ready':False}
    g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed_after_floor_label_reconciliation')
    return g,{'status':'scoped_source_floor_label_repair_not_physical_floor_acceptance',
        **hashes,'changes':changes,'coverage':coverage,'graph_connectivity_changed':False,
        'crossview_path_mapping_ready':False,'hil_ready':False}


def verify_output(graph_path):
    graph_path=Path(graph_path);report=json.loads((graph_path.parent/'floor-label-repair-audit.json').read_text(encoding='utf8'))
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    files={k:Path(report['input_files'][k]) for k in ('source','plan_source','graph','policy')}
    if report['script_sha256']!=sha(__file__) or report['policy_sha256']!=sha(files['policy']) or report['output_graph_sha256']!=sha(graph_path):raise ValueError('floor repair artifacts changed')
    doc,pre=read_source(files['source']);plan,planpre=read_source(files['plan_source'])
    hashes={'source_sha256':pre['source_sha256'],'plan_source_sha256':planpre['source_sha256'],'graph_sha256':sha(files['graph'])}
    if any(report.get(k)!=v for k,v in hashes.items()):raise ValueError('floor repair inputs changed')
    g,audit=repair(doc,plan,json.loads(files['graph'].read_text(encoding='utf8')),json.loads(files['policy'].read_text(encoding='utf8')),hashes)
    if (g!=json.loads(graph_path.read_text(encoding='utf8')) or audit['changes']!=report['changes']
            or audit['coverage']!=report['coverage']):raise ValueError('floor repair not reproducible')
    return {'status':'source_floor_label_repair_reproduced','nodes':len(audit['changes']),'graph_sha256':sha(graph_path),'hil_ready':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','plan-source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    doc,pre=read_source(a.source);plan,planpre=read_source(a.plan_source)
    g,report=repair(doc,plan,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),
        {'source_sha256':pre['source_sha256'],'plan_source_sha256':planpre['source_sha256'],'graph_sha256':sha(a.graph)})
    a.output.mkdir(exist_ok=False,parents=True);gp=a.output/'graph_with_edges.json';gp.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report.update(input_files={k:str(getattr(a,k).resolve()) for k in ('source','plan_source','graph','policy')},
        source_preflight=pre,plan_source_preflight=planpre,output_graph_sha256=sha(gp),policy_sha256=sha(a.policy),script_sha256=sha(__file__))
    (a.output/'floor-label-repair-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'corrected_nodes':len(report['changes']),'output_graph_sha256':sha(gp),'crossview_path_mapping_ready':False}))


if __name__=='__main__':main()
