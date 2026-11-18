"""Replay a named riser TEXT, underline and leader to a native target.

The evidence is local. Identical names in a main view and detail are not merged;
DN is an annotation observation, never an edge-wide value or installed length.
"""
import argparse,hashlib,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS,_on


def label(value):
    match=re.fullmatch(r'\s*(CHW([SR])\s*([1-9]\d*))\s+DN\s*([1-9]\d*(?:\.\d+)?)\s*',value,re.I)
    if not match:raise ValueError('unsupported named riser annotation')
    nominal=float(match[4])
    if not math.isfinite(nominal) or nominal<=0:raise ValueError('nonfinite named riser DN')
    return dict(identifier='CHW'+match[2].upper()+match[3],system='supply' if match[2].upper()=='S' else 'return',nominal_mm_observed=nominal)


def xyz(line):return [list(line.dxf.start),list(line.dxf.end)]


def at(point,line,tol=.05):
    a,b=xyz(line);delta=[b[i]-a[i] for i in range(3)];den=sum(x*x for x in delta)
    if not all(math.isfinite(x) for p in (point,a,b) for x in p) or den<=tol*tol:return False
    t=sum((point[i]-a[i])*delta[i] for i in range(3))/den
    return -tol/math.sqrt(den)<=t<=1+tol/math.sqrt(den) and math.dist(point,[a[i]+t*delta[i] for i in range(3)])<=tol


def underlines(doc,text,layers):
    p=list(text.dxf.insert);angle=math.radians(text.dxf.rotation);u=[math.cos(angle),math.sin(angle)];normal=[-u[1],u[0]];result=[]
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer not in layers:continue
        a,b=xyz(line);length=math.dist(a,b)
        if length<=.05 or abs(a[2]-b[2])>.05 or abs(p[2]-a[2])>.05:continue
        direction=[(b[i]-a[i])/length for i in (0,1)]
        if abs(u[0]*direction[1]-u[1]*direction[0])>math.sin(math.radians(2)):continue
        t=sum((p[i]-a[i])*(b[i]-a[i]) for i in (0,1))/(length*length)
        q=[a[i]+t*(b[i]-a[i]) for i in (0,1)];signed=sum((p[i]-q[i])*normal[i] for i in (0,1))
        if -.05/length<=t<=1+.05/length and .05<abs(signed)<=.5*text.dxf.height:result.append(line)
    return result


