"""Inventory native plan pipe LINE handles against the final graph, without repair."""
import argparse,collections,hashlib,json,math
from pathlib import Path
from duplicate_native_main_diagnostics import same_line
from source_readability import read_source

def inventory(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('stale source or graph')
 layers=policy.get('system_layers');tol=policy.get('normalization_tolerance')
 if not isinstance(layers,dict) or not layers or any(not isinstance(k,str) or v not in ('supply','return') for k,v in layers.items()) or isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or tol<=0:raise ValueError('invalid scope')
 edges=graph['edges'];ids=[e['edge_id'] for e in edges]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate edge IDs')
 owners=collections.defaultdict(list)
 for e in edges:
  for h in set(e.get('source_handles',[])):owners[h].append(e['edge_id'])
 systems={e['edge_id']:e.get('system') for e in edges}
 lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in layers];rows=[]
 for e in lines:
  h=e.dxf.handle;length=math.dist(e.dxf.start,e.dxf.end)
  if not math.isfinite(length):raise ValueError('nonfinite source line')
  direct=sorted(owners[h]);coincident=[]
  if not direct and length>tol:
   for other in lines:
    if other.dxf.handle!=h and owners[other.dxf.handle] and same_line(e,other,tol):coincident.append({'source_handle':other.dxf.handle,'edge_ids':sorted(owners[other.dxf.handle])})
  status=('source_handle_system_conflict' if any(systems[i]!=layers[e.dxf.layer] for i in direct) else 'source_handle_referenced') if direct else 'shorter_than_normalization_tolerance_unclassified' if length<=tol else 'coincident_referenced_source_candidate' if coincident else 'unreferenced_source_line_unclassified'
  rows.append({'source_handle':h,'source_layer':e.dxf.layer,'system':layers[e.dxf.layer],'start':list(e.dxf.start),'end':list(e.dxf.end),'drawing_length':length,'status':status,'direct_edge_ids':direct,'coincident_referenced_sources':coincident,'physical_identity_resolved':False})
 counts=collections.Counter(x['status'] for x in rows)
 return {'status':'final_plan_line_handle_inventory_not_acceptance','source_sha256':source_hash,'graph_sha256':graph_hash,'normalization_tolerance':tol,'records':rows,'counts':dict(counts),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Modelspace LINEs on explicitly selected layers only; nested lines, polylines, auxiliary layers and proxies are excluded.','A referenced handle does not prove full source geometry coverage or correct connectivity.','Short lines and coincident source handles remain unclassified: neither omission nor duplicate physical identity is inferred.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));r=inventory(doc,load(a.graph),load(a.policy),proof['source_sha256'],h(a.graph));r.update(policy_sha256=h(a.policy),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'counts':r['counts']}))
if __name__=='__main__':main()
