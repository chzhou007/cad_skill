"""Screen explicitly selected cross-view DN clues; no mapping or DN assignment."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source
from pipe_annotation_attributes import parse_dn_annotation

LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
def projection(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
 if not den:return None
 u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den
 return u,math.hypot(p[0]-a[0]-u*dx,p[1]-a[1]-u*dy)

def screen(plan,iso,doc,policy):
 pe={x['edge_id']:x for x in plan['edges']};ie={x['edge_id']:x for x in iso['edges']};rows=[]
 selected=policy.get('selections')
 if len(pe)!=len(plan['edges']) or len(ie)!=len(iso['edges']) or not isinstance(selected,list) or not selected:raise ValueError('invalid graph or selection')
 if len({x['text_handle'] for x in selected})!=len(selected) or len({(x['plan_edge'],x['iso_edge']) for x in selected})!=len(selected):raise ValueError('duplicate selected text or edge pair')
 for spec in selected:
  a=pe[spec['plan_edge']];b=ie[spec['iso_edge']];system=spec['system'];t=doc.entitydb.get(spec['text_handle']);line=doc.entitydb.get(spec['line_handle'])
  if system not in LAYERS or a.get('system')!=system or b.get('system')!=system:raise ValueError('system mismatch')
  inf=a.get('diameter_inference',{});plan_dn=inf.get('nominal_mm_candidate');plan_kind='source_scoped_inheritance_candidate';lineage=inf.get('lineage',[])
  if inf.get('status')!='source_scoped_inheritance_candidate_not_accepted':
   local=a.get('pipe_diameter') or {};obs=local.get('observations') or []
   if local.get('status')!='local_source_observation_edgewide_unverified' or local.get('nominal_mm') is not None or len(obs)!=1 or obs[0].get('status')!='native_source_local_observation':raise ValueError('plan candidate missing')
   plan_dn=obs[0].get('nominal_mm');plan_kind='native_local_observation';lineage=[{'text_handle':obs[0].get('text',{}).get('handle'),'source_line_handle':obs[0].get('source_line_handle')}]
   if not lineage[0]['text_handle'] or lineage[0]['source_line_handle'] not in a.get('source_handles',[]):raise ValueError('incomplete plan local observation')
  if not isinstance(plan_dn,(int,float)) or isinstance(plan_dn,bool) or not math.isfinite(plan_dn) or plan_dn<=0:raise ValueError('plan candidate missing')
  if not t or t not in doc.modelspace() or t.dxftype()!='TEXT' or t.dxf.layer not in policy['text_layers'] or t.plain_text()!=spec['text']:raise ValueError('source text mismatch')
  if tuple(t.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or t.dxf.get('text_generation_flag',0)!=0:raise ValueError('unsupported source text transform')
  parsed=parse_dn_annotation(t.plain_text())
  if not parsed:raise ValueError('unsupported DN syntax')
  if not line or line not in doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[system]:raise ValueError('native source line mismatch')
  p=(t.dxf.insert.x,t.dxf.insert.y);a0=(line.dxf.start.x,line.dxf.start.y);b0=(line.dxf.end.x,line.dxf.end.y);height=float(t.dxf.height);angle=math.radians(t.dxf.rotation);hits=[]
  if not math.isfinite(height) or height<=0:raise ValueError('invalid text height')
  for ent in doc.modelspace().query('LINE'):
   if ent.dxf.layer not in LAYERS.values():continue
   a1=(ent.dxf.start.x,ent.dxf.start.y);b1=(ent.dxf.end.x,ent.dxf.end.y);dx,dy=b1[0]-a1[0],b1[1]-a1[1];length=math.hypot(dx,dy)
   if not length or abs(math.cos(angle)*dy-math.sin(angle)*dx)/length>math.sin(math.radians(2)):continue
   proj=projection(p,a1,b1)
   if proj and 0<proj[0]<1 and proj[1]<=2*height:hits.append((proj[1],ent.dxf.handle))
  hits.sort()
  if not hits or hits[0][1]!=spec['line_handle'] or len(hits)>1 and hits[1][0]-hits[0][0]<=.5*height:raise ValueError('source text to line association ambiguous')
  witnessed=[]
  for path in b.get('attribute_paths',[]):
   for x,y in zip(path,path[1:]):
    u=projection(x,a0,b0);v=projection(y,a0,b0)
    if u and v and -.0001<=u[0]<=1.0001 and -.0001<=v[0]<=1.0001 and u[1]<=.05 and v[1]<=.05:witnessed.append([x,y])
  if len(witnessed)!=1:raise ValueError('native line does not uniquely cover an isometric edge segment')
  rows.append({'system':system,'plan_edge':spec['plan_edge'],'plan_dn_candidate_mm':plan_dn,'plan_candidate_kind':plan_kind,'plan_candidate_lineage':lineage,'iso_edge':spec['iso_edge'],'iso_text_handle':spec['text_handle'],'iso_text':t.plain_text(),'iso_dn_candidate_mm':parsed['nominal_mm'],'iso_line_handle':spec['line_handle'],'iso_witness_segment':witnessed[0],'label_distance_drawing_units':hits[0][0],'status':'different_values_potential_conflict' if plan_dn!=parsed['nominal_mm'] else 'same_values_candidate_only','crossview_path_mapping':'not_confirmed','annotation_binding':'candidate_not_accepted','physical_diameter_selected':False})
 return {'status':'crossview_candidate_screen_not_mapping','records':rows,'graph_mutated':False,'hil_ready':False,'limits':['Explicitly selected edges and native modelspace TEXT/LINE only; nested/proxy and F-shaped annotations are not covered.','Source text association is a candidate; neither same-device caption nor path proximity proves cross-view identity or equal pipe segment extent.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-source','iso-source','plan-graph','iso-graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--plan-local-dn-policy',type=Path)
 a=p.parse_args();policy=json.loads(a.policy.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 for key,path in [('plan_source_sha256',a.plan_source),('iso_source_sha256',a.iso_source),('plan_graph_sha256',a.plan_graph),('iso_graph_sha256',a.iso_graph)]:
  if policy.get(key)!=sha(path):raise ValueError(key+' mismatch')
 if a.output.exists():raise FileExistsError(a.output)
 plan_doc,pp=read_source(a.plan_source);doc,ip=read_source(a.iso_source);g=json.loads(a.plan_graph.read_text(encoding='utf8'));h=json.loads(a.iso_graph.read_text(encoding='utf8'));result=screen(g,h,doc,policy)
 local=[r for r in result['records'] if r['plan_candidate_kind']=='native_local_observation']
 if local:
  if a.plan_local_dn_policy is None or policy.get('plan_local_dn_policy_sha256')!=sha(a.plan_local_dn_policy):raise ValueError('missing or stale plan local DN policy')
  from source_direct_dn_evidence import collect
  verified=collect(plan_doc,g,json.loads(a.plan_local_dn_policy.read_text(encoding='utf8')),pp['source_sha256'],sha(a.plan_graph))
  observations={r['edge_id']:r for r in verified['observations']}
  for row in local:
   r=observations.get(row['plan_edge']);lineage=row['plan_candidate_lineage'][0]
   if not r or r['nominal_mm']!=row['plan_dn_candidate_mm'] or r['source_text']['handle']!=lineage['text_handle'] or r['source_line_handle']!=lineage['source_line_handle']:raise ValueError('plan local observation does not match source')
 result.update({k:policy[k] for k in ('plan_source_sha256','iso_source_sha256','plan_graph_sha256','iso_graph_sha256')});result.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),plan_preflight=pp,iso_preflight=ip)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'records':len(result['records']),'status':result['status']}))
if __name__=='__main__':main()
