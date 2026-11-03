import pipe_geometry as pg_constants
"""Profile-configured native source preparation. No SH16 file paths in the execution path."""
import json,math,csv,hashlib,collections
from pathlib import Path
import ezdxf
from ezdxf import bbox
from pipe_geometry import *
from native_recovery import *
from equipment_assemblies import *
from auxiliary_pipes import *
def prepare(dxf,bindings_path,profiles_path,config,output_dir):
 bindings=json.loads(Path(bindings_path).read_text(encoding='utf8'))
 TASK=config['project_id'];OUT=Path(output_dir);OUT.mkdir(parents=True,exist_ok=True)
 SRC=Path(dxf)
 SYSTEMS=config['system_layers']
 TYPES={k:tuple(v)for k,v in config['inline_types'].items()}
 BRIDGES=set(config['inline_bridge_blocks'])
 def write(name,data):
  (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 def csvout(name,rows,fields=None):
  fields=fields or list(dict.fromkeys(k for r in rows for k in r)) or ['status']
  with (OUT/name).open('w',encoding='utf-8-sig',newline='')as f:
   w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader()
   for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list,tuple)) else v for k,v in r.items()})
 def segment_box_contact(a,b,bb):
  if point_bbox(a,bb)<=pg_constants.TOL or point_bbox(b,bb)<=pg_constants.TOL:return True
  corners=[(bb[0],bb[1]),(bb[2],bb[1]),(bb[2],bb[3]),(bb[0],bb[3])]
  return any(intersection(a,b,c,d)is not None for c,d in zip(corners,corners[1:]+corners[:1]))
 def source_geometry(e):
  t=e.dxftype()
  if t=='LINE':return {'type':t,'a':xy(e.dxf.start),'b':xy(e.dxf.end)}
  if t=='ARC':return {'type':t,'center':xy(e.dxf.center),'radius':e.dxf.radius,'start_angle':e.dxf.start_angle,'end_angle':e.dxf.end_angle}
  return {'type':t}
 doc=ezdxf.readfile(SRC);m=doc.modelspace();segments=[];arcs=[]
 for e in m:
  sy=SYSTEMS.get(e.dxf.layer)
  if not sy:continue
  if e.dxftype()=='LINE':segments.append({'a':xy(e.dxf.start),'b':xy(e.dxf.end),'system':sy,'handle':e.dxf.handle,'source_layer':e.dxf.layer})
  elif e.dxftype()=='ARC':arcs.append({'a':xy(e.start_point),'b':xy(e.end_point),'system':sy,'handle':e.dxf.handle,'radius':e.dxf.radius,'span':(e.dxf.end_angle-e.dxf.start_angle)%360,'source_display_geometry':source_geometry(e)})
 original_segments=list(segments);arc_audit=[]
 bs_segments,bs_curves,bs_curve_audit=physical_auxiliary_geometry(list(m),config['auxiliary_pipe_layer'])
 for layer in config.get('additional_auxiliary_pipe_layers',[]):
  extra,curves,audit=physical_auxiliary_geometry(list(m),layer);bs_segments+=extra;bs_curves+=curves;bs_curve_audit+=audit
 write('auxiliary_curve_contact_audit.json',bs_curve_audit)
 for a in arcs:
  norm,status=normalize_arc(a,original_segments+bs_segments,original_segments)
  arc_audit.append(dict(a,normalization_status=status,crossings=norm.get('crossings',[])if norm else []))
  if norm:segments.append(norm)
 for a in bs_curves:
  norm,status=normalize_arc(a,original_segments+bs_segments,bs_segments)
  arc_audit.append(dict(a,normalization_status=status,crossings=norm.get('crossings',[])if norm else []))
  if norm:bs_segments.append(norm)
 symbols=[]
 for e in m.query('INSERT'):
  if e.dxf.name not in TYPES:continue
  b=bbox.extents([e]);symbols.append({'handle':e.dxf.handle,'block':e.dxf.name,'bounds':[b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y],'insert':xy(e.dxf.insert),'bridge_allowed':e.dxf.name in BRIDGES,'entity':e})
 # Recover flexible joints from their actual two-flange native signature, never block INSERT origin.
 pump_prototypes=[]
 for ce in m.query('CIRCLE'):
  if ce.dxf.layer!='HVAC-D-阀门仪表':continue
  pp=detect_pump(ce,list(m))
  if pp:pump_prototypes.append(pp)
 pump_bindings=[]
 for binding in bindings:
  if not binding['equipment_tag'].startswith(tuple(config.get('pump_tag_prefixes',['CHWP-','CWP-']))):continue
  candidates=[pp for pp in pump_prototypes if dist((binding['x'],binding['y']),pp['center'])<=pp['radius']*5]
  if len(candidates)==1:pump_bindings.append(dict(candidates[0],binding=binding))
 aux=[];aux_audit=[]
 for le in m.query('LINE'):
  if le.dxf.layer not in config['native_lead_layers']:continue
  a,b=xy(le.dxf.start),xy(le.dxf.end);evidence=[]
  if le.dxf.layer==config['pump_lead_layer']:
   for pp in pump_bindings:
    c,r=pp['center'],pp['radius']
    if abs(a[0]-c[0])<pg_constants.TOL*2 and abs(b[0]-c[0])<pg_constants.TOL*2 and min(dist(a,c),dist(b,c))<r*1.05 and max(dist(a,c),dist(b,c))<r*2.05:
     # Clip native lead overshoot to the exact pump circle boundary along the source axis.
     rad=math.sqrt(max(0,r*r-(a[0]-c[0])**2))
     def clip(p):
      if abs(p[1]-c[1])<rad:return(p[0],c[1]+(rad if p[1]>c[1]else -rad))
      return p
     a,b=clip(a),clip(b);evidence=pp['source_handles'];break
  else:
   for ee in m.query('INSERT'):
    if ee.dxf.name not in list(config['equipment_blocks']):continue
    prim=[(xy(pe.dxf.start),xy(pe.dxf.end))for pe in ee.virtual_entities()if pe.dxftype()=='LINE']
    if any(segdist(z,u,v)<=pg_constants.TOL for z in [a,b]for u,v in prim):evidence=[ee.dxf.handle];break
  if evidence and dist(a,b)>pg_constants.TOL:
   aux.append({'a':a,'b':b,'system':'pending','handle':le.dxf.handle,'normalization':'native_equipment_connection_lead','source_layer':le.dxf.layer});aux_audit.append({'source_handle':le.dxf.handle,'source_layer':le.dxf.layer,'a':a,'b':b,'port_evidence_handles':evidence,'source_display_geometry':{'a':xy(le.dxf.start),'b':xy(le.dxf.end)}})
 bridges=[];native_gap_audit=[]
 for sym in symbols:
  if sym['block']not in ['橡胶软连接','金属软连接']:continue
  docks,reason=dock_axis(sym['entity'],segments+aux)
  audit={'source_handle':sym['handle'],'source_block_name':sym['block'],'recognition_rule':reason,'status':'pending'}
  if docks:
   a,b=docks;bridges.append({'a':a,'b':b,'system':'pending','handle':'SYMBOL-'+sym['handle'],'source_handles':[sym['handle']],'normalization':'native_two_flange_symbol_axis'});audit.update(a=a,b=b,gap_length=dist(a,b))
  native_gap_audit.append(audit)
 # Propagate a source system only through exact contacts and verified flange axes.
 bs_inline_bridges,bs_inline_audit=native_inline_gap_candidates(bs_segments,symbols)
 bs_segments+=bs_inline_bridges;write('auxiliary_inline_gap_audit.json',bs_inline_audit)
 raw=aux+bridges+bs_segments;temp=[dict(r,system='inference')for r in raw];iv,ip,ia=build_network(temp);v_components={};component_systems={};comp=0
 for v in range(len(iv)):
  if v in v_components:continue
  todo=[v];v_components[v]=comp;comp+=1
  while todo:
   k=todo.pop()
   for j in ia.get(('inference',k),[]):
    for nxt in ip[j]['vertices']:
     if nxt not in v_components:v_components[nxt]=v_components[k];todo.append(nxt)
 for r in segments:
  for v,z in enumerate(iv):
   if on(z,r['a'],r['b']):
    if r.get('normalization')=='semicircular_crossover_chord'and min(dist(z,r['a']),dist(z,r['b']))>pg_constants.TOL:continue
    # Only an actual auxiliary endpoint can dock onto a typed native main.
    if any(min(dist(z,rs['a']),dist(z,rs['b']))<=pg_constants.TOL for rs in raw):component_systems.setdefault(v_components[v],set()).add(r['system'])
 recovered=[]
 for r in raw:
  v=next(i for i,p in enumerate(iv)if dist(p,r['a'])<=pg_constants.TOL);systems=component_systems.get(v_components[v],set())
  if len(systems)==1:recovered.append(dict(r,system=next(iter(systems))))
  for audit in aux_audit+native_gap_audit:
   if audit['source_handle']in [r['handle'],r['handle'].replace('SYMBOL-','')]:audit.update(status='recovered_unique_contact_system'if len(systems)==1 else 'pending_ambiguous_or_unknown_system',candidate_systems=sorted(systems))
 segments+=recovered;gap_audit=native_gap_audit
 write('auxiliary_pipe_system_audit.json',[{'source_handle':r['handle'],'source_layer':r.get('source_layer'),'system':r['system'],'status':'source_contact_inferred_unreviewed','a':r['a'],'b':r['b']}for r in recovered if r in bs_segments or r.get('source_layer')==config['auxiliary_pipe_layer']])
 write('native_auxiliary_leads.json',aux_audit);write('exploded_pump_recognition.json',[{k:v for k,v in pp.items()if k!='binding'}|{'equipment_tag':pp['binding']['equipment_tag']}for pp in pump_bindings])
 
 return dict(doc=doc,source=SRC,segments=segments,raw=raw,original_segments=original_segments,arc_audit=arc_audit,symbols=symbols,pump_bindings=pump_bindings,bs_segments=bs_segments,bindings=bindings,profiles=json.loads(Path(profiles_path).read_text(encoding='utf8')))
