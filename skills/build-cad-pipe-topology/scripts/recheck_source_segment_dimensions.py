"""Recheck scoped native dimension evidence on the current graph, without mutation."""
import argparse,copy,hashlib,json
from pathlib import Path
from source_readability import read_source
from attach_source_segment_dimensions import collect

def recheck(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source mismatch')
 p=copy.deepcopy(policy);p['graph_sha256']=graph_hash
 selections=p.get('dimensions',[]);handles=[x['dimension_handle'] for x in selections]
 if not handles or len(handles)!=len(set(handles)):raise ValueError('invalid scoped dimension selection')
 existing=[]
 for edge in graph.get('edges',[]):
  for item in edge.get('source_dimensioned_segments',[]):
   if item.get('dimension_handle') in handles:
    if item.get('edge_id')!=edge['edge_id']:raise ValueError('dimension attached to wrong edge')
    existing.append(copy.deepcopy(item))
 if len(existing)!=len(handles) or {x['dimension_handle'] for x in existing}!=set(handles):raise ValueError('missing or duplicated existing dimension evidence')
 current=collect(doc,graph,p,source_hash,graph_hash)
 old={x['dimension_handle']:x for x in existing};new={x['dimension_handle']:x for x in current}
 differences=[{'dimension_handle':h,'before':old.get(h),'after':new.get(h)} for h in sorted(set(old)|set(new)) if old.get(h)!=new.get(h)]
 return {'status':'unchanged_source_dimensions_rechecked' if not differences else 'dimension_difference_requires_invalidation',
         'source_sha256':source_hash,'graph_sha256':graph_hash,'prior_policy_graph_sha256':policy.get('graph_sha256'),
         'checked_dimensions':handles,'observations':current,'differences':differences,'graph_mutated':False,
         'whole_edge_physical_length_assigned':False,'human_acceptance':False,
         'limitations':['Recheck covers the selected native dimensions and graph segments only.','A dimensioned segment does not establish the complete edge or installed pipe length.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 doc,proof=read_source(a.source);raw=a.graph.read_bytes();g=json.loads(raw);h=hashlib.sha256(raw).hexdigest()
 result=recheck(doc,g,json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],h)
 result['policy_sha256']=hashlib.sha256(a.policy.read_bytes()).hexdigest()
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'status':result['status'],'dimensions':len(result['observations']),'differences':len(result['differences'])}))
 if result['differences']:raise SystemExit(2)
if __name__=='__main__':main()
