"""Read-only native DN label to source line and graph segment candidate inventory."""
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
from source_readability import read_source
from native_dn_text_position import supported as supported_dn_text_position
from pipe_annotation_attributes import parse_dn_annotation
from ezdxf.disassemble import recursive_decompose

def project(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
 if not den:return None
 u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den
 return u,(a[0]+u*dx,a[1]+u*dy),math.hypot(p[0]-a[0]-u*dx,p[1]-a[1]-u*dy)

def screen(doc,graph,policy):
 layers=policy.get('source_layer_systems',{});text_layers=set(policy.get('text_layers',[]));tol=policy.get('geometry_tolerance',.05)
 if not layers or not text_layers or not isinstance(tol,(int,float)) or isinstance(tol,bool) or not 0<tol<=1:raise ValueError('invalid screening configuration')
 endpoint_limit=policy.get('endpoint_context_max_text_heights',0)
 if isinstance(endpoint_limit,bool) or not isinstance(endpoint_limit,(int,float)) or not math.isfinite(endpoint_limit) or not 0<=endpoint_limit<=5:raise ValueError('invalid endpoint context configuration')
 edges=graph['edges'];ids=[e['edge_id'] for e in edges]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate graph edge IDs')
 lines=[]
 for ent in doc.modelspace().query('LINE'):
  if ent.dxf.layer not in layers:continue
  a=(ent.dxf.start.x,ent.dxf.start.y);b=(ent.dxf.end.x,ent.dxf.end.y);length=math.dist(a,b)
  if length>tol:lines.append((ent,a,b,length,{'scope':'modelspace','handle':ent.dxf.handle}))
 nested_summary={'enabled':policy.get('include_graph_insert_lines',False),'root_inserts':0,'non_insert_references':[],'failed_roots':[]}
 if nested_summary['enabled'] is not False and nested_summary['enabled'] is not True:raise ValueError('invalid nested-line policy')
 if nested_summary['enabled']:
  for handle in sorted({e.get('source_insert_handle') for e in edges if e.get('source_insert_handle')}):
   root=doc.entitydb.get(handle)
   if not root or root.dxftype()!='INSERT' or root not in doc.modelspace():
    nested_summary['non_insert_references'].append({'handle':handle,'type':root.dxftype() if root else 'missing'});continue
   nested_summary['root_inserts']+=1; pending=[]
   try:
    for ent in recursive_decompose([root]):
     if ent.dxftype()!='LINE' or ent.dxf.layer not in layers:continue
     a=(ent.dxf.start.x,ent.dxf.start.y);b=(ent.dxf.end.x,ent.dxf.end.y);length=math.dist(a,b)
     if not all(math.isfinite(x) for x in (*a,*b,ent.dxf.start.z,ent.dxf.end.z)):raise ValueError('non-finite decomposed line')
     if length>tol:pending.append((ent,a,b,length,{'scope':'graph_referenced_insert','root_handle':handle,'child_handle':None}))
    lines.extend(pending)
   except Exception as exc:
    nested_summary['failed_roots'].append({'handle':handle,'error':str(exc)})
 segments=[]
 for edge in edges:
  for path in edge.get('attribute_paths',[]):
   for a,b in zip(path,path[1:]):
    if len(a)!=2 or len(b)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in a+b):raise ValueError('invalid edge path')
    if math.dist(a,b)>tol:segments.append((edge['edge_id'],edge.get('system'),a,b))
 rows=[]
 for ent in doc.modelspace().query('TEXT MTEXT'):
  if ent.dxf.layer not in text_layers:continue
  raw=ent.plain_text();parsed=parse_dn_annotation(raw)
  if not parsed:continue
  row={'text_handle':ent.dxf.handle,'text':raw,'layer':ent.dxf.layer,'nominal_mm_candidate':parsed['nominal_mm'],'status':'unsupported_text_transform','edge_candidates':[],'human_accepted':False}
  if not supported_dn_text_position(ent):rows.append(row);continue
  p=(ent.dxf.insert.x,ent.dxf.insert.y);height=float(ent.dxf.height);angle=math.radians(ent.dxf.rotation)
  if not all(math.isfinite(x) for x in (*p,height,angle)) or height<=0:rows.append(row);continue
  hits=[];endpoint_hits=[]
  for line,a,b,length,provenance in lines:
   dx,dy=b[0]-a[0],b[1]-a[1]
   if abs(math.cos(angle)*dy-math.sin(angle)*dx)/length>math.sin(math.radians(2)):continue
   v=project(p,a,b)
   if v and 0<v[0]<1 and v[2]<=2*height:hits.append((v[2],line,a,b,v[1],provenance))
   if endpoint_limit and v and not 0<=v[0]<=1:
    endpoint=a if v[0]<0 else b;distance=math.dist(p,endpoint)
    if distance<=endpoint_limit*height:endpoint_hits.append((distance,line,a,b,endpoint,provenance,v[0]))
  hits.sort(key=lambda x:(x[0],x[5].get('handle',x[5].get('root_handle',''))));row.update(position=list(p),height=height,rotation_degrees=ent.dxf.rotation,native_line_candidates=[{'handle':h[5].get('handle'),'provenance':h[5],'system':layers[h[1].dxf.layer],'distance_drawing_units':h[0]} for h in hits])
  if not hits:
   row['status']='no_source_line_in_local_scope'
   if endpoint_limit:
    context=[]
    for distance,line,a,b,endpoint,provenance,u in sorted(endpoint_hits,key=lambda x:(x[0],x[5].get('handle',x[5].get('root_handle','')))):
     system=layers[line.dxf.layer];matches=[]
     for eid,esys,x,y in segments:
      if esys!=system:continue
      pa,pb,pe=project(x,a,b),project(y,a,b),project(endpoint,x,y)
      if pa and pb and pe and -.0001<=pa[0]<=1.0001 and -.0001<=pb[0]<=1.0001 and -.0001<=pe[0]<=1.0001 and max(pa[2],pb[2],pe[2])<=tol:matches.append({'edge_id':eid,'segment':[x,y]})
     context.append({'provenance':provenance,'system':system,'source_line_endpoints':[list(a),list(b)],'nearest_endpoint':list(endpoint),'distance_drawing_units':distance,'projection_fraction':u,'graph_segment_candidates':matches})
    row['endpoint_context_candidates']=context
   rows.append(row);continue
  if len(hits)>1 and hits[1][0]-hits[0][0]<=.5*height:row['status']='ambiguous_source_lines';rows.append(row);continue
  _,line,a,b,foot,provenance=hits[0];system=layers[line.dxf.layer];matches=[]
  along=project(p,a,b)[0];line_z=line.dxf.start.z+along*(line.dxf.end.z-line.dxf.start.z)
  row.update(source_text_z=ent.dxf.insert.z,source_line_z_at_projection=line_z,source_z_delta=ent.dxf.insert.z-line_z)
  for eid,esys,x,y in segments:
   if esys!=system:continue
   pa,pb,pf=project(x,a,b),project(y,a,b),project(foot,x,y)
   if pa and pb and pf and -.0001<=pa[0]<=1.0001 and -.0001<=pb[0]<=1.0001 and -.0001<=pf[0]<=1.0001 and max(pa[2],pb[2],pf[2])<=tol:matches.append({'edge_id':eid,'segment':[x,y]})
  row.update(source_line_handle=provenance.get('handle'),source_line_provenance=provenance,source_line_endpoints=[list(a),list(b)],system=system,source_projection=list(foot),edge_candidates=matches)
  row['status']='unique_source_line_and_graph_segment_candidate' if len(matches)==1 else 'no_matching_graph_segment' if not matches else 'ambiguous_graph_segments'
  rows.append(row)
 return {'status':'native_dn_bulk_screen_candidates_only','records':rows,'summary':dict(Counter(x['status'] for x in rows)),'nested_scope':nested_summary,'graph_mutated':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Only selected-layer modelspace TEXT/MTEXT, modelspace LINE and, when enabled, LINE descendants of graph-referenced modelspace inserts are scanned; other blocks, unsupported annotations and proxies are not covered.','A unique geometric match is a scoped local annotation candidate, not proof of an entire edge diameter, cross-view correspondence or engineering acceptance.','Text/line Z, insert transforms and hidden geometric context require independent source review.','Endpoint proximity is context only: no line, edge or DN ownership is selected and the label status remains unmatched.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();policy=json.loads(a.policy.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if policy.get('source_sha256')!=sha(a.source) or policy.get('graph_sha256')!=sha(a.graph):raise ValueError('source or graph hash mismatch')
 if a.output.exists():raise FileExistsError(a.output)
 doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));r=screen(doc,g,policy);r.update(source_sha256=proof['source_sha256'],graph_sha256=policy['graph_sha256'],policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),text_guard_sha256=sha(Path(__file__).with_name('native_dn_text_position.py')),source_preflight=proof)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'labels':len(r['records']),'summary':r['summary'],'status':r['status']},ensure_ascii=False))
if __name__=='__main__':main()
