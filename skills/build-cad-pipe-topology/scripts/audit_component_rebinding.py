"""Audit source component identity across candidate graph versions without remapping."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def audit(old_graph,new_graph,old_rows,new_rows,identity,policy,hashes):
 for key in ('source_sha256','old_graph_sha256','new_graph_sha256','identity_sha256','old_components_sha256','new_components_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('stale '+key)
 if any(g.get('metadata',{}).get('source_sha256')!=hashes['source_sha256'] for g in (old_graph,new_graph)):raise ValueError('source graph mismatch')
 if identity.get('old_graph_sha256')!=hashes['old_graph_sha256'] or identity.get('new_graph_sha256')!=hashes['new_graph_sha256'] or identity.get('source_sha256')!=hashes['source_sha256'] or identity.get('status')!='identity_candidates_only_no_review_transfer' or identity.get('graph_mutated') is not False or identity.get('human_accepted') is not False:raise ValueError('stale identity audit')
 def by_name(rows):
  d={r.get('device_name'):r for r in rows}
  if len(d)!=len(rows) or any(not isinstance(k,str) or not k for k in d):raise ValueError('duplicate or missing component identity')
  return d
 a,b=by_name(old_rows),by_name(new_rows)
 if set(a)!=set(b):raise ValueError('component identity set changed')
 old_edges={e['edge_id']:e for e in old_graph['edges']};new_edges={e['edge_id']:e for e in new_graph['edges']}
 limit=policy.get('maximum_anchor_distance')
 if isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit) or not 0<limit<=5:raise ValueError('invalid anchor distance')
 mappings=identity['edges']['candidates'];m={v['old_id']:v['new_id'] for v in mappings}
 if len(m)!=len(mappings) or len(set(m.values()))!=len(m):raise ValueError('ambiguous edge candidates')
 reused=set(identity['edges']['same_id_different_or_unknown_signature']);rows=[]
 for name in sorted(a):
  x,y=a[name],b[name]
  if any(not x.get(k) or x.get(k)!=y.get(k) for k in ('source_handle','equipment_type')):raise ValueError('component source identity changed')
  oe,ne=x.get('edge_id'),y.get('edge_id')
  if oe not in old_edges or ne not in new_edges:raise ValueError('component edge missing')
  try:before=(float(x['x']),float(x['y']));after=(float(y['x']),float(y['y']))
  except (ValueError,TypeError,KeyError):raise ValueError('invalid component anchor')
  if not all(math.isfinite(v) for v in before+after) or math.dist(before,after)>.05:raise ValueError('component anchor changed')
  oldedge,newedge=old_edges[oe],new_edges[ne];path=newedge.get('path',newedge.get('path_points',[]));distances=[]
  for a0,b0 in zip(path,path[1:]):
   dx,dy=b0[0]-a0[0],b0[1]-a0[1];den=dx*dx+dy*dy
   if not den:continue
   t=max(0,min(1,((after[0]-a0[0])*dx+(after[1]-a0[1])*dy)/den));distances.append(math.hypot(after[0]-a0[0]-t*dx,after[1]-a0[1]-t*dy))
  distance=min(distances) if distances else None;overlap=sorted(set(oldedge.get('source_handles',[]))&set(newedge.get('source_handles',[])))
  local=bool(overlap and oldedge.get('system')==newedge.get('system') and distance is not None and distance<=limit)
  same=m.get(oe)==ne
  rows.append({'device_name':name,'source_handle':x['source_handle'],'equipment_type':x['equipment_type'],'old_edge_id':oe,'new_edge_id':ne,'status':'unique_same_source_path_candidate' if same else 'split_or_unmatched_edge_requires_review','old_edge_id_reused_for_other_path':oe in reused,'same_numeric_edge_id':oe==ne,'component_anchor':list(after),'new_edge_anchor_distance':distance,'shared_source_handles':overlap,'same_system_source_geometry_candidate':local,'physical_ownership_verified':False})
 return {'status':'component_rebinding_candidates_not_ownership_acceptance','source_sha256':hashes['source_sha256'],'old_graph_sha256':hashes['old_graph_sha256'],'new_graph_sha256':hashes['new_graph_sha256'],'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Unique geometry candidates do not independently prove physical component ownership.','This only compares supplied assigned components; unassigned and later-added instances require separate audits.','Historical component annotations must not be transferred automatically.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','old-graph','new-graph','old-components','new-components','identity','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'))
 def rows(p):
  with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 hashes={'source_sha256':sha(a.source),'old_graph_sha256':sha(a.old_graph),'new_graph_sha256':sha(a.new_graph),'identity_sha256':sha(a.identity),'old_components_sha256':sha(a.old_components),'new_components_sha256':sha(a.new_components)};r=audit(load(a.old_graph),load(a.new_graph),rows(a.old_components),rows(a.new_components),load(a.identity),load(a.policy),hashes);r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'components':len(r['records']),'unmatched':sum(x['status']!='unique_same_source_path_candidate' for x in r['records'])}))
if __name__=='__main__':main()
