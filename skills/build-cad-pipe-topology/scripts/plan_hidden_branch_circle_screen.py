"""Screen possible hidden plan branches against same-service native main circles.

This is a bounded candidate inventory, not a connection inference. It does not
modify a graph or decide whether an apparent crossing is connected.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from repair_confirmed_circle_junctions import pos
from source_readability import read_source

TOL = .05


def cross(a,b):return a[0]*b[1]-a[1]*b[0]


def screen(doc, graph, policy, source_hash, graph_hash):
    if policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash or graph.get('metadata',{}).get('source_sha256') != source_hash:
        raise ValueError('source or graph hash mismatch')
    radii = policy.get('radius_range', [])
    max_extension = policy.get('max_extension')
    max_offset = policy.get('max_along_main_offset')
    layers = policy.get('system_layers')
    if (not isinstance(radii,list) or len(radii)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in radii) or radii[0]>radii[1] or
        not isinstance(max_extension,(int,float)) or not math.isfinite(max_extension) or max_extension<=0 or
        not isinstance(max_offset,(int,float)) or not math.isfinite(max_offset) or max_offset<=0 or not isinstance(layers,dict) or not layers):
        raise ValueError('invalid screening bounds or system layers')
    nodes={n['node_id']:n for n in graph['nodes']}; edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph ID')
    circles=[c for c in doc.modelspace().query('CIRCLE') if radii[0]<=c.dxf.radius<=radii[1]]
    tees=[n for n in nodes.values() if n.get('node_type') in ('tee','physical_junction')]
    candidates=[]; ambiguous=[]
    for terminal in nodes.values():
        if terminal.get('subtype')!='unresolved_source_terminal' or terminal.get('system') not in layers:continue
        incident=[e for e in edges.values() if terminal['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=1:
            ambiguous.append({'terminal':terminal['node_id'],'reason':'not_single_incident_edge'});continue
        branch=incident[0];system=terminal['system'];point=[terminal['x'],terminal['y']]
        if branch.get('system')!=system:
            ambiguous.append({'terminal':terminal['node_id'],'reason':'branch_system_mismatch'});continue
        source=[]
        for h in branch.get('source_handles',[]):
            line=doc.entitydb.get(h)
            if not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=layers[system]:continue
            ends=[[v.x,v.y] for v in (line.dxf.start,line.dxf.end)]
            if min(math.dist(point,v) for v in ends)<=TOL:
                other=max(ends,key=lambda x:math.dist(x,point));vec=[point[0]-other[0],point[1]-other[1]];length=math.hypot(*vec)
                if length>TOL:source.append((h,[vec[0]/length,vec[1]/length]))
        if len(source)!=1:
            if source:ambiguous.append({'terminal':terminal['node_id'],'reason':'multiple_native_branch_directions','handles':[x[0] for x in source]})
            continue
        branch_handle, direction=source[0]
        for main in edges.values():
            if main['edge_id']==branch['edge_id'] or main.get('system')!=system:continue
            for handle in main.get('source_handles',[]):
                line=doc.entitydb.get(handle)
                if not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=layers[system]:continue
                a=[line.dxf.start.x,line.dxf.start.y];b=[line.dxf.end.x,line.dxf.end.y];axis=[b[0]-a[0],b[1]-a[1]];length=math.hypot(*axis)
                if length<=TOL:continue
                axis=[axis[0]/length,axis[1]/length];denom=cross(direction,axis)
                if abs(denom)<1e-6:continue
                delta=[a[0]-point[0],a[1]-point[1]];extension=cross(delta,axis)/denom;along=cross(delta,direction)/denom
                if extension<=TOL or extension>max_extension or along < -TOL or along > length+TOL:continue
                projection=[a[0]+along*axis[0],a[1]+along*axis[1]]
                try:pos(main['path'],projection)
                except ValueError:continue
                for circle in circles:
                    center=[circle.dxf.center.x,circle.dxf.center.y];offset=(center[0]-a[0])*axis[0]+(center[1]-a[1])*axis[1]
                    if offset < -TOL or offset > length+TOL or abs(cross([center[0]-a[0],center[1]-a[1]],axis))>TOL or abs(offset-along)>max_offset:continue
                    try:pos(main['path'],center)
                    except ValueError:continue
                    if any(t.get('system')==system and math.dist([t['x'],t['y']],center)<=TOL for t in tees):continue
                    candidates.append({'terminal':terminal['node_id'],'branch_edge':branch['edge_id'],'branch_handle':branch_handle,'system':system,'main_edge':main['edge_id'],'main_handle':handle,'circle_handle':circle.dxf.handle,'circle_layer':circle.dxf.layer,'circle_center':center,'projection':projection,'extension_drawing_units':extension,'circle_offset_drawing_units':abs(offset-along),'status':'candidate_not_connectivity_proof'})
    candidates.sort(key=lambda x:(x['terminal'],x['main_edge'],x['circle_handle']))
    return {'status':'candidates_not_connectivity_proof','source_sha256':source_hash,'graph_sha256':graph_hash,'bounds':{'radius_range':radii,'max_extension':max_extension,'max_along_main_offset':max_offset},'candidates':candidates,'ambiguous':ambiguous,'limitations':['Only modelspace native LINE/CIRCLE, supported unresolved endpoints, and declared radii/layers are considered.','Screen bounds affect recall and do not establish physical distance or length.','The circle layer is recorded but does not establish the service.','Candidates require source comparison and applicable human evidence; proximity does not authorize a repair.']}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
    result=screen(doc,g,policy,proof['source_sha256'],sha(a.graph));result.update(policy_sha256=sha(a.policy),script_sha256=sha(__file__),source_preflight=proof)
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'candidates':len(result['candidates']),'ambiguous':len(result['ambiguous']),'status':result['status']}))


if __name__=='__main__':main()
