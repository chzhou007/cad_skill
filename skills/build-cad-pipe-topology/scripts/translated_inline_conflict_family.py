"""Compare translated source joint conflicts; never infer a correction."""
import argparse,hashlib,json,math
from pathlib import Path
from native_line_path_evidence import LAYERS
from source_readability import read_source

def compare(doc,graph,triage,policy,hashes,tol=.05):
 if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or not 0<tol<=.05:raise ValueError('invalid tolerance')
 for k in ('source_sha256','graph_sha256','triage_sha256'):
  if policy.get(k)!=hashes.get(k):raise ValueError('hash mismatch: '+k)
 if triage.get('source_sha256')!=hashes['source_sha256'] or triage.get('graph_sha256')!=hashes['graph_sha256'] or triage.get('status')!='read_only_triage_not_repair' or triage.get('hil_ready') is not False:raise ValueError('stale or invalid triage')
 records={r['joint_handle']:r for r in triage['records']}
 if len(records)!=len(triage['records']):raise ValueError('duplicate conflict')
 edges={e['edge_id']:e for e in graph['edges']}
 if len(edges)!=len(graph['edges']):raise ValueError('duplicate graph edge')
 pairs=policy.get('pairs',[]);flat=[h for p in pairs for h in p]
 if not pairs or any(not isinstance(p,list) or len(p)!=2 for p in pairs) or len(flat)!=len(set(flat)):raise ValueError('invalid family pairs')
 offsets=[];out=[]
 for left,right in pairs:
  a,b=records.get(left),records.get(right);x,y=doc.entitydb.get(left),doc.entitydb.get(right)
  if not a or not b or not x or not y or x.dxftype()!='INSERT' or y.dxftype()!='INSERT' or x not in doc.modelspace() or y not in doc.modelspace():raise ValueError('source joint mismatch')
  if any(r.get('resolution')!='unresolved' or r.get('human_accepted') is not False or len(r.get('contacts',[]))!=2 for r in (a,b)):raise ValueError('conflict review state mismatch')
  for r in (a,b):
   assigned=edges.get(r['assigned_edge_id'])
   if not assigned or assigned.get('system')!=r.get('assigned_system') or any(eid not in edges for eid in r.get('witness_edge_ids',[])):raise ValueError('conflict graph edge mismatch')
  if x.dxf.name!=y.dxf.name or x.dxf.layer!=y.dxf.layer or any(x.dxf.get(k,v)!=y.dxf.get(k,v) for k,v in [('rotation',0),('xscale',1),('yscale',1),('zscale',1),('extrusion',(0,0,1))]):raise ValueError('joint transform mismatch')
  delta=[y.dxf.insert[i]-x.dxf.insert[i] for i in range(3)];lines=[]
  for ca,cb in zip(a['contacts'],b['contacts']):
   if len(ca.get('lines',[]))!=1 or len(cb.get('lines',[]))!=1:raise ValueError('contact ambiguity')
   la,lb=ca['lines'][0],cb['lines'][0];ea,eb=doc.entitydb.get(la['source_handle']),doc.entitydb.get(lb['source_handle'])
   if not ea or not eb or ea.dxftype()!='LINE' or eb.dxftype()!='LINE' or ea not in doc.modelspace() or eb not in doc.modelspace() or ea.dxf.layer!=eb.dxf.layer or ea.dxf.layer!=LAYERS.get(la['system']) or la['system']!=lb['system']:raise ValueError('source line or system mismatch')
   if math.dist([ca['midpoint'][i]+delta[i] for i in range(3)],cb['midpoint'])>tol:raise ValueError('contact translation mismatch')
   v=lambda p:[p[i]+delta[i] for i in range(3)]
   direct=max(math.dist(v(ea.dxf.start),tuple(eb.dxf.start)),math.dist(v(ea.dxf.end),tuple(eb.dxf.end)))
   reverse=max(math.dist(v(ea.dxf.start),tuple(eb.dxf.end)),math.dist(v(ea.dxf.end),tuple(eb.dxf.start)))
   if min(direct,reverse)>tol:raise ValueError('source line translation mismatch')
   lines.append({'left_handle':la['source_handle'],'right_handle':lb['source_handle'],'source_system':la['system'],'max_translation_error':min(direct,reverse)})
  if {x['source_system'] for x in lines}!={'supply','return'}:raise ValueError('expected mixed source systems')
  offsets.append(delta);out.append({'left_joint':left,'right_joint':right,'translation':delta,'source_lines':lines,'left_classification':a['classification'],'right_classification':b['classification'],'status':'same_source_geometry_not_a_resolution'})
 if any(math.dist(offsets[0],d)>tol for d in offsets[1:]):raise ValueError('pairs do not share one translation')
 return {'status':'translated_conflict_family_unresolved','records':out,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Translated source geometry and layers do not prove either layer is correct, a component assignment, or a physical connection.','Only selected modelspace LINE and INSERT entities are compared.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','triage','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));t=json.loads(a.triage.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'triage_sha256':sha(a.triage)};r=compare(doc,g,t,policy,hashes);r.update(hashes,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'pairs':len(r['records'])}))
if __name__=='__main__':main()
