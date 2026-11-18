"""Verify nested source shaft text and list nearby graph riser candidates.

Location screening only. This does not define a shaft boundary, room, pipe
ownership, cross-floor relationship, or hydraulic connection.
"""
import argparse,hashlib,json,math
from pathlib import Path

def scan(doc,source_hash,context,graph,labels,radius,tol=.05):
 if not source_hash or context.get('source_sha256')!=source_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source identity mismatch')
 if not labels or not math.isfinite(radius) or radius<=0 or not math.isfinite(tol) or tol<=0:raise ValueError('invalid labels, radius or tolerance')
 found=[]
 for record in context['records']:
  if record.get('source_text') not in labels:continue
  chain=record.get('source_chain');pos=record.get('position')
  if not isinstance(chain,list) or len(chain)!=2 or not isinstance(pos,list) or len(pos)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in pos):raise ValueError('unsupported source label chain or location')
  parent=doc.entitydb.get(chain[0]);child=doc.entitydb.get(chain[1])
  if parent is None or parent.dxftype()!='INSERT' or parent not in doc.modelspace() or child is None or child.dxftype()!='TEXT':raise ValueError('source label entities not supported')
  block=doc.blocks.get(parent.dxf.name)
  if block is None or block.block.dxf.flags & 12 or child not in block or child.plain_text()!=record['source_text']:raise ValueError('source label block or text mismatch')
  world=parent.matrix44().transform(child.ocs().to_wcs(child.dxf.insert))
  if math.dist((world.x,world.y),pos)>tol:raise ValueError('source label transform mismatch')
  risers=[]
  for node in graph['nodes']:
   if node.get('subtype')!='out_of_plane_riser':continue
   xy=(node.get('x'),node.get('y'))
   if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in xy):raise ValueError('invalid riser location')
   d=math.dist(pos,xy)
   if d<=radius:risers.append({'node_id':node['node_id'],'system':node.get('system'),'xy':list(xy),'distance_drawing_units':d,'source_handles':node.get('source_handles',[]),'status':'nearby_unverified'})
  risers.sort(key=lambda n:(n['distance_drawing_units'],n['node_id']))
  found.append({'source_text':record['source_text'],'source_chain':chain,'source_layer':record.get('source_layer'),'position':pos,'nearby_riser_candidates':risers,'status':'source_label_verified_location_only'})
 return {'status':'source_label_verified_no_connectivity_assertion','labels':found,'radius_drawing_units':radius,'source_sha256':source_hash,'graph_mutated':False,'hil_ready':False,'limitations':['Only explicitly named two-handle modelspace INSERT/TEXT chains; no deeper, XREF or proxy label coverage.','Text insertion point and radius do not establish shaft outline, pipe location within a shaft, system ownership, or cross-floor connection.','Nearby riser nodes may be provisional; graph and source geometry require separate technical review.']}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','context','graph','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--label',action='append',required=True);p.add_argument('--radius',type=float,required=True);a=p.parse_args()
 import sys
 sys.path.insert(0,str(Path.home()/'.codex/skills/build-cad-pipe-topology/scripts'))
 from source_readability import read_source
 doc,proof=read_source(a.source);ctx=a.context.read_bytes();gb=a.graph.read_bytes();r=scan(doc,proof['source_sha256'],json.loads(ctx),json.loads(gb),set(a.label),a.radius)
 r.update(context_sha256=hashlib.sha256(ctx).hexdigest(),graph_sha256=hashlib.sha256(gb).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'labels':len(r['labels']),'riser_candidates':sum(len(x['nearby_riser_candidates']) for x in r['labels']),'status':r['status']},ensure_ascii=False))
if __name__=='__main__':main()