def collect(doc,graph,policy,source_hash,graph_hash):
    if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash):raise ValueError('named riser source/graph differs')
    text_layers=set(policy.get('text_layers',[]));leader_layers=set(policy.get('leader_layers',[]));specs=policy.get('selections',[])
    if not text_layers or not leader_layers or not specs or len({s['text_handle'] for s in specs})!=len(specs):raise ValueError('invalid named riser scope')
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph IDs')
    lines=list(doc.modelspace().query('LINE'));records=[]
    for spec in specs:
        text=doc.entitydb.get(spec['text_handle'])
        if not text or text not in doc.modelspace() or not supported(text) or text.dxf.layer not in text_layers or text.plain_text()!=spec.get('expected_text'):raise ValueError('native named riser text differs')
        parsed=label(text.plain_text());under=underlines(doc,text,leader_layers)
        if len(under)!=1 or under[0].dxf.handle!=spec['underline_handle']:raise ValueError('named riser underline is ambiguous or changed')
        underline=under[0];joins=[]
        for line in lines:
            if line is underline or line.dxf.layer not in leader_layers:continue
            for ui,u in enumerate(xyz(underline)):
                for li,p in enumerate(xyz(line)):
                    if math.dist(u,p)<=.05:joins.append((line,ui,li))
        if len(joins)!=1 or joins[0][0].dxf.handle!=spec['leader_handle']:raise ValueError('named riser leader is ambiguous or changed')
        leader,ui,li=joins[0];tip=xyz(leader)[1-li]
        target=spec['target'];kind=target.get('kind');proof={}
        if kind=='plan_riser_circle':
            node=nodes.get(target['node_id']);circle=doc.entitydb.get(target['circle_handle'])
            if (not node or node.get('subtype')!='out_of_plane_riser' or node.get('system')!=parsed['system'] or node.get('source_handle')!=target['circle_handle']
                or not circle or circle not in doc.modelspace() or circle.dxftype()!='CIRCLE' or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.)
                or not all(math.isfinite(x) for x in (*circle.dxf.center,node['x'],node['y']))
                or not math.isfinite(circle.dxf.radius) or circle.dxf.radius<=0 or math.dist(tip,list(circle.dxf.center))>.05 or math.dist([node['x'],node['y']],list(circle.dxf.center)[:2])>.05):raise ValueError('named riser circle/node target differs')
            incident=[e for e in edges.values() if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
            if len(incident)!=1 or incident[0]['system']!=parsed['system']:raise ValueError('named riser interface incidence differs')
            proof=dict(node_id=node['node_id'],floor=node['floor'],circle_handle=circle.dxf.handle,circle_center=list(circle.dxf.center),circle_radius=circle.dxf.radius,incident_edge=incident[0]['edge_id'])
        elif kind in ('axis_source_line','axis_source_corner','axis_source_junction'):
            hits=[line for line in lines if line.dxf.layer in LAYERS.values() and at(tip,line)]
            expected=[target['line_handle']] if kind=='axis_source_line' else target.get('line_handles',[])
            required={'axis_source_line':1,'axis_source_corner':2,'axis_source_junction':3}[kind]
            if (len(hits)!=required or sorted(l.dxf.handle for l in hits)!=sorted(expected)
                or any(l.dxf.layer!=LAYERS[parsed['system']] for l in hits)):raise ValueError('named riser source pipe target ambiguous or changed')
            if kind in ('axis_source_corner','axis_source_junction'):
                if any(sum(math.dist(tip,p)<=.05 for p in xyz(l))!=1 for l in hits):raise ValueError('named riser corner is an interior crossing')
                rays=[]
                for native in hits:
                    remote=next(p for p in xyz(native) if math.dist(tip,p)>.05);v=[remote[i]-tip[i] for i in range(3)];length=math.sqrt(sum(x*x for x in v));rays.append([x/length for x in v])
                dots=[sum(a*b for a,b in zip(rays[i],rays[j])) for i in range(len(rays)) for j in range(i+1,len(rays))]
                if kind=='axis_source_corner' and abs(dots[0])>=math.cos(math.radians(2)):raise ValueError('named riser corner is not a two-arm bend')
                if kind=='axis_source_junction' and (max(dots)>=math.cos(math.radians(2)) or min(dots)>-math.cos(math.radians(2))):raise ValueError('named riser junction lacks three distinct T rays')
            line=hits[0];coverage=[];continuations=[]
            for edge in edges.values():
                if edge['system']!=parsed['system']:continue
                for pi,path in enumerate(edge.get('attribute_paths',[])):
                    for si,(a,b) in enumerate(zip(path,path[1:])):
                        if _on(tip[:2],a,b,.05):coverage.append(dict(edge_id=edge['edge_id'],path_index=pi,segment_index=si))
            # Record native contacts even when the legacy graph omitted a cap
            # stub. These are source candidates, never a silent graph extension.
            for endpoint in xyz(line):
                incident=[other for other in lines if other.dxf.layer==line.dxf.layer and any(math.dist(endpoint,p)<=.05 for p in xyz(other))]
                if len(incident)<2:continue
                continuations.append(dict(point=endpoint,source_handles=[other.dxf.handle for other in incident],graph_nodes=[n['node_id'] for n in nodes.values() if math.dist(endpoint[:2],[n['x'],n['y']])<=.05],connection_accepted=False))
            if kind=='axis_source_corner':
                if len(coverage)!=2 or len({(c['edge_id'],c['path_index']) for c in coverage})!=1 or abs(coverage[0]['segment_index']-coverage[1]['segment_index'])!=1:raise ValueError('named riser corner lacks one current graph path')
                paths=edges[coverage[0]['edge_id']]['attribute_paths'];index=coverage[0]['path_index'];segments=sorted(c['segment_index'] for c in coverage)
                for native in hits:
                    matches=[si for si in segments if all(at([*p,tip[2]],native) for p in (paths[index][si],paths[index][si+1]))]
                    if len(matches)!=1:raise ValueError('named riser corner native/graph segment differs')
                proof=dict(source_line_handles=sorted(expected),native_lines=[dict(handle=l.dxf.handle,XYZ=xyz(l)) for l in hits],target_graph_coverage=coverage,native_endpoint_contacts=continuations,one_graph_corner_not_a_new_T=True)
            elif kind=='axis_source_junction':
                at_nodes=[n['node_id'] for n in nodes.values() if math.dist(tip[:2],[n['x'],n['y']])<=.05]
                proof=dict(source_line_handles=sorted(expected),native_lines=[dict(handle=l.dxf.handle,XYZ=xyz(l)) for l in hits],target_graph_coverage=coverage,native_endpoint_contacts=continuations,
                    native_three_endpoint_T=True,current_graph_nodes=at_nodes,local_topology_recheck_required=True,connection_accepted=False)
            else:proof=dict(source_line_handle=line.dxf.handle,native_XYZ=xyz(line),target_graph_coverage=coverage,native_endpoint_contacts=continuations)
        else:raise ValueError('unsupported named riser target kind')
        records.append(dict(**parsed,source_text=dict(handle=text.dxf.handle,text=text.plain_text(),layer=text.dxf.layer,position=list(text.dxf.insert),rotation=text.dxf.rotation,height=text.dxf.height),
            underline=dict(handle=underline.dxf.handle,layer=underline.dxf.layer,XYZ=xyz(underline)),leader=dict(handle=leader.dxf.handle,layer=leader.dxf.layer,XYZ=xyz(leader),target_point=tip),target_kind=kind,target=proof,
            physical_diameter_selected=False,physical_length_mm=None,physical_ports_verified=False,crossview_mapping_confirmed=False,human_accepted=False))
    return dict(status='native_named_riser_annotations_replayed_not_crossview_mapping',source_sha256=source_hash,graph_sha256=graph_hash,records=records,graph_mutated=False,hil_ready=False,human_accepted=False,
        limitations=['Selected modelspace TEXT and LINE leaders only. Separately declared two-arm bends require one current graph path; three native endpoint T rays are recorded as requiring local topology recheck. Other multiple targets fail closed. Unsupported transforms/nested leaders remain pending.','Equal identifiers across repeated views are correspondence evidence, not permission to merge local topology or duplicate physical quantities.','DN remains a local named-riser annotation. No diameter inheritance, whole-edge value, installed length or shaft ownership is inferred.','Uncovered axis target pipes and native endpoint contacts must return to local source comparison before mapping.'])


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source);result=collect(doc,load(a.graph),load(a.policy),sha(a.source),sha(a.graph))
    result.update(policy_sha256=sha(a.policy),source_preflight=preflight,implementation_sha256={name:sha(Path(__file__).with_name(name)) for name in ('native_named_riser_evidence.py','native_dn_text_position.py','native_line_path_evidence.py','source_readability.py')})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encode(result));print({'records':len(result['records']),'graph_mutated':False,'mapping_confirmed':False},flush=True)


if __name__=='__main__':main()
