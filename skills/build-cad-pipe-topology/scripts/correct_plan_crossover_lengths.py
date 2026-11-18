"""Separate source-drawn paths from confirmed drafted crossover spans."""
import argparse,copy,hashlib,json,math,shutil
from pathlib import Path
from source_readability import read_source
LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def close(a,b,tol=.05):return math.dist(a[:2],b[:2])<=tol
def apply(doc,graph,gaps,fragments,policy,source_hash,graph_hash,gaps_hash,fragments_hash):
 for key,value in [('source_sha256',source_hash),('graph_sha256',graph_hash),('gaps_sha256',gaps_hash),('fragments_sha256',fragments_hash)]:
  if policy.get(key)!=value:raise ValueError('stale '+key)
 if graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('graph source mismatch')
 selected=policy.get('gap_ids');byid={x['id']:x for x in gaps}
 if not isinstance(selected,list) or not selected or len(set(selected))!=len(selected) or len(byid)!=len(gaps) or not set(selected)<=byid.keys():raise ValueError('invalid gap selections')
 g=copy.deepcopy(graph);edges=g['edges'];rows=[];used_edges=set()
 for gid in selected:
  gap=byid[gid];handles=gap.get('source_handles',[])
  if len(handles)!=2 or len(set(handles))!=2 or gap.get('status')!='applied' or gap.get('crossing_connectivity')!='independent_pipes_no_junction':raise ValueError('unsupported gap evidence')
  fs=[x for x in fragments if x.get('normalization')=='source_straight_crossover_gap' and set(x.get('source_handles',[]))==set(handles) and (close(x['a'],gap['a']) and close(x['b'],gap['b']) or close(x['a'],gap['b']) and close(x['b'],gap['a']))]
  if len(fs)!=1 or fs[0].get('crossing_connectivity')!='independent_pipes_no_junction' or len(fs[0].get('crossings',[]))!=1:raise ValueError('source crossover fragment ambiguous')
  frag=fs[0];system=frag['system'];cross=frag['crossings'][0]
  if system not in LAYERS or cross.get('crossed_source_system') not in LAYERS or cross['crossed_source_system']==system:raise ValueError('not an independent supply/return crossing')
  lines=[doc.entitydb.get(h) for h in handles];crossline=doc.entitydb.get(cross.get('crossed_handle'))
  if any(not e or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=LAYERS[system] for e in lines) or not crossline or crossline.dxftype()!='LINE' or crossline not in doc.modelspace() or crossline.dxf.layer!=LAYERS[cross['crossed_source_system']]:raise ValueError('source line identity or system mismatch')
  endpoint_matches=[[i for i,e in enumerate(lines) if any(close(p,(v.x,v.y)) for v in (e.dxf.start,e.dxf.end))] for p in (gap['a'],gap['b'])]
  if any(len(x)!=1 for x in endpoint_matches) or endpoint_matches[0]==endpoint_matches[1]:raise ValueError('source gap endpoints not uniquely witnessed')
  q=cross['crossing'];ga,gb=gap['a'],gap['b'];v=crossline.dxf.start;w=crossline.dxf.end
  dx,dy=gb[0]-ga[0],gb[1]-ga[1];span=math.hypot(dx,dy)
  if span<=.05:raise ValueError('degenerate crossover gap')
  for side,index in enumerate((endpoint_matches[0][0],endpoint_matches[1][0])):
   line=lines[index];p=(line.dxf.start.x,line.dxf.start.y);qline=(line.dxf.end.x,line.dxf.end.y);anchor=(ga,gb)[side]
   other=qline if close(p,anchor) else p
   lx,ly=other[0]-anchor[0],other[1]-anchor[1];length=math.hypot(lx,ly)
   if length<=.05 or abs(dx*ly-dy*lx)>1e-6*span*length or ((dx*lx+dy*ly)>=0 if side==0 else (dx*lx+dy*ly)<=0):raise ValueError('gap source tails must be opposed and collinear')
  def interior(point,a,b):
   dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
   if not den:return False
   t=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den
   return 0<t<1 and math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)<=.05
  if not interior(q,ga,gb) or not interior(q,(v.x,v.y),(w.x,w.y)):raise ValueError('source crossing not witnessed in both interiors')
  for node in g.get('nodes',[]):
   if not all(k in node for k in ('node_id','x','y')):raise ValueError('node geometry required to protect system isolation')
   if close((node['x'],node['y']),q):
    incident={e.get('system') for e in edges if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))}
    if system in incident and cross['crossed_source_system'] in incident:raise ValueError('opposite systems share crossing node')
  hit=[e for e in edges if e.get('system')==system and set(handles)<=set(e.get('source_handles',[]))]
  if len(hit)!=1 or hit[0]['edge_id'] in used_edges:raise ValueError('gap to final edge ambiguous or repeated')
  e=hit[0];used_edges.add(e['edge_id']);paths=e.get('attribute_paths',[]);before=sum(math.dist(a,b) for p in paths for a,b in zip(p,p[1:]));old=e.get('path_length')
  if not isinstance(old,(float,int)) or isinstance(old,bool) or not math.isfinite(old):raise ValueError('unsupported existing length')
  def gap_segment(a,b):return close(a,gap['a']) and close(b,gap['b']) or close(a,gap['b']) and close(b,gap['a'])
  matches=sum(gap_segment(a,b) for p in paths for a,b in zip(p,p[1:]));gaplen=math.dist(gap['a'],gap['b'])
  if matches==0:
   evidence=e.get('source_straight_crossover_evidence')
   evidence=([evidence] if evidence else [])+e.get('source_normalized_crossovers',[])
   matching=[x for x in evidence if set(x.get('source_handles',[]))==set(handles) and x.get('crossing_connectivity')=='independent_pipes_no_junction' and (not x.get('source_gap_id') or x['source_gap_id']==gid)]
   endpoints=[p for path in paths if path for p in (path[0],path[-1])]
   if len(matching)!=1 or not all(sum(close(p,q) for p in endpoints)==1 for q in (gap['a'],gap['b'])) or e.get('path_length_complete') is not False:raise ValueError('gap missing without matching prior exclusion evidence and path endpoints')
   rows.append({'gap_id':gid,'edge_id':e['edge_id'],'status':'already_excluded','gap_drawing_units':gaplen});continue
  if matches!=1 or any(k in e for k in ('diameter_inference','pipe_diameter','source_dimensioned_segments')):raise ValueError('ambiguous gap or dependent edge attributes need revalidation')
  new=[]
  for path in paths:
   if len(path)<2:raise ValueError('invalid attribute path')
   part=[path[0]]
   for a,b in zip(path,path[1:]):
    if gap_segment(a,b):
     if len(part)>=2:new.append(part)
     part=[b]
    else:part.append(b)
   if len(part)>=2:new.append(part)
  endpoints=[p for path in new for p in (path[0],path[-1])]
  if not all(sum(close(p,q) for p in endpoints)==1 for q in (gap['a'],gap['b'])):raise ValueError('gap endpoints not uniquely represented after path split')
  after=sum(math.dist(a,b) for p in new for a,b in zip(p,p[1:]));
  if abs(before-after-gaplen)>.001 or after<=0:raise ValueError('path separation length mismatch')
  if abs(old-before)<=.001:new_length=after
  elif abs(old-after)<=.001 and e.get('path_length_complete') is False:new_length=old
  else:raise ValueError('existing path length has unsupported scope')
  prior_scope=e.get('path_length_scope')
  if 'source_path_coverage' in e:
   coverage=e.pop('source_path_coverage')
   if e.get('previous_source_path_coverage') is not None:raise ValueError('existing coverage history requires explicit reconciliation')
   e['previous_source_path_coverage']={'evidence':coverage,'input_graph_sha256':graph_hash,'status':'historical_segment_indices_invalid_after_path_split'}
  e['attribute_paths']=new;e['drawing_path_length_before_crossover_exclusion']=old;e['path_length']=new_length;e['path_length_complete']=False;e['path_length_scope']='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown';e['physical_length']='unknown'
  entry={'source_gap_id':gid,'source_handles':handles,'source_sha256':source_hash,'source_gap_coverage_sha256':gaps_hash,'source_fragments_sha256':fragments_hash,'a':gap['a'],'b':gap['b'],'crossings':[cross],'crossing_connectivity':'independent_pipes_no_junction','physical_length':'unknown','relative_elevation':'unknown','prior_length_scope':prior_scope}
  e.setdefault('source_normalized_crossovers',[]).append(entry)
  rows.append({'gap_id':gid,'edge_id':e['edge_id'],'status':'gap_excluded_from_attribute_paths','gap_drawing_units':gaplen,'previous_path_length':old,'corrected_drawing_length':new_length})
 g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_crossover_length_change')
 if 'preHilComparison' in g:g['preHilComparison']={'status':'pending','previous_comparison':g['preHilComparison'],'families':[{'id':'crossover_length_source_recheck','status':'pending'}]}
 return g,{'status':'crossover_drawing_length_corrected_not_physical_length','source_sha256':source_hash,'input_graph_sha256':graph_hash,'gap_evidence_sha256':gaps_hash,'fragments_sha256':fragments_hash,'records':rows,'human_accepted':False,'hil_ready':False,'limitations':['Drawing paths exclude identified crossing gaps but remaining drawing geometry is not certified installed length.','Only explicitly selected source gaps are handled; topology and components are preserved.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','gaps','fragments','policy','devices','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);load=lambda p:json.loads(p.read_text(encoding='utf8'));g,r=apply(doc,load(a.graph),load(a.gaps),load(a.fragments),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.gaps),sha(a.fragments));a.output.mkdir(parents=True,exist_ok=False);out=a.output/'graph_with_crossover_length_status.json';out.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv');r.update(output_graph_sha256=sha(out),policy_sha256=sha(a.policy),devices_sha256=sha(a.devices),source_preflight=proof['status']);(a.output/'audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'corrected':sum(x['status']=='gap_excluded_from_attribute_paths' for x in r['records']),'already_excluded':sum(x['status']=='already_excluded' for x in r['records']),'graph_sha256':r['output_graph_sha256']}))
if __name__=='__main__':main()
