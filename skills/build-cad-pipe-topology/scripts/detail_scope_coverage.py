"""Inventory graph interface glyphs in explicitly scoped regions; never infer mapping."""
import argparse,hashlib,json,math,statistics
from collections import Counter
from pathlib import Path
from detail_glyph_ambiguity import glyph
from source_readability import read_source

def analyze(doc,graph,glyphs,policy,source_hash,graph_hash):
 if any(x.get('source_sha256')!=source_hash or x.get('graph_sha256')!=graph_hash for x in (glyphs,policy)) or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or graph mismatch')
 from canonicalize_confirmed_sideviews import source_expression_context
 graph=source_expression_context(graph)
 rows=glyphs['rows'];nodes={n['node_id']:n for n in graph['nodes']}
 if len(nodes)!=len(graph['nodes']) or not rows:raise ValueError('duplicate nodes or empty candidates')
 bands=policy['regions'];tol=float(policy['translation_tolerance']);
 if not math.isfinite(tol) or tol<=0:raise ValueError('bad tolerance')
 def inventory(region):
  b=bands[region];found=[]
  for n in nodes.values():
   if n.get('subtype')!='out_of_plane_interface' or n.get('system') not in ('supply','return'):continue
   if b['xmin']<=n['x']<=b['xmax'] and b['ymin']<=n['y']<=b['ymax']:
    evidence=glyph(doc,n);found.append({'node_id':n['node_id'],'system':n['system'],'center':evidence['center'],'source_handles':evidence['handles'],'signature':evidence['signature']})
  return sorted(found,key=lambda n:(n['system'],n['center'][0],n['node_id']))
 upper,lower=inventory('upper'),inventory('detail');u={x['node_id']:x for x in upper};l={x['node_id']:x for x in lower}
 if not upper or not lower:raise ValueError('empty region')
 seen_upper=set();seen_lower=set();vectors=[]
 for r in rows:
  a=u.get(r['upper_glyph']);b=l.get(r['detail_glyph'])
  if a is None or b is None or a['system']!=r['system'] or b['system']!=r['system'] or a['signature']!=r['upper']['signature'] or b['signature']!=r['detail']['signature']:raise ValueError('candidate not witnessed in selected regions')
  if a['node_id'] in seen_upper or b['node_id'] in seen_lower:raise ValueError('duplicate candidate endpoint')
  seen_upper.add(a['node_id']);seen_lower.add(b['node_id']);vectors.append((a['center'][0]-b['center'][0],a['center'][1]-b['center'][1]))
 offset=[statistics.median(v[0] for v in vectors),statistics.median(v[1] for v in vectors)]
 for item in upper:
  item['in_existing_candidate_set']=item['node_id'] in seen_upper
  matches=[]
  for b in lower:
   if item['system']!=b['system'] or item['signature']!=b['signature']:continue
   residual=math.dist((item['center'][0]-b['center'][0],item['center'][1]-b['center'][1]),offset)
   if residual<=tol:matches.append({'detail_node_id':b['node_id'],'offset_residual':residual})
  item['translation_matches']=matches
  item.pop('signature')
 for item in lower:
  item['in_existing_candidate_set']=item['node_id'] in seen_lower;item.pop('signature')
 return {'status':'scoped_coverage_not_mapping','source_sha256':source_hash,'graph_sha256':graph_hash,'calibration':'median of existing candidates; not independent identity evidence','median_xy_offset':offset,'translation_tolerance':tol,'regions':bands,'upper':upper,'detail':lower,'counts':{'upper':len(upper),'detail':len(lower),'upper_in_candidates':len(seen_upper),'upper_outside_candidates':len(upper)-len(seen_upper),'detail_in_candidates':len(seen_lower),'upper_by_system':dict(Counter(i['system'] for i in upper)),'detail_by_system':dict(Counter(i['system'] for i in lower))},'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'limitations':['Only graph interface nodes in the explicit regions are inventoried; absent source entities and other regions are not audited.','A shared translation was calibrated from the same candidates and cannot establish identity or hydraulic connection.','Unselected upper glyphs are not proof that a matching detail does not exist elsewhere.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('source','graph','glyphs','policy','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);r=analyze(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.glyphs.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));r.update(glyphs_sha256=sha(a.glyphs),policy_sha256=sha(a.policy),source_text_preflight=proof['status']);
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'counts':r['counts']}))
if __name__=='__main__':main()
