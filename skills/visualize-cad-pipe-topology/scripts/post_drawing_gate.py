"""Post-render fidelity gate. Machine checks never constitute a human HIL review."""
import argparse,hashlib,json,math
from pathlib import Path
import ezdxf
from ezdxf.disassemble import recursive_decompose
from cad_geometry import strokes
from instance_geometry import source_paths

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalized(paths):
 return sorted(json.dumps({'fill':bool(p.get('fill')),'points':[[round(float(v),6)for v in q]for q in p['points']]},sort_keys=True)for p in paths)

def check(viewer,dxf,visual_evidence=None):
 viewer=Path(viewer);dxf=Path(dxf);gp=viewer/'public/data/graph.json';g=json.loads(gp.read_text(encoding='utf8'));doc=ezdxf.readfile(dxf);tf=g['transform'];errors=[];pending=[];checks=[]
 def geometry(handles):
  out=[]
  for h in handles:
   if h not in doc.entitydb:raise ValueError('Missing source handle: '+h)
   for e in recursive_decompose([doc.entitydb[h]]):
    for pts,fill in strokes(e):
     if len(pts)>=2:out.append({'points':[[(p[0]-tf['originX'])/tf['scale'],(tf['originY']-p[1])/tf['scale']]for p in pts],'fill':bool(fill)})
  return out
 if digest(dxf)!=g['provenance']['sha256']:errors.append({'check':'source_identity','reason':'DXF hash differs from rendered graph'})
 ids={n['node_id']for n in g['nodes']}
 if len(ids)!=len(g['nodes']):errors.append({'check':'node_ids','reason':'Duplicate ID'})
 if len({e['edge_id']for e in g['edges']})!=len(g['edges']):errors.append({'check':'edge_ids','reason':'Duplicate ID'})
 for e in g['edges']:
  if e['start_node_id']not in ids or e['end_node_id']not in ids or e['start_node_id']==e['end_node_id']:errors.append({'check':'edge_endpoints','id':e['edge_id']})
 for n in g['nodes']:
  if n['node_type']!='physical_junction':continue
  incident=[e for e in g['edges']if n['node_id']in [e['start_node_id'],e['end_node_id']]]
  directions=[]
  for e in incident:
   points=e.get('path_points',[])
   if not points:continue
   p=(n['x'],n['y']);points=points if math.dist(p,points[0])<=math.dist(p,points[-1])else list(reversed(points))
   q=next((q for q in points if math.dist(p,q)>.5),None)
   if q:
    angle=math.atan2(q[1]-p[1],q[0]-p[0])
    if not any(abs(math.atan2(math.sin(angle-a),math.cos(angle-a)))<.001 for a in directions):directions.append(angle)
  if len(incident)==3 and len(directions)!=3:errors.append({'check':'junction_final_directions','id':n['node_id'],'reason':'Three adjacent edges do not form three distinct final directions'})
 for a in g.get('sourceFidelity',[]):
  missing=set(a['required_source_handles'])-set(a['exported_source_handles'])
  if missing or a['status']!='PASS':errors.append({'check':'assembly_members','id':a['id'],'missing_source_handles':sorted(missing)})
 edge_ids={e['edge_id']for e in g['edges']}
 def on_native(p,a,b):
  dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
  if length<1e-9:return False
  t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length
  return -.5<=t<=length+.5 and abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)/length<=.5
 for row in g.get('normalizationCoverage',[]):
  if row['status']=='applied'and(not row.get('edge_ids')or not set(row['edge_ids'])<=edge_ids):errors.append({'check':'source_gap_coverage','id':row['id'],'reason':'Accepted normalization is absent from loaded logical edges'})
  elif row['status']=='applied'and not any(on_native(row['a'],a,b)and on_native(row['b'],a,b)for e in g['edges']if e['edge_id']in row['edge_ids']for path in e.get('attribute_paths',[])for a,b in zip(path,path[1:])):errors.append({'check':'source_gap_geometry','id':row['id'],'reason':'Named final edge does not contain the complete normalized source span'})
  elif row['status']=='pending':pending.append({'id':row['id'],'reason':row.get('reason','Source gap remains pending')})
 for nid in g.get('junctionValidation',{}).get('new_unexplained_degree_exceptions',[]):errors.append({'check':'junction_degree','id':nid,'reason':'New unexplained degree exception after normalization'})
 for obj in g['nodes']+g['instances']+g.get('pendingSourceObjects',[]):
  equipment=obj.get('node_type')=='equipment';component='source_device_name'in obj
  if not equipment and not component:continue
  key=obj.get('node_id',obj.get('id'));handles=obj.get('display_source_handles')if equipment else obj.get('source_handles');chain=obj.get('display_source_chain')
  if isinstance(chain,str):chain=json.loads(chain)if chain.strip()else None
  if isinstance(handles,str):handles=json.loads(handles)if handles.strip()else None
  if not handles and not chain:
   pending.append({'id':key,'reason':'No explicit instance display source handles; native fidelity unverified'});continue
  if component and obj.get('source_kind')in ['block_insert','block_reference']:
   body=chain[-1]if chain else obj.get('source_top_handle')or(handles[0]if len(handles)==1 else None)
   if body not in doc.entitydb or(not chain and body not in handles)or doc.entitydb[body].dxftype()!='INSERT' or doc.entitydb[body].dxf.name!=obj['source_block_name']:errors.append({'check':'component_source_identity','id':key,'reason':'Parent assembly is not the declared native component; resolve actual nested INSERT chain'})
  expected=[{'points':[[(p[0]-tf['originX'])/tf['scale'],(tf['originY']-p[1])/tf['scale']]for p in path['points']],'fill':path['fill']}for path in source_paths(doc,chain=chain)]if chain else geometry(handles);actual=obj.get('sourceGeometry',[]);ok=normalized(expected)==normalized(actual)
  checks.append({'id':key,'kind':'equipment'if equipment else 'component','source_handles':handles,'expected_paths':len(expected),'actual_paths':len(actual),'status':'PASS'if ok else 'FAIL'})
  if not ok:errors.append({'check':'native_geometry','id':key,'reason':'Exported paths/fills differ from source instance at original transform'})
 exported=set()
 for obj in g['nodes']+g['instances']+g.get('pendingSourceObjects',[]):
  hs=obj.get('display_source_handles')or obj.get('source_handles')or[]
  if isinstance(hs,str):hs=json.loads(hs)if hs.strip()else[]
  exported.update(hs)
 for row in g.get('sourceTaggedHeadCoverage',[]):
  h=row['source_head_handle']
  if row['status']=='pending_unrepresented_tagged_head':pending.append({'id':h,'reason':'Tagged source instrument head has no proven component representation: '+row['source_tag']})
  elif row['status']=='represented_source_geometry'and h not in exported:errors.append({'check':'source_tagged_head_coverage','id':h,'reason':'Recognized source head is absent from exported instance geometry'})
 for r in g.get('review',[]):pending.append({'id':r['id'],'reason':r['reason']})
 for r in g.get('componentReview',[]):pending.append({'id':r['id'],'reason':r['reason']})
 pending.extend(g.get('technicalPending',[]))
 for e in g['edges']:
  if 'pending'in str(e.get('system_assignment','')).lower():pending.append({'id':e['edge_id'],'reason':'Source hydraulic system classification remains pending'})
 for n in g['nodes']:
  if n.get('display_source_status')=='pending_ambiguous_display_family':pending.append({'id':n['node_id'],'reason':'Competing native equipment display families'})
 visual={'status':'NOT_CHECKED','required':'Inspect same-range CAD/topology overview, each equipment family, repeated assemblies, terminals/crossovers and all repaired regions. Record actual observations and evidence against this graph SHA.'}
 if visual_evidence:
  ev=json.loads(Path(visual_evidence).read_text(encoding='utf8'));bad=[]
  if ev.get('graph_sha256')!=digest(gp):bad.append('Visual evidence belongs to another rendered graph')
  if (viewer/'public/app.js').is_file()and ev.get('renderer_sha256')!=digest(viewer/'public/app.js'):bad.append('Visual evidence belongs to another renderer')
  if not ev.get('regions'):bad.append('No inspected regions')
  for r in ev.get('regions',[]):
   p=Path(visual_evidence).parent/r['artifact']
   if r.get('result')!='checked' or not r.get('observation')or not p.is_file()or digest(p)!=r.get('sha256'):bad.append('Unresolved/missing/stale visual region: '+r.get('id','unknown'))
  if ev.get('known_unfixed_defects'):bad.append('Known deterministic defects remain')
  if bad:errors.extend({'check':'visual_evidence','reason':s}for s in bad)
  else:visual={'status':'CHECKED','regions':ev['regions'],'performed_by':ev.get('performed_by','unspecified'),'scope':'Technical drawing check only; HIL review remains unchanged'}
 status='FAIL'if errors else 'AWAITING_VISUAL_CHECK'if visual['status']!='CHECKED'else 'PASS_WITH_PENDING'if pending else 'PASS'
 result={'schemaVersion':1,'status':status,'graph_sha256':digest(gp),'source_sha256':digest(dxf),'machine_status':'FAIL'if errors else 'PASS','checked_instances':len(checks),'checks':checks,'blocking_defects':errors,'pending':pending,'visual_check':visual,'human_review':'unchanged; no automatic attestation','scope_limit':'Known source families and supplied handle evidence; not proof that every unknown CAD primitive has semantic recognition'}
 (viewer/'quality-gate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--viewer',type=Path,required=True);p.add_argument('--dxf',type=Path,required=True);p.add_argument('--visual-evidence',type=Path);a=p.parse_args();r=check(a.viewer,a.dxf,a.visual_evidence);print(json.dumps({k:r[k]for k in ['status','machine_status','checked_instances','blocking_defects']},indent=2));raise SystemExit(1 if r['status']=='FAIL'else 0)
