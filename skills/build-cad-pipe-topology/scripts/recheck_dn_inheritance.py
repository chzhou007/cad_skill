"""Read-only source-bound reevaluation of previously recorded DN candidates."""
import argparse,copy,hashlib,json
from pathlib import Path
from source_readability import read_source
from infer_local_dn_candidates import collect_evidence,calculate
from source_direct_dn_evidence import collect as collect_direct

def compare(old,fresh):
 differences=[]
 for eid in sorted(set(old)|set(fresh)):
  a,b=old.get(eid),fresh.get(eid)
  if not a or not b or any(a.get(k)!=b.get(k) for k in ('nominal_mm_candidate','candidate_type','lineage','status')):differences.append({'edge_id':eid,'before':a,'after':b})
 return differences

def recheck(doc,graph,policy,direct_policy,source_hash,graph_hash,source_id):
 if policy.get('source_sha256')!=source_hash or direct_policy.get('source_sha256')!=source_hash:raise ValueError('source mismatch')
 p=copy.deepcopy(policy);p['graph_sha256']=graph_hash;dp=copy.deepcopy(direct_policy);dp['graph_sha256']=graph_hash
 fresh_direct=collect_direct(doc,graph,dp,source_hash,graph_hash)
 pairs={(x['edge_id'],x['source_text']['handle'],x['nominal_mm']) for x in fresh_direct['observations']}
 if not {(x['edge_id'],x['text_handle'],x['nominal_mm']) for x in p['seeds']}<=pairs:raise ValueError('current native source seed missing')
 coverage,junctions,risks,nested=collect_evidence(doc,graph,p,source_hash,graph_hash,source_id)
 work=copy.deepcopy(graph);old={}
 for e in work['edges']:
  inf=e.get('diameter_inference')
  if not inf:continue
  old[e['edge_id']]=copy.deepcopy(inf)
  for key in ('diameter_inference','diameter_candidate_mm','diameter_candidate_status','diameter_candidate_lineage'):e.pop(key,None)
  if inf.get('candidate_type')=='inherited_candidate':
   for key in ('pipe_diameter','diameter_nominal_mm','diameter_text','diameter_status'):e.pop(key,None)
 if set(old)!=set(p['edges']):raise ValueError('historical candidate scope differs from selected policy')
 recomputed,_=calculate(work,p,coverage,junctions,risks,nested,source_hash,graph_hash)
 fresh={e['edge_id']:e['diameter_inference'] for e in recomputed['edges'] if e.get('diameter_inference')}
 differences=compare(old,fresh)
 return {'status':'unchanged_candidates_rechecked_not_accepted' if not differences else 'candidate_difference_requires_invalidation',
  'source_sha256':source_hash,'graph_sha256':graph_hash,'prior_inference_graph_sha256s':sorted({x['source_graph_sha256'] for x in old.values()}),
  'checked_edges':p['edges'],'checked_junctions':p['junctions'],'fresh_direct_observation_count':len(fresh_direct['observations']),
  'recomputed_candidate_count':len(fresh),'differences':differences,'graph_mutated':False,'human_acceptance':False,
  'limitations':['Candidate DN remains non-authoritative and is limited to the selected source scope.','Preserve the historical inference provenance; this recheck does not update the graph.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','direct-policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 doc,proof=read_source(a.source);raw=a.graph.read_bytes();g=json.loads(raw);h=hashlib.sha256(raw).hexdigest()
 result=recheck(doc,g,json.loads(a.policy.read_text(encoding='utf8')),json.loads(a.direct_policy.read_text(encoding='utf8')),proof['source_sha256'],h,a.source.stem)
 result['policy_sha256']=hashlib.sha256(a.policy.read_bytes()).hexdigest();result['direct_policy_sha256']=hashlib.sha256(a.direct_policy.read_bytes()).hexdigest()
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'candidates':result['recomputed_candidate_count'],'differences':len(result['differences'])}))
 if result['differences']:raise SystemExit(2)
if __name__=='__main__':main()
