"""Validate freshness and completeness of independent detail-mapping screens."""
import argparse,hashlib,json
from pathlib import Path

def evaluate(graph_sha,source_sha,islands,glyphs):
 for evidence in (islands,glyphs):
  if evidence.get('graph_sha256')!=graph_sha or evidence.get('source_sha256')!=source_sha:raise ValueError('stale source or graph evidence')
 if islands.get('hil_ready') is not False or glyphs.get('hil_ready') is not False:raise ValueError('unexpected review state')
 def indexed(rows):
  result={}
  for r in rows:
   key=(r['service'] if 'service' in r else r['system'],r['rank'])
   if key in result:raise ValueError('duplicate candidate key')
   result[key]=r
  return result
 a=indexed(islands['rows']);b=indexed(glyphs['rows'])
 if not a or a.keys()!=b.keys() or glyphs.get('candidate_count')!=len(b):raise ValueError('candidate sets differ')
 records=[]
 for key in sorted(a):
  x,y=a[key],b[key]
  if x['upper_edge']!=y['upper_edge'] or x['detail_edge']!=y['detail_edge']:raise ValueError('candidate edge mismatch')
  if x.get('status')!='candidate_not_confirmed' or y.get('status')!='individual_mapping_ambiguous':raise ValueError('unsupported candidate state')
  records.append({'system':key[0],'rank':key[1],'upper_edge':x['upper_edge'],'detail_edge':x['detail_edge'],'source_exception':x.get('exception',''),'same_signature_detail_ranks':y['same_signature_detail_ranks'],'status':'mapping_unresolved'})
 return {'status':'detail_correspondence_unresolved','source_sha256':source_sha,'graph_sha256':graph_sha,'records':records,'candidate_count':len(records),'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['The screens verify referenced source geometry and ambiguity within their scope, not the physical identity of any pair.','A matching repeated glyph or translation does not prove correspondence.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','islands','glyphs','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if a.output.exists():raise FileExistsError(a.output)
 result=evaluate(sha(a.graph),sha(a.source),json.loads(a.islands.read_text(encoding='utf8')),json.loads(a.glyphs.read_text(encoding='utf8')));result.update(islands_sha256=sha(a.islands),glyphs_sha256=sha(a.glyphs),script_sha256=sha(Path(__file__)))
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'candidate_count':result['candidate_count']}))
if __name__=='__main__':main()
