import math

def dist(a,b):return math.dist(a,b)
def on(p,a,b,tol=.05):
 dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy
 if not ll:return None
 t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll;q=(a[0]+t*dx,a[1]+t*dy)
 return max(0,min(1,t)) if -tol/math.sqrt(ll)<=t<=1+tol/math.sqrt(ll) and dist(p,q)<=tol else None

def circle_connection_candidate(c,segments,tol=.05):
 if c['radius']<=80+tol:return None
 return radial_circle_connection_candidate(c,segments,tol)

def radial_circle_connection_candidate(c,segments,tol=.05):
 """Geometry only; callers must establish the native circle symbol meaning."""
 center=c['center'];mains=[u for u in segments if u['system']==c['system'] and on(center,u['a'],u['b'],tol) is not None and min(dist(center,u['a']),dist(center,u['b']))>c['radius']]
 if len(mains)!=1:return None
 branches=[]
 for u in segments:
  if u['system']!=c['system'] or u is mains[0]:continue
  for side,other in [('a','b'),('b','a')]:
   end=u[side]
   if abs(dist(center,end)-c['radius'])<=tol and on(end,u[other],center,tol) is not None:branches.append((u,side,end))
 if len(branches)!=1:return None
 main=mains[0];branch=branches[0][0];u=(main['b'][0]-main['a'][0],main['b'][1]-main['a'][1]);v=(branch['b'][0]-branch['a'][0],branch['b'][1]-branch['a'][1])
 if abs(u[0]*v[1]-u[1]*v[0])/(math.hypot(*u)*math.hypot(*v))<.17:return None
 return main,branches[0]

def expert_circle_connection_candidate(c,segments,policy,tol=.05):
 """Recognize only explicitly scoped source circles with a unique geometric main."""
 item=next((x for x in policy.get('circles',[]) if x.get('circle_handle')==c.get('handle')),None)
 if item is None:return None
 if not policy.get('expert_issue') or not item.get('main_handle') or not item.get('branch_handle'):raise ValueError('expert circle policy lacks evidence')
 if abs(c['radius']-float(item['radius']))>tol or c['system']!=item['system']:raise ValueError('expert circle does not match profile')
 center=c['center'];mains=[u for u in segments if u['system']==c['system'] and on(center,u['a'],u['b'],tol) is not None and min(dist(center,u['a']),dist(center,u['b']))>c['radius']]
 ref=next((u for u in mains if u['handle']==item['main_handle']),None)
 if ref is None:raise ValueError('expert circle source main absent')
 def same(a,b):return (dist(a['a'],b['a'])<=tol and dist(a['b'],b['b'])<=tol) or (dist(a['a'],b['b'])<=tol and dist(a['b'],b['a'])<=tol)
 if any(not same(ref,u) for u in mains):raise ValueError('ambiguous circle mains')
 branches=[]
 for u in segments:
  if u['system']!=c['system'] or any(u is m for m in mains):continue
  for side,other in [('a','b'),('b','a')]:
   end=u[side]
   if abs(dist(center,end)-c['radius'])<=tol and on(end,u[other],center,tol) is not None:branches.append((u,side,end))
 if len(branches)!=1 or branches[0][0]['handle']!=item['branch_handle']:raise ValueError('ambiguous circle branch')
 branch=branches[0][0];u=(ref['b'][0]-ref['a'][0],ref['b'][1]-ref['a'][1]);v=(branch['b'][0]-branch['a'][0],branch['b'][1]-branch['a'][1])
 if abs(u[0]*v[1]-u[1]*v[0])/(math.hypot(*u)*math.hypot(*v))<.17:raise ValueError('circle branch is not transverse')
 return ref,branches[0]

def match_out_of_plane_symbol(c,glyphs,tol=.05):
 if abs(c['radius']-80)>tol:return None
 center=c['center'];arms=[u for u in glyphs if min(dist(center,u['a']),dist(center,u['b']))<=tol and 115<=dist(u['a'],u['b'])<=135]
 if len(arms)!=2:return None
 # Nearby opposite-facing symbols may place their bars in the same radius.
 # Anchor the selection to this symbol's own two outward native arm rays.
 axis=[sum((u['b'][i] if dist(center,u['a'])<=tol else u['a'][i])-center[i] for u in arms) for i in (0,1)]
 axis_length=math.hypot(*axis)
 if axis_length<=tol:return None
 threshold=sum(dist(u['a'],u['b']) for u in arms)/4
 bars=[u for u in glyphs if max(dist(center,u['a']),dist(center,u['b']))<=230 and min(dist(center,u['a']),dist(center,u['b']))>tol and 130<=dist(u['a'],u['b'])<=145 and sum((((u['a'][i]+u['b'][i])/2)-center[i])*axis[i] for i in (0,1))/axis_length>=threshold]
 if len(bars)!=2:return None
 vv=[(u['b'][0]-u['a'][0],u['b'][1]-u['a'][1]) for u in bars]
 if abs(vv[0][0]*vv[1][1]-vv[0][1]*vv[1][0])/(math.hypot(*vv[0])*math.hypot(*vv[1]))>.001:return None
 return arms,bars

def riser_terminal_candidate(c,segments,radii,tol=.05):
 if not any(abs(c['radius']-r)<=tol for r in radii):return None
 center=c['center'];matches=[]
 if any(s['system']==c['system']and on(center,s['a'],s['b'],tol)is not None for s in segments):return None
 for s in segments:
  if s['system']!=c['system']:continue
  for end,other in [('a','b'),('b','a')]:
   p=s[end]
   if abs(dist(p,center)-c['radius'])<=tol and on(p,center,s[other],tol)is not None:matches.append((s,end,p))
 return matches[0]if len(matches)==1 else None
