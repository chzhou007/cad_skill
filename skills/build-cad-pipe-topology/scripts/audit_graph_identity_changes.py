"""Compare source-bound graphs without rewriting IDs or transferring reviews."""
import argparse,collections,hashlib,json,math
from pathlib import Path

def audit(old,new,policy,hashes):
 for k in ('source_sha256','old_graph_sha256','new_graph_sha256'):
  if policy.get(k)!=hashes.get(k):raise ValueError('stale '+k)
 if any(g.get('metadata',{}).get('source_sha256')!=hashes['source_sha256'] for g in (old,new)):raise ValueError('source graph mismatch')
 def position(p):
  if not isinstance(p,(list,tuple)) or len(p)<2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p[:2]):raise ValueError('invalid coordinate')
  return tuple(round(v,4) for v in p[:2])
 def node_key(n):return (n.get('node_type'),n.get('subtype'),n.get('system'),n.get('floor'),position([n['x'],n['y']]))
 def edge_key(e):
  handles=e.get('source_handles');path=e.get('path',e.get('path_points'))
  if not isinstance(handles,list) or not handles or not all(isinstance(x,str) and x for x in handles) or not isinstance(path,list) or len(path)<2:return None
  p=tuple(position(x) for x in path);return (e.get('system'),e.get('start_floor'),e.get('end_floor'),tuple(sorted(handles)),min(p,p[::-1]))
 def index(items,idkey,keyfun):
  ids=[x.get(idkey) for x in items]
  if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):raise ValueError('invalid or duplicate IDs')
  bykey=collections.defaultdict(list);byid={}
  for x in items:
   k=keyfun(x);byid[x[idkey]]=k
   if k is not None:bykey[k].append(x[idkey])
  return bykey,byid
 def compare(a,b,idkey,keyfun):
  ak,ai=index(a,idkey,keyfun);bk,bi=index(b,idkey,keyfun);matched=[]
  for k,oldids in ak.items():
   newids=bk.get(k,[])
   if len(oldids)==len(newids)==1:matched.append({'old_id':oldids[0],'new_id':newids[0],'same_id':oldids[0]==newids[0],'status':'unique_signature_candidate_not_review_transfer'})
  matched.sort(key=lambda x:x['old_id']);om={x['old_id'] for x in matched};nm={x['new_id'] for x in matched}
  reused=sorted(id for id in ai.keys()&bi.keys() if ai[id] is None or bi[id] is None or ai[id]!=bi[id])
  return {'candidates':matched,'old_unmatched_ids':sorted(set(ai)-om),'new_unmatched_ids':sorted(set(bi)-nm),'same_id_different_or_unknown_signature':reused,'ambiguous_signature_count':sum(len(v)>1 or len(bk.get(k,[]))>1 for k,v in ak.items())}
 nodes=compare(old['nodes'],new['nodes'],'node_id',node_key);edges=compare(old['edges'],new['edges'],'edge_id',edge_key)
 return {'status':'identity_candidates_only_no_review_transfer','source_sha256':hashes['source_sha256'],'old_graph_sha256':hashes['old_graph_sha256'],'new_graph_sha256':hashes['new_graph_sha256'],'nodes':nodes,'edges':edges,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Unique rounded geometry, source handles and system do not prove full semantic equivalence or component ownership.','Splits, merges, parallel identical paths, omitted source handles and slightly different path tessellations remain unmatched or ambiguous.','Never transfer historical reviews automatically; evaluate each affected object against current source and semantics.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','old-graph','new-graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));hashes={'source_sha256':sha(a.source),'old_graph_sha256':sha(a.old_graph),'new_graph_sha256':sha(a.new_graph)};r=audit(load(a.old_graph),load(a.new_graph),load(a.policy),hashes);r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'node_candidates':len(r['nodes']['candidates']),'edge_candidates':len(r['edges']['candidates']),'reused_edge_ids':len(r['edges']['same_id_different_or_unknown_signature'])}))
if __name__=='__main__':main()
