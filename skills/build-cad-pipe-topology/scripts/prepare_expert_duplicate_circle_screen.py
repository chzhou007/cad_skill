"""Bind scoped expert circle feedback to a current graph with coincident source mains.

This produces a screen only. It does not establish physical pipe identity or
authorize an unselected branch; the subsequent reconstruction retains ambiguity.
"""
import argparse,hashlib,json,math
from pathlib import Path
from duplicate_native_main_diagnostics import same_line
from repair_confirmed_circle_junctions import pos
from source_circle_rim_tee_screen import LAYERS
from source_readability import read_source

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(doc,graph,screen,issue,policy,source_hash,graph_hash,screen_hash,issue_hash):
    if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or
        policy.get('screen_sha256')!=screen_hash or policy.get('issue_sha256')!=issue_hash or
        screen.get('source_sha256')!=source_hash or screen.get('graph_sha256')!=graph_hash or
        graph.get('metadata',{}).get('source_sha256')!=source_hash or issue.get('sourceHashes',{}).get('main_dxf')!=source_hash):
        raise ValueError('source or graph evidence identity mismatch')
    mark=issue.get('issue',{});bounds=mark.get('sourceBounds',[])
    if mark.get('id')!=policy.get('issue_id') or not mark.get('note') or len(bounds)!=4 or bounds[2]<=0 or bounds[3]<=0:
        raise ValueError('invalid expert issue')
    amb={c['circle_handle']:c for c in screen.get('ambiguous_native_geometry',[])}
    edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    if len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph ID')
    rows=[];selected=policy.get('selections',[])
    if not selected or len({x['circle_handle'] for x in selected})!=len(selected):raise ValueError('invalid selections')
    for sel in selected:
        c=amb.get(sel['circle_handle']);main=edges.get(sel['main_edge']);branch=edges.get(sel['branch_edge']);terminal=nodes.get(sel['terminal'])
        if not c or not main or not branch or not terminal:raise ValueError('candidate missing')
        if sel['terminal'] not in mark.get('nodes',[]) or sel['main_edge'] not in mark.get('edges',[]) or sel['branch_edge'] not in mark.get('edges',[]):raise ValueError('expert issue does not select graph objects')
        system=c['system'];mh=c['main_handles'];bh=c['branch_handles']
        if len(mh)<2 or len(bh)!=1 or main['system']!=system or branch['system']!=system or terminal.get('system')!=system or terminal.get('subtype')!='unresolved_source_terminal':raise ValueError('ambiguous system or terminal')
        if terminal['node_id'] not in (branch.get('start_node_id'),branch.get('end_node_id')) or bh[0] not in branch.get('source_handles',[]):raise ValueError('branch graph identity mismatch')
        circle=doc.entitydb.get(c['circle_handle']);lines=[doc.entitydb.get(h) for h in mh];b=doc.entitydb.get(bh[0])
        if circle is None or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or b is None or b.dxftype()!='LINE' or b not in doc.modelspace() or any(x is None or x not in doc.modelspace() for x in lines):raise ValueError('native entities missing')
        if tuple(circle.dxf.extrusion)!=(0.,0.,1.) or not math.isfinite(circle.dxf.radius) or circle.dxf.radius<=0 or not all(math.isfinite(v) for v in circle.dxf.center):raise ValueError('unsupported native circle transform or geometry')
        if any(not same_line(lines[0],x,.05) for x in lines[1:]) or any(LAYERS.get(x.dxf.layer)!=system for x in [*lines,b]) or LAYERS.get(circle.dxf.layer)!=system:raise ValueError('native main coincidence or system mismatch')
        xy=[circle.dxf.center.x,circle.dxf.center.y]
        pos([[lines[0].dxf.start.x,lines[0].dxf.start.y],[lines[0].dxf.end.x,lines[0].dxf.end.y]],xy)
        if not(bounds[0]<=xy[0]<=bounds[0]+bounds[2] and bounds[1]<=xy[1]<=bounds[1]+bounds[3]):raise ValueError('circle outside expert marked region')
        at=[]
        for e in edges.values():
            if e['system']!=system or not set(mh).intersection(e.get('source_handles',[])):continue
            try:
                offset=pos(e['path'],xy);length=sum(math.dist(a,b) for a,b in zip(e['path'],e['path'][1:]))
                if .05<offset<length-.05:at.append(e['edge_id'])
            except ValueError:pass
        if at!=[main['edge_id']]:raise ValueError('main graph path not unique at source circle')
        canonical=[h for h in mh if h in main.get('source_handles',[])]
        if len(canonical)!=1:raise ValueError('canonical graph source reference is ambiguous')
        endpoints=[b.dxf.start,b.dxf.end];rim=min(endpoints,key=lambda p:math.dist((p.x,p.y),xy))
        if abs(math.dist((rim.x,rim.y),xy)-circle.dxf.radius)>.05 or math.dist((terminal['x'],terminal['y']),(rim.x,rim.y))>.05:raise ValueError('branch does not meet circle rim')
        if sum(terminal['node_id'] in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1:raise ValueError('terminal degree changed')
        a,z=lines[0].dxf.start,lines[0].dxf.end;dx=z.x-a.x;dy=z.y-a.y;t=((xy[0]-a.x)*dx+(xy[1]-a.y)*dy)/(dx*dx+dy*dy);mz=a.z+t*(z.z-a.z)
        rows.append({'circle_handle':c['circle_handle'],'circle_layer':circle.dxf.layer,'circle_system':system,'line_system':system,'circle_layer_matches_lines':True,'center':xy,'radius':circle.dxf.radius,'main_handle':canonical[0],'branch_handle':bh[0],'branch_rim':[rim.x,rim.y],'main_z_at_center':mz,'branch_z_at_rim':rim.z,'circle_z':circle.dxf.center.z,'z_consistent_within_tolerance':max(abs(mz-circle.dxf.center.z),abs(rim.z-circle.dxf.center.z))<=.05,'main_graph_edges':[main['edge_id']],'branch_graph_edges':[branch['edge_id']],'rim_virtual_nodes':[terminal['node_id']],'protected_boundaries':[],'status':'source_shape_graph_connection_not_established','coincident_native_main_handles':mh,'physical_main_identity':'unresolved'})
    return {'source_sha256':source_hash,'graph_sha256':graph_hash,'candidates':rows,'status':'expert_scoped_duplicate_main_screen_not_physical_identity'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','graph','screen','issue','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));screen=json.loads(a.screen.read_text(encoding='utf8'));issue=json.loads(a.issue.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
    result=prepare(doc,g,screen,issue,policy,proof['source_sha256'],sha(a.graph),sha(a.screen),sha(a.issue));a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'expert-scoped-circle-screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'selected':len(result['candidates']),'physical_main_identity':'unresolved'}))
if __name__=='__main__':main()
