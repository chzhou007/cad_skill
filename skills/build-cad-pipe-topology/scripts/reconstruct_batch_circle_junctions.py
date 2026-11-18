"""Reconstruct only source circles explicitly confirmed in a batch Pair reply."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from native_line_path_evidence import _on, LAYERS
from repair_confirmed_circle_junctions import apply, pos, slice_path
from source_readability import read_source

DECISION = '接入同系统主管，供回水独立'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'batch-confirmed-circle-audit.json')
    if audit.get('script_sha256')!=sha(__file__) or audit.get('applier_sha256')!=sha(Path(__file__).with_name('repair_confirmed_circle_junctions.py')):
        raise ValueError('stale confirmed-circle implementation')
    for pathkey,hashkey in [('source','source_sha256'),('input_graph','input_graph_sha256'),('input_devices','input_devices_sha256'),('policy','policy_sha256')]:
        if sha(audit[pathkey])!=audit[hashkey]:raise ValueError('stale '+pathkey)
    with tempfile.TemporaryDirectory() as temp:
        output=Path(temp)/'replay'
        subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),
            '--source',audit['source'],'--graph',audit['input_graph'],'--devices',audit['input_devices'],
            '--policy',audit['policy'],'--output',str(output)],check=True,stdout=subprocess.DEVNULL)
        for filename in ('graph_with_batch_confirmed_circles.json','assigned_edge_device_instances.csv','native-confirmed-circle-screen.json'):
            if sha(output/filename)!=sha(directory/filename):raise ValueError('confirmed-circle replay differs: '+filename)
    return audit


def prepare(doc, graph, manifest, reply, policy, source_hash, graph_hash, tol=.05):
    if (policy['source_sha256'] != source_hash or policy['input_graph_sha256'] != graph_hash
        or manifest['source_sha256'] != source_hash or manifest['graph_sha256'] != graph_hash
        or graph['metadata']['source_sha256'] != source_hash):
        raise ValueError('source or graph evidence mismatch')
    selected = policy['selections']
    if not selected or len({s['circle_handle'] for s in selected}) != len(selected):
        raise ValueError('duplicate or empty circle selection')
    questions = [q for section in reply['sections'] for q in section['questions']]
    if len({q['id'] for q in questions}) != len(questions):
        raise ValueError('duplicate reply question')
    questions = {q['id']: q for q in questions}
    images = {q['id']: section['image']['sha256'] for section in reply['sections'] for q in section['questions']}
    candidates = [c for group in manifest['groups'] for c in group['candidates']]
    edges = {e['edge_id']: e for e in graph['edges']}
    nodes = {n['node_id']: n for n in graph['nodes']}
    rows, answers = [], []
    for spec in selected:
        h = spec['circle_handle']
        q = questions.get(spec['question_id'])
        if (not q or h not in q['text']
            or q.get('answer', {}).get('decision') != DECISION):
            raise ValueError('missing explicit same-system circle confirmation')
        matches = [c for c in candidates if c['circle_handle'] == h]
        if len(matches) != 1:
            raise ValueError('review candidate missing or ambiguous')
        shown = [group for group in manifest['groups'] if any(c['circle_handle']==h for c in group['candidates'])]
        if len(shown)!=1 or shown[0]['sha256']!=images[q['id']]:
            raise ValueError('reply does not match the native Pair image')
        c = matches[0]; system = c['system']
        circle, main, branch = [doc.entitydb.get(c[k]) for k in ('circle_handle','main_handle','branch_handle')]
        if (not circle or circle.dxftype() != 'CIRCLE' or not main or not branch
            or any(e not in doc.modelspace() for e in (circle, main, branch))
            or any(e.dxftype() != 'LINE' or e.dxf.layer != LAYERS.get(system) for e in (main, branch))
            or tuple(circle.dxf.get('extrusion',(0,0,1))) != (0.,0.,1.)):
            raise ValueError('native circle or same-system pipes changed')
        center = [circle.dxf.center.x, circle.dxf.center.y]
        if not all(math.isfinite(v) for e in (main,branch) for p in (e.dxf.start,e.dxf.end) for v in p):
            raise ValueError('nonfinite native line')
        ends = [[p.x,p.y] for p in (branch.dxf.start,branch.dxf.end)]
        rim = min(ends, key=lambda p: math.dist(p,center))
        ma, mb = ([p.x,p.y] for p in (main.dxf.start,main.dxf.end))
        if (math.dist(center,c['circle_center']) > tol or abs(math.dist(rim,center)-circle.dxf.radius)>tol
            or not _on(center,ma,mb,tol)):
            raise ValueError('native main/rim geometry mismatch')
        u=[mb[i]-ma[i] for i in (0,1)]
        main_edge, branch_edge, terminal = edges.get(c['main_edge']),edges.get(c['branch_edge']),nodes.get(c['terminal'])
        if (not main_edge or not branch_edge or not terminal or main_edge['system'] != system
            or branch_edge['system'] != system or terminal.get('system') != system
            or terminal.get('subtype') != 'unresolved_source_terminal'
            or math.dist(rim,[terminal['x'],terminal['y']])>tol
            or c['main_handle'] not in main_edge.get('source_handles',[])
            or c['branch_handle'] not in branch_edge.get('source_handles',[])):
            raise ValueError('reviewed graph candidate changed')
        protected=[b['boundary_id'] for b in graph.get('boundary_anchors',[]) if h in b.get('source_marker_handles',[])]
        if protected:
            raise ValueError('confirmed non-node boundary protected')
        offset=pos(main_edge['path'],center)
        total=sum(math.dist(a,b) for a,b in zip(main_edge['path'],main_edge['path'][1:]))
        if not tol < offset < total-tol:
            raise ValueError('circle not inside main graph edge')
        # A main may turn at the circle: its two rays can belong to two native
        # LINEs. Do not require one LINE to pass straight through the center.
        neighbors=[slice_path(main_edge['path'],0,offset)[-2],slice_path(main_edge['path'],offset,total)[1]]
        rays=[]
        for endpoint in neighbors:
            hits=[]
            for line in doc.modelspace().query('LINE'):
                if line.dxf.layer!=LAYERS[system]:continue
                a,b=([p.x,p.y] for p in (line.dxf.start,line.dxf.end))
                if _on(center,a,b,tol) and _on(endpoint,a,b,tol):hits.append(line.dxf.handle)
            if len(hits)!=1 or hits[0] not in main_edge['source_handles']:
                raise ValueError('main ray source missing or ambiguous')
            rays.append(dict(source_handle=hits[0],endpoint=endpoint))
        directions=[]
        for endpoint in [*neighbors,rim]:
            vector=[endpoint[i]-center[i] for i in (0,1)];length=math.hypot(*vector)
            if length<=tol:raise ValueError('zero junction ray')
            direction=[v/length for v in vector]
            if any(sum(a*b for a,b in zip(direction,other))>math.cos(math.radians(.1)) for other in directions):
                raise ValueError('coincident rays cannot form confirmed tee')
            directions.append(direction)
        # Retain all Z values and the conflicting circle colour. The reply
        # confirms this connection, not a physical height or layer rewrite.
        t=sum((center[i]-ma[i])*u[i] for i in (0,1))/sum(x*x for x in u)
        mz=main.dxf.start.z+t*(main.dxf.end.z-main.dxf.start.z)
        bp=min((branch.dxf.start,branch.dxf.end),key=lambda p:math.dist([p.x,p.y],center))
        rows.append(dict(circle_handle=h,circle_layer=circle.dxf.layer,circle_system=None,
                         line_system=system,circle_layer_matches_lines=circle.dxf.layer==LAYERS[system],
                         center=center,radius=circle.dxf.radius,main_handle=c['main_handle'],branch_handle=c['branch_handle'],
                         branch_rim=rim,main_z_at_center=mz,branch_z_at_rim=bp.z,circle_z=circle.dxf.center.z,
                         z_consistent_within_tolerance=max(abs(mz-bp.z),abs(mz-circle.dxf.center.z))<=tol,
                         main_graph_edges=[c['main_edge']],branch_graph_edges=[c['branch_edge']],
                         rim_virtual_nodes=[c['terminal']],protected_boundaries=[],
                         native_main_rays=rays,ray_directions=directions,
                         status='source_shape_graph_connection_not_established'))
        answers.append(dict(question_id=q['id'],question=q['text'],answer=q['answer']))
    return dict(source_sha256=source_hash,graph_sha256=graph_hash,candidates=rows), answers


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','policy','output'):p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args(); policy=load(a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    for key in ('reply','manifest'):
        if sha(policy[key]) != policy[key+'_sha256']:raise ValueError('stale '+key)
    for image in policy['pair_images']:
        if sha(image['path'])!=image['sha256']:raise ValueError('stale Pair image')
    if {x['sha256'] for x in policy['pair_images']}!={g['sha256'] for g in load(policy['manifest'])['groups']}:
        raise ValueError('native Pair images not completely pinned')
    if sha(a.devices)!=policy['devices_sha256']:raise ValueError('component input changed')
    doc,proof=read_source(a.source);graph=load(a.graph)
    screen,answers=prepare(doc,graph,load(policy['manifest']),load(policy['reply']),policy,proof['source_sha256'],sha(a.graph))
    with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;devices=list(r)
    a.output.mkdir(parents=True)
    review=a.output/'review-scope.json'
    review.write_text(json.dumps(dict(source_sha256=proof['source_sha256'],graph_sha256=sha(a.graph),pairs=[dict(connections=screen['candidates'])]),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    screen_file=a.output/'native-confirmed-circle-screen.json';screen_file.write_text(json.dumps(screen,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    selection=dict(policy,screen_basis='current_graph',screen_sha256=sha(screen_file),circle_handles=[c['circle_handle'] for c in screen['candidates']],
                   review_evidence=dict(image=policy['pair_images'][0]['path'],image_sha256=policy['pair_images'][0]['sha256'],manifest=str(review),manifest_sha256=sha(review),shown_circle_handles=[c['circle_handle'] for c in screen['candidates']]),
                   confirmation=dict(confirmed_by='user',question='Batch Pair circle connections',answer=DECISION,records=answers,reply_sha256=policy['reply_sha256']))
    out,devices,audit=apply(doc,graph,devices,screen,selection,proof['source_sha256'],sha(a.graph),sha(screen_file))
    target=a.output/'graph_with_batch_confirmed_circles.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(devices)
    audit.update(source_sha256=proof['source_sha256'],source=str(a.source.resolve()),input_graph=str(a.graph.resolve()),input_devices=str(a.devices.resolve()),policy=str(a.policy.resolve()),input_graph_sha256=sha(a.graph),output_graph_sha256=sha(target),input_devices_sha256=sha(a.devices),policy_sha256=sha(a.policy),reply_sha256=policy['reply_sha256'],script_sha256=sha(__file__),applier_sha256=sha(Path(__file__).with_name('repair_confirmed_circle_junctions.py')),graph_review='unreviewed_after_scoped_confirmed_reconstruction')
    (a.output/'batch-confirmed-circle-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(connections=len(audit['records']),graph_sha256=sha(target))))


if __name__=='__main__':main()
