"""Source-bound, opt-in direct DN *candidates*; does not modify a graph.

Only explicit policy-selected TEXT entities and native LINE witnesses are
examined. This is local evidence, not semantic approval of a whole edge, a
complete annotation inventory, T connectivity or a physical measurement.
"""
import argparse,hashlib,json,math,re
from pathlib import Path
from pipe_annotation_attributes import direct_diameters,source_texts,parse_dn_annotation
from source_readability import read_source
from native_dn_text_position import supported as supported_dn_text_position
LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def _projection(point,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
 if not den:return None
 u=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den
 foot=(a[0]+u*dx,a[1]+u*dy)
 return u,math.dist(point,foot),foot

def collect(doc,graph,policy,source_hash,graph_hash,tol=.1):
 if not math.isfinite(tol) or tol<=0:raise ValueError('invalid source tolerance')
 if not source_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash or policy.get('source_sha256')!=source_hash:raise ValueError('source hash mismatch')
 if not graph_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('graph hash mismatch')
 selected=policy.get('selections')
 if not isinstance(selected,list) or not selected:raise ValueError('empty selections')
 if len({x['text_handle'] for x in selected})!=len(selected) or len({x['edge_id'] for x in selected})!=len(selected):raise ValueError('duplicate text or edge selection')
 edges=graph['edges'];by_edge={e['edge_id']:e for e in edges}
 if len(by_edge)!=len(edges):raise ValueError('duplicate graph edge')
 texts=source_texts(doc,policy.get('source_id','source'),source_hash);by_handle={x['handle']:x for x in texts}
 layers=set(policy.get('text_layers',[]))
 if not layers:raise ValueError('missing text layers')
 assigned,pending=direct_diameters(texts,edges,set(),layers)
 # Any DN-bearing text outside the simple grammar can contain a transition
 # or system-qualified value. Project its location as a blocker only; never
 # infer its DN, order, system, or meaning from this synthetic probe.
 unparsed=[dict(t,text='DN1') for t in texts if t['layer'] in layers and re.search(r'DN',t['text'],re.I) and parse_dn_annotation(t['text']) is None]
 unparsed_assigned,unparsed_pending=direct_diameters(unparsed,edges,set(),layers)
 unparsed_hits=unparsed_assigned+unparsed_pending
 assigned_by_id={x['text']['handle']:x for x in assigned}
 result=[]
 for item in selected:
  h=item['text_handle'];edge_id=item['edge_id'];source_line=item['source_line_handle'];text=by_handle.get(h);edge=by_edge.get(edge_id)
  if not text or not edge or text['entity_type']!='TEXT' or text['layer'] not in layers or text['text']!=item['expected_text']:raise ValueError('selected source text mismatch')
  native=doc.entitydb.get(h)
  if native not in doc.modelspace() or not supported_dn_text_position(native):raise ValueError('unsupported text transform')
  label=parse_dn_annotation(text['text']);row=assigned_by_id.get(h)
  if not label or not row or row['edge_id']!=edge_id:raise ValueError('source annotation match is ambiguous or changed')
  if any(edge_id in x['candidate_edge_ids'] for x in pending):raise ValueError('pending annotation overlaps selected edge')
  if any(edge_id in x['candidate_edge_ids'] for x in unparsed_hits):raise ValueError('unparsed DN annotation overlaps selected edge')
  for other in assigned:
   if other['edge_id']==edge_id and other['nominal_mm']!=label['nominal_mm']:raise ValueError('conflicting direct annotations')
  line=doc.entitydb.get(source_line)
  if not line or line not in doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS.get(edge.get('system')) or source_line not in edge.get('source_handles',[]):raise ValueError('source line or system mismatch')
  a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y);point=row['point'];projected=_projection(point,a,b)
  if not projected or not 0<projected[0]<1 or projected[1]>tol:raise ValueError('edge text projection not on native line')
  # Compare against every parallel, modelspace native pipe LINE, including
  # those omitted from graph. Shorter source primitives need no graph link.
  angle=math.radians(text['rotation']);u=(math.cos(angle),math.sin(angle));native_hits=[]
  for e in doc.modelspace().query('LINE'):
   if e.dxf.layer not in LAYERS.values():continue
   a=(e.dxf.start.x,e.dxf.start.y);b=(e.dxf.end.x,e.dxf.end.y);dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
   if not length or abs(u[0]*dy-u[1]*dx)/length>math.sin(math.radians(2)):continue
   candidate=_projection(text['position'],a,b)
   if candidate and 0<candidate[0]<1 and candidate[1]<=2*text['height']:native_hits.append((candidate[1],e.dxf.handle))
  native_hits.sort()
  if not native_hits or native_hits[0][1]!=source_line or (len(native_hits)>1 and native_hits[1][0]-native_hits[0][0]<=.5*text['height']):raise ValueError('native source pipe match is ambiguous')
  result.append({'edge_id':edge_id,'system':edge['system'],'nominal_mm':label['nominal_mm'],'parenthesized_source_value':label['parenthesized_source_value'],'status':'candidate_source_annotation','source_text':text,'source_line_handle':source_line,'graph_projection':list(point),'source_pipe_candidates':[{'handle':h,'distance':distance} for distance,h in native_hits], 'limitations':['candidate only; source glyph semantics and edge-wide applicability require independent review','modelspace LINE/TEXT only; no nested, proxy, or F-leader classification','parenthesized value is retained without physical interpretation']})
 return {'schema_version':1,'source_sha256':source_hash,'graph_sha256':graph_hash,'status':'candidate_not_accepted','observations':result,'graph_mutated':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','graph','policy','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);graph_bytes=a.graph.read_bytes();graph=json.loads(graph_bytes);policy=json.loads(a.policy.read_text(encoding='utf8'))
 result=collect(doc,graph,policy,proof['source_sha256'],hashlib.sha256(graph_bytes).hexdigest());result['policy_sha256']=hashlib.sha256(a.policy.read_bytes()).hexdigest();result['extractor_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['text_guard_sha256']=hashlib.sha256(Path(__file__).with_name('native_dn_text_position.py').read_bytes()).hexdigest();result['source_preflight']=proof
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'observations':len(result['observations'])},ensure_ascii=False))
if __name__=='__main__':main()
