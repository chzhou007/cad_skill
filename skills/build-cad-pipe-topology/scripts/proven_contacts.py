"""Canonical points for explicitly proven endpoint incidence; no spatial clustering."""
def canonical_contact_points(segments,contact_pairs):
  cp={};coords={}
  def root(x):
   cp.setdefault(x,x)
   if cp[x]!=x:cp[x]=root(cp[x])
   return cp[x]
  for a,b,p in contact_pairs:
   ra,rb=root(a),root(b)
   if ra!=rb:cp[rb]=ra
   coords.setdefault(ra,p)
  def contact_point(s,v):
   token=(s['id'],v);r=root(token)
   return coords.get(r,(s['a'][0]+v*(s['b'][0]-s['a'][0]),s['a'][1]+v*(s['b'][1]-s['a'][1])))
  return contact_point


def validate_junction_contacts(nodes,edges,contacts,tolerance):
 import math
 result=[]
 for c in contacts:
  p=c['semantic_endpoint'];matches=[n for n in nodes if n['node_type']=='tee'and math.dist((n['x'],n['y']),p)<=tolerance]
  valid=len(matches)==1 and sum(matches[0]['node_id']in(e['start_node_id'],e['end_node_id'])for e in edges)==3
  result.append(dict(source=c,node_id=matches[0]['node_id']if len(matches)==1 else None,valid=valid))
 if not all(r['valid']for r in result):raise ValueError('Source-proven junction missing from final graph')
 return result
