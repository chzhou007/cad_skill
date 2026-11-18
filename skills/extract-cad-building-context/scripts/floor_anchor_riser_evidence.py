"""Test a hypothesized floor translation against selected native text anchors.

Result is a registration candidate and aligned riser locations, not evidence
that risers are physically continuous or mapped to an isometric graph.
"""
import argparse,hashlib,json,math,statistics
from pathlib import Path

def _anchor(doc,context,item,tol):
 chain=item['chain'];matches=[r for r in context['records'] if r.get('source_chain')==chain and r.get('source_text')==item['text']]
 if len(chain)!=2 or len(matches)!=1:raise ValueError('anchor chain is missing or ambiguous')
 p=doc.entitydb.get(chain[0]);t=doc.entitydb.get(chain[1]);r=matches[0]
 if not p or p.dxftype()!='INSERT' or p not in doc.modelspace() or not t or t.dxftype()!='TEXT':raise ValueError('unsupported anchor entities')
 block=doc.blocks.get(p.dxf.name)
 if block is None or block.block.dxf.flags & 12 or t not in block or t.plain_text()!=item['text']:raise ValueError('anchor native text mismatch')
 q=p.matrix44().transform(t.ocs().to_wcs(t.dxf.insert));xy=r['position']
 if math.dist((q.x,q.y),xy)>tol:raise ValueError('anchor transform mismatch')
 return xy

def compare(doc_a,doc_b,source_a,source_b,context_a,context_b,graph_a,graph_b,shaft_a,shaft_b,policy,tol=.05):
 for source,context,graph,shaft in [(source_a,context_a,graph_a,shaft_a),(source_b,context_b,graph_b,shaft_b)]:
  if not source or context.get('source_sha256')!=source or graph.get('metadata',{}).get('source_sha256')!=source or shaft.get('source_sha256')!=source:raise ValueError('source identity mismatch')
 anchors=policy['anchors']
 if len(anchors)<3:raise ValueError('at least three anchors required')
 source_pts=[];target_pts=[];details=[]
 for spec in anchors:
  if spec['a']['text']!=spec['b']['text']:raise ValueError('anchor text mismatch')
  a=_anchor(doc_a,context_a,spec['a'],tol);b=_anchor(doc_b,context_b,spec['b'],tol);source_pts.append(a);target_pts.append(b);details.append({'text':spec['a']['text'],'source_chain':spec['a']['chain'],'target_chain':spec['b']['chain'],'source_position':a,'target_position':b})
 if len({tuple(x) for x in source_pts})!=len(source_pts) or len({tuple(x) for x in target_pts})!=len(target_pts):raise ValueError('duplicate anchor points')
 a,b,c=source_pts[:3];area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
 if area<policy.get('minimum_triangle_area',1):raise ValueError('anchors are collinear or too close')
 delta=[statistics.median([b[i]-a[i] for a,b in zip(source_pts,target_pts)]) for i in (0,1)]
 for row,a,b in zip(details,source_pts,target_pts):
  row['residual']=math.dist([a[0]+delta[0],a[1]+delta[1]],b)
  if row['residual']>tol:raise ValueError('anchors do not support one translation')
 def candidates(shaft,graph):
  ids={n['node_id']:n for n in graph['nodes']};r=[]
  for label in shaft['labels']:
   for c in label['nearby_riser_candidates']:
    n=ids.get(c['node_id'])
    if not n or n.get('subtype')!='out_of_plane_riser' or n.get('system')!=c['system'] or math.dist((n['x'],n['y']),c['xy'])>tol:raise ValueError('riser candidate mismatch')
    r.append(c)
  return r
 aa=candidates(shaft_a,graph_a);bb=candidates(shaft_b,graph_b);pairs=[]
 for x in aa:
  for y in bb:
   if x['system']!=y['system']:continue
   residual=math.dist([x['xy'][0]+delta[0],x['xy'][1]+delta[1]],y['xy'])
   pairs.append({'source_node':x['node_id'],'target_node':y['node_id'],'system':x['system'],'registration_residual_drawing_units':residual,'status':'spatial_candidate_not_a_connection'})
 return {'status':'translation_hypothesis_not_confirmed','translation':delta,'anchors':details,'anchor_triangle_area_square_drawing_units':area,'same_system_riser_pairs':pairs,'graph_mutated':False,'hil_ready':False,'limitations':['Only explicitly selected native labels, not a global registration or unique correspondence; alternative repeated text matches may exist.','Selected anchors are not evidence of shaft boundary or connection; aligned risers require original drawing validation and isometric corroboration.','No rotation, scale or mirrored registration estimated; units are drawing coordinates.']}

def main():
 p=argparse.ArgumentParser()
 for x in ('source-a','source-b','context-a','context-b','graph-a','graph-b','shaft-a','shaft-b','policy','output'):p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();import sys;sys.path.insert(0,str(Path.home()/'.codex/skills/build-cad-pipe-topology/scripts'));from source_readability import read_source
 da,pa=read_source(a.source_a);db,pb=read_source(a.source_b);files={k:getattr(a,k.replace('-','_')).read_bytes() for k in ['context-a','context-b','graph-a','graph-b','shaft-a','shaft-b','policy']};j={k:json.loads(v) for k,v in files.items()};policy=j['policy'];sha=lambda b:hashlib.sha256(b).hexdigest()
 for k in ['context-a','context-b','graph-a','graph-b','shaft-a','shaft-b']:
  if policy['input_sha256'][k]!=sha(files[k]):raise ValueError('policy input hash mismatch: '+k)
 if policy['source_sha256']!=[pa['source_sha256'],pb['source_sha256']]:raise ValueError('policy source hash mismatch')
 if j['shaft-a']['graph_sha256']!=sha(files['graph-a']) or j['shaft-b']['graph_sha256']!=sha(files['graph-b']):raise ValueError('stale riser candidates')
 r=compare(da,db,pa['source_sha256'],pb['source_sha256'],j['context-a'],j['context-b'],j['graph-a'],j['graph-b'],j['shaft-a'],j['shaft-b'],policy)
 r.update(anchor_selection_basis=policy.get('selection_basis','not documented'),source_sha256=policy['source_sha256'],input_sha256=policy['input_sha256'],policy_sha256=sha(files['policy']),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=[pa,pb])
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'translation':r['translation'],'pairs':r['same_system_riser_pairs']},ensure_ascii=False))
if __name__=='__main__':main()
