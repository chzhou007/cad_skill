"""Source-scoped center/rim connection; preserve its unmeasured graphic span."""
import math

def apply_source_riser_connections(circles,segments,policy,tol=.05):
 if not policy:return []
 if not policy.get('expert_issue'):raise ValueError('missing expert issue')
 seen=set();out=[]
 for item in policy.get('connections',[]):
  ch=item['circle_handle']
  if ch in seen:raise ValueError('duplicate expert riser circle')
  seen.add(ch);cs=[c for c in circles if c['handle']==ch];center_lines=[s for s in segments if s['handle']==item['center_line']];rim_lines=[s for s in segments if s['handle']==item['rim_line']]
  if len(cs)!=1 or len(center_lines)!=1 or len(rim_lines)!=1:raise ValueError('missing or ambiguous source riser geometry')
  c=cs[0];a=center_lines[0];b=rim_lines[0];center=c['center'];radius=float(item['radius']);system=item['system']
  if abs(c['radius']-radius)>tol or c['system']!=system or a['system']!=system or b['system']!=system:raise ValueError('riser system or radius mismatch')
  def endpoints(s,what):
   return [(side,s[side]) for side in ('a','b') if abs(math.dist(s[side],center)-what)<=tol]
  ca=endpoints(a,0);rb=endpoints(b,radius)
  if len(ca)!=1 or len(rb)!=1:raise ValueError('riser source endpoint mismatch')
  occupied=[]
  for s in segments:
   if s['system']!=system:continue
   for side in ('a','b'):
    if math.dist(s[side],center)<=tol or math.dist(s[side],rb[0][1])<=tol:occupied.append((s['handle'],side))
  if set(occupied)!={(a['handle'],ca[0][0]),(b['handle'],rb[0][0])}:raise ValueError('competing riser contact')
  for s in segments:
   if s is a or s is b or s['system']!=system:continue
   p,q=s['a'],s['b'];dx=q[0]-p[0];dy=q[1]-p[1];length2=dx*dx+dy*dy
   if not length2:continue
   for probe in (center,rb[0][1]):
    t=((probe[0]-p[0])*dx+(probe[1]-p[1])*dy)/length2
    if -tol/math.sqrt(length2)<=t<=1+tol/math.sqrt(length2) and math.dist(probe,(p[0]+t*dx,p[1]+t*dy))<=tol:raise ValueError('competing riser interior contact')
  au=a['b' if ca[0][0]=='a' else 'a'];bu=b['b' if rb[0][0]=='a' else 'a'];u=(au[0]-center[0],au[1]-center[1]);v=(bu[0]-center[0],bu[1]-center[1])
  if abs(u[0]*v[1]-u[1]*v[0])/(math.hypot(*u)*math.hypot(*v))<.17:raise ValueError('riser pipes not transverse')
  rim=rb[0][1];b['original_'+rb[0][0]]=rim;b[rb[0][0]]=center
  out.append({'expert_issue':policy['expert_issue'],'circle_handle':ch,'center_line':a['handle'],'rim_line':b['handle'],'center':center,'rim':rim,'system':system,'graphic_radius':radius})
 return out

def separate_riser_source_path(edges,evidence,tol=.05):
 audit=[]
 for x in evidence:
  hits=[e for e in edges if e['system']==x['system'] and {x['center_line'],x['rim_line']}.issubset(e['source_handles'])]
  if len(hits)!=1:raise ValueError('riser connection does not map to one edge')
  e=hits[0]
  if len(e['attribute_paths'])!=1:raise ValueError('riser edge source paths already discontinuous')
  path=e['attribute_paths'][0];parts=[[list(path[0])]];removed=0
  for a,b in zip(path,path[1:]):
   rim=x['rim'];a_center=math.dist(a,x['center'])<=tol;b_center=math.dist(b,x['center'])<=tol
   contains_rim=abs(math.dist(a,b)-math.dist(a,rim)-math.dist(rim,b))<=tol
   if a_center and contains_rim:removed+=1;parts.append([list(rim),list(b)])
   elif b_center and contains_rim:removed+=1;parts[-1].append(list(rim));parts.append([list(b)])
   else:parts[-1].append(list(b))
  if removed!=1 or any(len(p)<2 for p in parts):raise ValueError('riser graphic span missing or ambiguous')
  e['attribute_paths']=parts;e['path_length']-=x['graphic_radius'];e['path_length_complete']=False;e['path_length_scope']='source_drawn_pipe_only_riser_length_unknown';e.setdefault('source_expert_riser_connections',[]).append({**x,'physical_length':'unknown','physical_elevation':'unknown'});audit.append({'edge_id':e['edge_id'],**x,'graphic_radius_excluded':x['graphic_radius']})
 return audit
