"""Re-extract and verify scoped native shaft text, without assigning pipe systems."""
import argparse,hashlib,json,math
from pathlib import Path
from architecture_context import extract

def inventory(doc,source_hash,context,graph,radius):
 if context.get('source_sha256')!=source_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash or not isinstance(radius,(int,float)) or isinstance(radius,bool) or not math.isfinite(radius) or radius<=0:raise ValueError('source or radius mismatch')
 transform=context.get('transform');fresh=extract(doc,transform,source_hash);original=[x for x in context['records'] if '井' in x.get('source_text','')];current=[x for x in fresh['records'] if '井' in x.get('source_text','')]
 def key(x):return (tuple(x.get('source_chain',[])),x.get('source_text'),x.get('entity_type'),x.get('source_layer'))
 a={key(x):x for x in original};b={key(x):x for x in current}
 if len(a)!=len(original) or len(b)!=len(current) or a.keys()!=b.keys():raise ValueError('shaft source text scope changed or ambiguous')
 rows=[]
 for k,x in a.items():
  y=b[k];pos=x.get('position');freshpos=y.get('position')
  if not isinstance(pos,list) or len(pos)!=2 or not isinstance(freshpos,list) or len(freshpos)!=2 or math.dist(pos,freshpos)>.05:raise ValueError('shaft text source position changed')
  nearby=[]
  for node in graph['nodes']:
   if node.get('subtype')!='out_of_plane_riser':continue
   xy=(node.get('x'),node.get('y'))
   if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in xy):raise ValueError('invalid riser position')
   dist=math.dist(pos,xy)
   if dist<=radius:nearby.append({'node_id':node['node_id'],'system':node.get('system'),'distance_drawing_units':dist,'status':'nearby_not_ownership'})
  nearby.sort(key=lambda v:(v['distance_drawing_units'],v['node_id']))
  rows.append({'source_text':x['source_text'],'source_chain':x['source_chain'],'source_layer':x['source_layer'],'entity_type':x['entity_type'],'position':pos,'nearby_riser_candidates':nearby,'status':'native_text_and_position_reextracted_no_system_assignment'})
 return {'status':'shaft_text_inventory_not_connection','source_sha256':source_hash,'radius_drawing_units':radius,'records':rows,'source_context_issue_count':len(fresh.get('issues',[])),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Scope is labels containing 井 already present in the supplied architectural context and re-extracted by its current source renderer; it is not proof of full native text coverage.','Proxy entities may be skipped during block copies without incrementing the context issue count; zero issues is not evidence of proxy completeness.','Virtual text under MULTILEADER is cached source rendering, not an independent shaft boundary.','Text, proximity and display categories do not prove water-system ownership, room boundary or cross-floor connection.']}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','context','graph','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--radius',type=float,required=True);a=p.parse_args()
 import sys
 sys.path.insert(0,str(Path.home()/'.codex/skills/build-cad-pipe-topology/scripts'))
 from source_readability import read_source
 doc,proof=read_source(a.source);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));r=inventory(doc,proof['source_sha256'],load(a.context),load(a.graph),a.radius);r.update(context_sha256=h(a.context),graph_sha256=h(a.graph),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'labels':len(r['records'])},ensure_ascii=False))
if __name__=='__main__':main()
