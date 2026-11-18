"""Compare unresolved duplicate-main contacts with source-bound expert controls.

Every branch source LINE, local system, 3D geometry and expert control must
match; no expert confirmation is transferred to a candidate.
"""
import argparse,hashlib,json,math
from pathlib import Path
from duplicate_native_main_diagnostics import same_line
from repair_confirmed_circle_junctions import pos
from source_circle_rim_tee_screen import LAYERS
from source_readability import read_source
TOL=.05
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(doc,center,handles):
    result=[]
    for h in handles:
        e=doc.entitydb.get(h)
        if e is None or e.dxftype()!='LINE' or e not in doc.modelspace():raise ValueError('missing native branch line')
        pts=sorted(tuple(float(p[i]-center[i]) for i in range(3)) for p in (e.dxf.start,e.dxf.end))
        result.append((e.dxf.layer,pts))
    return sorted(result,key=lambda x:(x[0],x[1]))
def equal_signature(a,b):
    return len(a)==len(b) and all(x[0]==y[0] and all(math.dist(p,q)<=TOL for p,q in zip(x[1],y[1])) for x,y in zip(a,b))
def prepare(doc,graph,screen,review,policy,source_hash,graph_hash,screen_hash,review_hash):
    if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('screen_sha256')!=screen_hash or policy.get('review_sha256')!=review_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash or screen.get('source_sha256')!=source_hash or screen.get('graph_sha256')!=graph_hash or review.get('source_sha256')!=source_hash or review.get('graph_sha256')!=graph_hash):raise ValueError('stale input')
    edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    if len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph identity')
    expert=graph.get('expertConfirmedCircleJunctionRepair',{});confirm=expert.get('confirmation',{})
    if expert.get('source_sha256')!=source_hash or confirm.get('confirmed_by')!='expert':raise ValueError('missing expert controls')
    controls={r['circle_handle']:r for r in expert.get('records',[])}
    ambiguous={c['circle_handle']:c for c in screen.get('ambiguous_native_geometry',[])}
    reviewed={c['circle_handle']:(pair,c) for pair in review.get('pairs',[]) for c in pair.get('connections',[])}
    selections=policy.get('selections',[])
    if not selections or len({s['circle_handle'] for s in selections})!=len(selections):raise ValueError('invalid selections')
    result=[]
    for sel in selections:
        h=sel['circle_handle'];c=ambiguous.get(h);control=controls.get(sel['control_circle']);pair=reviewed.get(h)
        if not c or not control or not pair:raise ValueError('candidate or expert control missing')
        image=Path(pair[0]['image'])
        if not image.is_file() or sha(image)!=pair[0]['image_sha256']:raise ValueError('stale source pair')
        circle=doc.entitydb.get(h);ref=doc.entitydb.get(sel['control_circle']);system=c['system']
        if not circle or circle.dxftype()!='CIRCLE' or not ref or ref.dxftype()!='CIRCLE' or any(e not in doc.modelspace() for e in (circle,ref)) or tuple(circle.dxf.extrusion)!=(0.,0.,1.) or tuple(ref.dxf.extrusion)!=(0.,0.,1.):raise ValueError('unsupported circle')
        if LAYERS.get(circle.dxf.layer)!=system or circle.dxf.layer!=ref.dxf.layer or abs(circle.dxf.radius-ref.dxf.radius)>TOL or abs(circle.dxf.center.z-ref.dxf.center.z)>TOL:raise ValueError('circle system, radius or source Z differs')
        node=nodes.get(control['tee']);refedge=edges.get(control['branch_edge'])
        if not node or not refedge or node.get('system')!=system or node.get('expert_confirmed_circle',{}).get('circle_handle')!=sel['control_circle']:raise ValueError('expert control no longer connected')
        control_evidence=node['expert_confirmed_circle'];issue_info=control_evidence.get('expert_issue_evidence',{});issue_path=Path(issue_info.get('issue',''))
        if not issue_path.is_file() or sha(issue_path)!=issue_info.get('issue_sha256'):raise ValueError('expert control issue evidence stale')
        issue=json.loads(issue_path.read_text(encoding='utf8'))
        if issue.get('sourceHashes',{}).get('main_dxf')!=source_hash or issue.get('issue',{}).get('id')!=issue_info.get('issue_id') or issue.get('issue',{}).get('note')!=confirm.get('answer'):raise ValueError('expert control issue no longer matches')
        incident=[e for e in edges.values() if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=3 or any(e.get('system')!=system for e in incident):raise ValueError('expert control no longer three-way')
        handles=c.get('main_handles',[]);branches=c.get('branch_handles',[])
        if len(handles)<2 or len(branches)!=1:raise ValueError('unsupported native ambiguity')
        if set(handles)!=set(control_evidence.get('coincident_native_main_handles',[])) or control_evidence.get('physical_main_identity')!='unresolved':raise ValueError('candidate does not share the expert control native main family')
        mains=[doc.entitydb.get(x) for x in handles];branchline=doc.entitydb.get(branches[0])
        if any(x is None or x not in doc.modelspace() for x in mains) or any(not same_line(mains[0],x,TOL) for x in mains[1:]) or any(LAYERS.get(x.dxf.layer)!=system for x in mains) or branchline is None or LAYERS.get(branchline.dxf.layer)!=system:raise ValueError('native main or system differs')
        branch=[e for e in edges.values() if branches[0] in e.get('source_handles',[]) and e.get('system')==system]
        if len(branch)!=1:raise ValueError('branch edge not unique')
        branch=branch[0]
        if not equal_signature(signature(doc,circle.dxf.center,branch['source_handles']),signature(doc,ref.dxf.center,refedge['source_handles'])):raise ValueError('complete branch source signature differs from expert control')
        xy=[circle.dxf.center.x,circle.dxf.center.y];target=[]
        for e in edges.values():
            if e.get('system')!=system or not set(handles).intersection(e.get('source_handles',[])):continue
            try:
                t=pos(e['path'],xy);length=sum(math.dist(a,b) for a,b in zip(e['path'],e['path'][1:]))
                if TOL<t<length-TOL:target.append(e)
            except ValueError:pass
        if len(target)!=1:raise ValueError('current main is not unique at candidate')
        main=target[0];canon=[x for x in handles if x in main.get('source_handles',[])]
        if len(canon)!=1:raise ValueError('main provenance ambiguous')
        endpoints=[nodes.get(branch.get(k)) for k in ('start_node_id','end_node_id')];terminal=[n for n in endpoints if n and n.get('subtype')=='unresolved_source_terminal'];remote=[n for n in endpoints if n and n.get('subtype')=='out_of_plane_interface']
        if len(terminal)!=1 or len(remote)!=1 or node.get('floor') is None or terminal[0].get('floor')!=node.get('floor') or remote[0].get('floor')!=node.get('floor'):raise ValueError('floor or terminal state differs')
        rim=min((branchline.dxf.start,branchline.dxf.end),key=lambda p:math.dist((p.x,p.y),xy))
        if abs(math.dist((rim.x,rim.y),xy)-circle.dxf.radius)>TOL or math.dist((terminal[0]['x'],terminal[0]['y']),(rim.x,rim.y))>TOL:raise ValueError('candidate rim mismatch')
        if sum(terminal[0]['node_id'] in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1:raise ValueError('terminal is not unique')
        # An opposite-system line through the circle centre cannot be silently merged.
        from cad_ceiling_native_rules import on
        for e in doc.modelspace().query('LINE'):
            other=LAYERS.get(e.dxf.layer)
            if other and other!=system and on(xy,(e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y),TOL) is not None:raise ValueError('opposite system at circle center')
        a,z=mains[0].dxf.start,mains[0].dxf.end;dx=z.x-a.x;dy=z.y-a.y;t=((xy[0]-a.x)*dx+(xy[1]-a.y)*dy)/(dx*dx+dy*dy);mz=a.z+t*(z.z-a.z)
        result.append({'circle_handle':h,'circle_layer':circle.dxf.layer,'circle_system':system,'line_system':system,'circle_layer_matches_lines':True,'center':xy,'radius':circle.dxf.radius,'main_handle':canon[0],'branch_handle':branches[0],'branch_rim':[rim.x,rim.y],'main_z_at_center':mz,'branch_z_at_rim':rim.z,'circle_z':circle.dxf.center.z,'z_consistent_within_tolerance':max(abs(mz-circle.dxf.center.z),abs(rim.z-circle.dxf.center.z))<=TOL,'main_graph_edges':[main['edge_id']],'branch_graph_edges':[branch['edge_id']],'rim_virtual_nodes':[terminal[0]['node_id']],'protected_boundaries':[],'status':'source_shape_graph_connection_not_established','coincident_native_main_handles':handles,'physical_main_identity':'unresolved','expert_control_circle':sel['control_circle'],'human_accepted':False})
    return {'source_sha256':source_hash,'graph_sha256':graph_hash,'candidates':result,'status':'technical_calibration_not_expert_acceptance'}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','graph','screen','review','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));screen=json.loads(a.screen.read_text(encoding='utf8'));review=json.loads(a.review.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
    out=prepare(doc,g,screen,review,policy,proof['source_sha256'],sha(a.graph),sha(a.screen),sha(a.review))
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'calibrated_candidates':len(out['candidates']),'human_accepted':False}))
if __name__=='__main__':main()
