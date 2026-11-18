"""Inventory dimension-to-graph segment geometry without assigning lengths."""
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
from source_readability import read_source

def screen(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or graph hash mismatch')
 if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or not 0<tol<=.05:raise ValueError('invalid tolerance')
 edges=graph['edges']
 if len({e['edge_id'] for e in edges})!=len(edges):raise ValueError('duplicate graph edge')
 segments=[]
 for e in edges:
  for pi,path in enumerate(e.get('attribute_paths',[])):
   for si,(a,b) in enumerate(zip(path,path[1:])):
    if len(a)!=2 or len(b)!=2 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in a+b):raise ValueError('invalid graph segment')
    if math.dist(a,b)>tol:segments.append((e['edge_id'],e.get('system'),pi,si,a,b))
 rows=[]
 for dim in doc.modelspace().query('DIMENSION'):
  row={'dimension_handle':dim.dxf.handle,'layer':dim.dxf.layer,'dimtype':dim.dxf.dimtype,'source_text_override':dim.dxf.get('text',''),'matches':[],'human_accepted':False}
  p=dim.dxf.get('defpoint2');q=dim.dxf.get('defpoint3')
  if dim.dxf.dimtype&7!=0 or tuple(dim.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or p is None or q is None:
   row['status']='unsupported_dimension_geometry';rows.append(row);continue
  a=(p.x,p.y);b=(q.x,q.y)
  if not all(math.isfinite(v) for v in (*a,*b,p.z,q.z)):row['status']='unsupported_dimension_geometry';rows.append(row);continue
  matches=[]
  for eid,system,pi,si,u,v in segments:
   if (math.dist(a,u)<=tol and math.dist(b,v)<=tol) or (math.dist(a,v)<=tol and math.dist(b,u)<=tol):matches.append({'edge_id':eid,'system':system,'path_index':pi,'segment_index':si,'segment_points':[u,v]})
  try:measurement=dim.get_measurement()
  except (ValueError,TypeError,AttributeError):measurement=None
  if not isinstance(measurement,(int,float)) or not math.isfinite(measurement):measurement=None
  row.update(definition_points=[list(p),list(q)],projected_measurement=measurement,matches=matches)
  row['status']='unique_exact_segment_geometry_candidate' if len(matches)==1 else 'ambiguous_exact_segment_geometry' if matches else 'no_exact_segment_geometry'
  rows.append(row)
 return {'status':'dimension_segment_geometry_screen_only','source_sha256':source_hash,'graph_sha256':graph_hash,'source_units_code':doc.header.get('$INSUNITS'),'records':rows,'summary':dict(Counter(r['status'] for r in rows)),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Only modelspace DIMENSION entities and linear default-OCS definition points are screened; nested, exploded, proxy and other dimension types are not covered.','Matching definition points do not validate dimension styling, units, source pipe identity, physical length or engineering acceptance.','A dimension between separate lines or reference objects is not a pipe length merely because its projected value is numeric.']}

def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','policy','output'):p.add_argument('--'+key,required=True,type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);r=screen(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'summary':r['summary']}))
if __name__=='__main__':main()
