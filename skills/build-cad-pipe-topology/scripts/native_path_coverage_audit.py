"""Audit source coverage of selected isometric path segments, without graph edits."""
import argparse,hashlib,json,math
from pathlib import Path
from ezdxf.disassemble import recursive_decompose
from native_line_path_evidence import _on,LAYERS
from source_readability import read_source

def audit(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph hash mismatch')
 edges={e['edge_id']:e for e in graph['edges']};selected=policy.get('edges',[])
 if len(edges)!=len(graph['edges']) or not selected or len(set(selected))!=len(selected):raise ValueError('invalid edge selections')
 rows=[]
 for eid in selected:
  e=edges.get(eid)
  if not e or e.get('system') not in LAYERS or len(e.get('attribute_paths',[]))!=1:raise ValueError('unsupported graph edge')
  nested=[];handle=e.get('source_insert_handle')
  if handle:
   insert=doc.entitydb.get(handle)
   if not insert or insert not in doc.modelspace():raise ValueError('source insert mismatch')
   if insert.dxftype()=='INSERT':
    nested=[x for x in recursive_decompose([insert]) if x.dxftype()=='LINE' and x.dxf.layer==LAYERS[e['system']]]
   elif insert.dxftype()=='LWPOLYLINE' and insert.dxf.layer=='DIM_SYMB' and e.get('connection_mode') in ('standalone_multiport_omission_stitched_by_order','standalone_omission_to_first_tee'):
    nodes=[n for n in graph.get('nodes',[]) if n.get('node_id') in (e.get('start_node_id'),e.get('end_node_id')) and n.get('source_marker_handle')==handle and n.get('node_type')=='virtual_equipment']
    if len(nodes)!=1:raise ValueError('marker node mismatch')
    n=nodes[0];side='start' if e.get('start_node_id')==n['node_id'] else 'end';ports=[p for p in n.get('ports',[]) if p.get('port_id')==e.get(side+'_port_id') and p.get('system')==e['system']]
    path=e['attribute_paths'][0];points=(path[0],path[1]) if side=='start' else (path[-1],path[-2])
    if len(ports)!=1 or math.dist(points[0],[n['x'],n['y']])>tol or math.dist(points[1],[ports[0]['x'],ports[0]['y']])>tol:raise ValueError('marker port mismatch')
    # Marker is drawing evidence, never itself a same-system pipe witness.
   else:raise ValueError('source insert mismatch')
  candidates=[(x,'modelspace',x.dxf.handle) for x in doc.modelspace().query('LINE') if x.dxf.layer==LAYERS[e['system']]]+[(x,'decomposed_selected_insert',handle) for x in nested]
  segments=[]
  for i,(a,b) in enumerate(zip(e['attribute_paths'][0],e['attribute_paths'][0][1:])):
   if len(a)!=2 or len(b)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in a+b) or math.dist(a,b)<=tol:raise ValueError('invalid graph segment')
   hits=[]
   for x,kind,h in candidates:
    v,w=x.dxf.start,x.dxf.end;p=(v.x,v.y);q=(w.x,w.y)
    if _on(a,p,q,tol) and _on(b,p,q,tol):hits.append({'scope':kind,'source_handle':h,'layer':x.dxf.layer,'start':list(p),'end':list(q)})
   status='single_source_line_covers' if len(hits)==1 else 'no_witness_in_scoped_search' if not hits else 'ambiguous_multiple_witnesses'
   segments.append({'index':i,'start':a,'end':b,'drawing_length':math.dist(a,b),'status':status,'witnesses':hits})
  rows.append({'edge_id':eid,'system':e['system'],'connection_mode':e.get('connection_mode'),'source_insert_handle':handle,'segments':segments,'source_covered_drawing_length':sum(x['drawing_length'] for x in segments if x['status']=='single_source_line_covers'),'unverified_drawing_length':sum(x['drawing_length'] for x in segments if x['status']!='single_source_line_covers'),'physical_length':'unknown','status':'source_geometry_audit_unreviewed'})
 return {'status':'partial_source_coverage_not_physical_length','source_sha256':source_hash,'graph_sha256':graph_hash,'edges':rows,'graph_mutated':False,'hil_ready':False,'limitations':['Only modelspace same-system LINE and LINE descendants of the edge selected INSERT are searched; other blocks, polylines, arcs and proxies are not covered.','Missing witness is unverified, not proof that no source entity exists or that a segment is synthetic.','Covered graph drawing length is not physical pipe length or proof of equipment port connectivity.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest();r=audit(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'edges':len(r['edges']),'missing_or_ambiguous_segments':sum(s['status']!='single_source_line_covers' for e in r['edges'] for s in e['segments']),'status':r['status']}))
if __name__=='__main__':main()
