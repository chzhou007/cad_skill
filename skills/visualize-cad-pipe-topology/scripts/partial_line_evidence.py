"""Validate partial LINE overlap evidence against actual native source geometry."""
import math

LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def validate(doc,edge,source_hash,tol=.05):
 ev=edge.get('source_partial_line_evidence')
 if ev is None:return
 if (not isinstance(ev,dict) or ev.get('source_sha256')!=source_hash or ev.get('status')!='partial_source_overlap_candidate_not_physical_length' or ev.get('physical_length')!='unknown' or ev.get('connection_confirmed') is not False or ev.get('human_accepted') is not False or edge.get('physical_length')!='unknown' or edge.get('path_length_complete') is not False or not all(isinstance(ev.get(k),str) and ev[k] for k in ('input_graph_sha256','coverage_sha256','screen_sha256'))):raise ValueError('invalid partial line identity')
 paths=edge.get('attribute_paths');records=ev.get('records');system=edge.get('system')
 if system not in LAYERS or not isinstance(paths,list) or len(paths)!=1 or not isinstance(records,list) or not records:raise ValueError('invalid partial line scope')
 lines=[x for x in doc.modelspace().query('LINE') if x.dxf.layer==LAYERS[system]];seen=set()
 for rec in records:
  i=rec.get('segment_index');path=paths[0]
  if isinstance(i,bool) or not isinstance(i,int) or i<0 or i>=len(path)-1 or i in seen or rec.get('edge_id')!=edge.get('edge_id') or rec.get('system')!=system or rec.get('physical_length')!='unknown':raise ValueError('invalid partial line segment')
  seen.add(i);a,b=path[i:i+2];length=math.dist(a,b)
  if rec.get('start')!=a or rec.get('end')!=b or length<=tol or abs(rec.get('drawing_length',-1)-length)>.001:raise ValueError('partial line geometry mismatch')
  ux=(b[0]-a[0])/length;uy=(b[1]-a[1])/length;hits=[]
  for line in lines:
   p=line.dxf.start;q=line.dxf.end
   if math.hypot(p.x-q.x,p.y-q.y)<=tol:continue
   if max(abs((x.x-a[0])*uy-(x.y-a[1])*ux) for x in (p,q))>tol:continue
   positions=sorted((x.x-a[0])*ux+(x.y-a[1])*uy for x in (p,q));lo=max(0.,positions[0]);hi=min(length,positions[1])
   if hi-lo>tol:hits.append((lo,hi,line.dxf.handle))
  cuts=sorted({0.,length,*[v for lo,hi,_ in hits for v in (lo,hi)]});actual=[]
  for lo,hi in zip(cuts,cuts[1:]):
   if hi-lo<=1e-9:continue
   mid=(lo+hi)/2;handles=sorted(h for start,end,h in hits if start<=mid<=end);status='unwitnessed' if not handles else 'unique_source_line' if len(handles)==1 else 'ambiguous_overlapping_lines';actual.append((lo,hi,status,handles))
  pieces=rec.get('pieces')
  if not isinstance(pieces,list) or len(pieces)!=len(actual):raise ValueError('partial line pieces mismatch')
  totals={'unique_source_line':0.,'unwitnessed':0.,'ambiguous_overlapping_lines':0.}
  for piece,(lo,hi,status,handles) in zip(pieces,actual):
   if piece.get('status')!=status or piece.get('source_handles')!=handles or any(abs(piece.get(k,-1)-v)>.001 for k,v in [('start_distance',lo),('end_distance',hi),('drawing_length',hi-lo)]):raise ValueError('partial line source witness mismatch')
   totals[status]+=hi-lo
  for k,status in [('unique_source_drawing_length','unique_source_line'),('unwitnessed_drawing_length','unwitnessed'),('ambiguous_drawing_length','ambiguous_overlapping_lines')]:
   if abs(rec.get(k,-1)-totals[status])>.001:raise ValueError('partial line totals mismatch')
