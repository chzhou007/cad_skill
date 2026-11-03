import math

def dist(a,b):return math.dist(a,b)
def on(p,a,b,tol=.05):
 dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy
 if not ll:return None
 t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll;q=(a[0]+t*dx,a[1]+t*dy)
 return max(0,min(1,t)) if -tol/math.sqrt(ll)<=t<=1+tol/math.sqrt(ll) and dist(p,q)<=tol else None

def circle_connection_candidate(c,segments,tol=.05):
 if c['radius']<=80+tol:return None
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

def _arm_bisector(center,arms):
 tips=[]
 for u in arms:
  tip=u['b'] if dist(center,u['a'])<=dist(center,u['b']) else u['a']
  vx,vy=tip[0]-center[0],tip[1]-center[1];ln=math.hypot(vx,vy)
  if ln<=1e-9:return None
  tips.append((vx/ln,vy/ln))
 bx,by=tips[0][0]+tips[1][0],tips[0][1]+tips[1][1];bl=math.hypot(bx,by)
 if bl<.25:return None
 return (bx/bl,by/bl)

def match_out_of_plane_symbol(c,glyphs,tol=.05):
 """Circle plus its own V and two forward bars.

 A bar belongs to this symbol only when both ends lie in front of the two
 arms. Bars behind the V, including those of a neighboring symbol inside the
 old 230 radius, stay out. Extra forward bars stay unmatched; the nearest
 bar is not chosen and no other system is bound.
 """
 if abs(c['radius']-80)>tol:return None
 center=c['center'];arms=[u for u in glyphs if min(dist(center,u['a']),dist(center,u['b']))<=tol and 115<=dist(u['a'],u['b'])<=135]
 if len(arms)!=2:return None
 bisector=_arm_bisector(center,arms)
 if bisector is None:return None
 def ahead(pt):
  return (pt[0]-center[0])*bisector[0]+(pt[1]-center[1])*bisector[1]>0
 bars=[u for u in glyphs if max(dist(center,u['a']),dist(center,u['b']))<=230 and min(dist(center,u['a']),dist(center,u['b']))>tol and 130<=dist(u['a'],u['b'])<=145 and ahead(u['a']) and ahead(u['b'])]
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
