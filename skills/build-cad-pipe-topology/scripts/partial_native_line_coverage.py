"""Measure source LINE overlap on selected incompletely witnessed graph segments.

This sidecar does not mutate topology or establish a physical pipe length.
"""
import argparse, hashlib, json, math
from pathlib import Path
from native_line_path_evidence import LAYERS
from source_readability import read_source


def intervals(a, b, lines, tol=.05):
    length=math.dist(a,b)
    if not math.isfinite(length) or length<=tol: raise ValueError('invalid segment')
    ux=(b[0]-a[0])/length;uy=(b[1]-a[1])/length
    hits=[]
    for handle,p,q in lines:
        if math.dist(p,q)<=tol: continue
        # Both source endpoints must lie on the graph's infinite axis; this
        # rejects transverse crossings and parallel lines outside tolerance.
        if max(abs((x[0]-a[0])*uy-(x[1]-a[1])*ux) for x in (p,q))>tol: continue
        u=sorted((x[0]-a[0])*ux+(x[1]-a[1])*uy for x in (p,q))
        lo=max(0.,u[0]);hi=min(length,u[1])
        if hi-lo>tol: hits.append((lo,hi,handle))
    cuts=sorted({0.,length,*[v for lo,hi,_ in hits for v in (lo,hi)]})
    pieces=[]
    for lo,hi in zip(cuts,cuts[1:]):
        if hi-lo<=1e-9: continue
        mid=(lo+hi)/2;handles=sorted(h for start,end,h in hits if start<=mid<=end)
        state='unwitnessed' if not handles else 'unique_source_line' if len(handles)==1 else 'ambiguous_overlapping_lines'
        pieces.append({'start_distance':lo,'end_distance':hi,'drawing_length':hi-lo,'status':state,'source_handles':handles})
    return pieces


def audit(doc, graph, coverage, policy, source_hash, graph_hash, coverage_hash):
    if any(policy.get(k)!=v for k,v in [('source_sha256',source_hash),('graph_sha256',graph_hash),('coverage_sha256',coverage_hash)]):raise ValueError('stale policy')
    if coverage.get('status')!='partial_source_coverage_not_physical_length' or coverage.get('source_sha256')!=source_hash or coverage.get('graph_mutated') is not False:raise ValueError('stale coverage')
    edges={e['edge_id']:e for e in graph['edges']};rows={e['edge_id']:e for e in coverage['edges']};choices=policy.get('selections')
    if len(edges)!=len(graph['edges']) or len(rows)!=len(coverage['edges']) or not isinstance(choices,list) or not choices:raise ValueError('invalid coverage selections')
    lines={system:[(x.dxf.handle,(x.dxf.start.x,x.dxf.start.y),(x.dxf.end.x,x.dxf.end.y)) for x in doc.modelspace().query('LINE') if x.dxf.layer==layer] for system,layer in LAYERS.items()}
    result=[];seen=set()
    for sel in choices:
        eid=sel.get('edge_id');idx=sel.get('segment_index');key=(eid,idx)
        if key in seen or not isinstance(idx,int) or isinstance(idx,bool) or idx<0:raise ValueError('invalid selection')
        seen.add(key);edge=edges.get(eid);row=rows.get(eid)
        if not edge or not row or edge.get('system') not in lines or edge.get('system')!=row.get('system') or len(edge.get('attribute_paths',[]))!=1:raise ValueError('edge mismatch')
        path=edge['attribute_paths'][0];segments=row['segments']
        if idx>=len(path)-1 or idx>=len(segments):raise ValueError('segment out of range')
        part=segments[idx];a,b=path[idx:idx+2]
        if part.get('index')!=idx or part.get('start')!=a or part.get('end')!=b or part.get('status') not in ('no_witness_in_scoped_search','ambiguous_multiple_witnesses'):raise ValueError('coverage segment mismatch')
        pieces=intervals(a,b,lines[edge['system']]);result.append({'edge_id':eid,'system':edge['system'],'segment_index':idx,'start':a,'end':b,'drawing_length':math.dist(a,b),'pieces':pieces,'unique_source_drawing_length':sum(x['drawing_length'] for x in pieces if x['status']=='unique_source_line'),'unwitnessed_drawing_length':sum(x['drawing_length'] for x in pieces if x['status']=='unwitnessed'),'ambiguous_drawing_length':sum(x['drawing_length'] for x in pieces if x['status']=='ambiguous_overlapping_lines'),'physical_length':'unknown'})
    return {'status':'partial_line_overlap_evidence_not_topology_fix','source_sha256':source_hash,'graph_sha256':graph_hash,'coverage_sha256':coverage_hash,'records':result,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Modelspace same-system LINEs only; nested lines, polylines, curves and proxies are not searched.','Drawing overlap is not a physical length, a pipe connection, or proof of source ownership.','Existing graph source-length totals are not changed.']}


def main():
    p=argparse.ArgumentParser()
    for name in ('source','graph','coverage','policy','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
    result=audit(doc,load(a.graph),load(a.coverage),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.coverage));result.update(source_preflight=proof,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'segments':len(result['records'])}))
if __name__=='__main__':main()
