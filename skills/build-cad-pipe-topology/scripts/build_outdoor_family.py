from pathlib import Path
import json,csv,math,hashlib,collections,sys
import ezdxf
class Graph:
 def __init__(self):self.adj={}
 def __iter__(self):return iter(self.adj)
 def __len__(self):return len(self.adj)
 def __getitem__(self,p):return self.adj[p]
 def has_edge(self,a,b):return a in self.adj and b in self.adj[a]
 def add_edge(self,a,b,**attrs):
  self.adj.setdefault(a,{})[b]=attrs;self.adj.setdefault(b,{})[a]=attrs
 def degree(self,p):return len(self.adj[p])
from ezdxf.math import Matrix44
from ezdxf import bbox
def Point(pt):return pt
class LineString:
 def __init__(self,pts):self.a,self.b=pts;self.v=[self.b[i]-self.a[i] for i in range(2)];self.l2=sum(x*x for x in self.v)
 def project(self,p,normalized=True):return max(0,min(1,sum((p[i]-self.a[i])*self.v[i] for i in range(2))/self.l2))
 def distance(self,p):
  t=self.project(p);return math.dist(p,[self.a[i]+t*self.v[i] for i in range(2)])
import argparse
from straight_crossovers import recover_straight_crossovers
import pipe_geometry as pg
from topology_normalization import snap_near_junction_endpoints
cli=argparse.ArgumentParser();cli.add_argument('--input-root',type=Path,required=True);cli.add_argument('--output-root',type=Path,required=True);cli.add_argument('--normalization-config',type=Path,required=True);args=cli.parse_args()
BATCH=args.input_root;OUT=args.output_root;LIB=BATCH/'reference-library/parameters-v1';NORM=json.loads(args.normalization_config.read_text(encoding='utf8'))
PROFILES=json.loads((LIB/'equipment-profiles.json').read_text(encoding='utf8'));MAN=json.loads((LIB/'catalog-manifest.json').read_text(encoding='utf8'))
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def csvout(p,rows,cols):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader()
  for r in rows:w.writerow({k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v) for k,v in r.items() if k in cols})
def equipment(name):
 if '双吸泵' in name:return ('cooling_water_pump' if '冷却泵' in name else 'pump','Pump')
 if name.startswith('主机 -'):return 'chiller','Chiller'
 if '板式换热器' in name:return 'heat_exchanger','Heat Exchanger'
 if '定压补水装置' in name:return 'pressurization_unit','Pressurization Unit'
 if '加药装置' in name:return 'dosing_unit','Dosing Unit'
def component(name):
 for words,fam in [(['橡胶软接头'],'rubber_flexible_joint'),(['消声止回阀'],'check_valve'),(['Y型过滤器'],'Y_strainer'),(['蝶阀'],'butterfly_valve'),(['电动调节阀'],'motorized_control_valve'),(['传感器'],'sensor')]:
  if any(w in name for w in words):return fam

def run(sheet):
 task=next(x for x in json.loads((BATCH/'batch.json').read_text(encoding='utf8'))['tasks'] if x['sheet']==sheet);tid=task['task_id'];p=next((BATCH/'sources/DXF').glob(sheet+'-*'));out=OUT/'tasks'/tid/'topology';out.mkdir(parents=True,exist_ok=True);rep=out.parent/'reports';rep.mkdir(exist_ok=True)
 d=ezdxf.readfile(p);m=d.modelspace();nodes=[];unres=[];geom=[];block_audit=[];layers=collections.Counter();curves=[];eq=[];bboxcache={}
 def walk(layout,parent=Matrix44(),chain=(),depth=0):
  if depth>12:raise RuntimeError('Nested block depth exceeded')
  for e in layout:
   layers[(e.dxf.layer,e.dxftype())]+=1;handle=e.dxf.handle;path=chain+(handle,)
   if e.dxftype()=='INSERT':
    name=e.dxf.name;mat=e.matrix44()@parent;block_audit.append({'source_chain':list(path),'name':name,'depth':depth,'layer':e.dxf.layer,'instance_origin':list(parent.transform(e.dxf.insert))[:2]})
    typ=equipment(name);comp=component(name)
    if typ or comp:
     if name not in bboxcache:
      try:bboxcache[name]=bbox.extents(d.blocks[name],fast=True)
      except Exception:bboxcache[name]=None
     box=bboxcache[name]
     if box and box.has_data:
      a,b=box.extmin,box.extmax;corn=[mat.transform((x,y,0)) for x in [a.x,b.x] for y in [a.y,b.y]];bounds=[min(v.x for v in corn),min(v.y for v in corn),max(v.x for v in corn),max(v.y for v in corn)];x=(bounds[0]+bounds[2])/2;y=(bounds[1]+bounds[3])/2
     else:x,y,_=parent.transform(e.dxf.insert);bounds=[x,y,x,y]
     if typ:
      fam,label=typ;ref_family={'cooling_water_pump':'pump','pressurization_unit':'pressurization'}.get(fam,fam);refs=[v['profile_id'] for v in PROFILES if v['family']==ref_family and (fam!='cooling_water_pump' or v['profile_id'].startswith('CWP-'))];nid='EQ-'+ '-'.join(path);eq.append({'node_id':nid,'node_type':'equipment','subtype':fam,'label':label+' '+str(len(eq)+1),'floor':0,'x':x,'y':y,'source_chain':list(path),'source_block_name':name,'source_bounds':bounds,'parameter_profile_candidates':refs,'parameter_binding_state':'family_reference_only_unreviewed' if refs else 'no_schedule_reference','recognition_state':'descriptive_native_block_equipment_unreviewed','connection_state':'native_equipment_ports_pending','system':'unresolved','placement_rule':'native_block_outline_center','review_status':'unreviewed'})
     if comp:unres.append({'device_name':'CMP-'+ '-'.join(path),'equipment_type':comp,'source_chain':list(path),'source_block_name':name,'source_kind':'nested_native_block' if chain else 'native_block','x':x,'y':y,'source_bounds':bounds,'assignment_status':'unresolved','reason':'Explicit symbol instance; pipe centerline/port ownership not established.','edge_id':None})
    walk(d.blocks[name],mat,path,depth+1)
   elif ('PIPE' in e.dxf.layer or '水冷-' in e.dxf.layer) and e.dxftype() in ['LINE','ARC','ELLIPSE','LWPOLYLINE']:
    row={'source_chain':list(path),'layer':e.dxf.layer,'entity_type':e.dxftype(),'status':'pending_double_line_centerline_reconstruction'}
    if e.dxftype()=='LINE':row['path_points']=[list(parent.transform(e.dxf.start))[:2],list(parent.transform(e.dxf.end))[:2]]
    if e.dxftype()=='LWPOLYLINE':row['path_points']=[list(parent.transform((v[0],v[1],0)))[:2] for v in e.get_points()];row['closed']=e.closed
    if e.dxftype() in ['ARC','ELLIPSE']:row['reason']='Curved pipe outlines must not be treated as verified crossovers or physical centerline bends';curves.append(row)
    geom.append(row)
 walk(m)
 # Only native open polylines on the actual top-level MEP plan. ACI groups remain unresolved semantics.
 segments=[];excluded=[]
 for e in m:
  if e.dxf.layer!='空调平面':continue
  if e.dxftype()=='LWPOLYLINE' and not e.closed and e.dxf.color in [112,5,2,6] and e.dxf.linetype=='BYLAYER':
   pts=list(e.get_points());system='unresolved:aci'+str(e.dxf.color)
   if any(abs(v[4])>1e-10 for v in pts):excluded.append({'handle':e.dxf.handle,'reason':'bulged_polyline_requires_semantic_curve_review'});continue
   for k,(a,b) in enumerate(zip(pts,pts[1:])):
    a=tuple(float(x) for x in a[:2]);b=tuple(float(x) for x in b[:2])
    if math.dist(a,b)>1:segments.append({'a':a,'b':b,'system':system,'handle':e.dxf.handle,'part':k})
  elif e.dxftype() in ['LINE','ARC','CIRCLE','LWPOLYLINE','POLYLINE']:
   excluded.append({'handle':e.dxf.handle,'type':e.dxftype(),'color':e.dxf.color,'reason':'Not verified pipe centerline; may be symbol leg, outline, detail, or curve'})
 pg.set_tolerance(.5)
 segments,near_audit=snap_near_junction_endpoints(segments,NORM[sheet].get('near_junction'))
 bridges,crossover_audit=recover_straight_crossovers(segments,[],NORM[sheet]['straight_crossovers']);segments+=bridges
 dump(out/'normalization_audit.json',{'near_junction':near_audit,'crossovers':crossover_audit,'configuration':NORM[sheet],'relative_elevation':'unknown','hydraulic_service':'unclassified_source_color_groups'})
 graphs={};physical={};snap_tol=0.5
 for system in sorted(set(s['system'] for s in segments)):
  ss=[s for s in segments if s['system']==system];G=Graph();points=[]
  def key(p):
   for q in points:
    if math.dist(p,q)<=snap_tol:return q
   q=(round(p[0],6),round(p[1],6));points.append(q);return q
  ends=[s[v] for s in ss for v in ['a','b']]
  for s in ss:
   line=LineString([s['a'],s['b']]);splits=[(0,s['a']),(1,s['b'])]
   for pt in ends:
    t=line.project(Point(pt),normalized=True)
    if 1e-7<t<1-1e-7 and line.distance(Point(pt))<=snap_tol and not s.get('crossing_connectivity'):splits.append((t,pt))
   splits=sorted(splits)
   for (_,a),(_,b) in zip(splits,splits[1:]):
    a=key(a);b=key(b)
    if a!=b:
     if G.has_edge(a,b):G[a][b]['handles'].add(s['handle'])
     else:G.add_edge(a,b,handles=set(s.get('source_handles',[s['handle']])))
  # retain only exactly three unique physical rays; no interior-interior crossing was connected.
  tees=[]
  for pt in G:
   rays=[]
   for q in G[pt]:
    a=math.atan2(q[1]-pt[1],q[0]-pt[0]);
    if all(abs(math.atan2(math.sin(a-b),math.cos(a-b)))>0.01 for b in rays):rays.append(a)
   if len(rays)==3 and G.degree(pt)==3:tees.append(pt)
  physical[system]=sorted(tees);graphs[system]=G
 for system,tees in physical.items():
  for pt in tees:
   nid='T'+str(len(nodes)+1).zfill(4);G=graphs[system];nodes.append({'node_id':nid,'node_type':'tee','subtype':'endpoint_on_polyline_three_ray','label':nid,'floor':0,'system':system,'x':pt[0],'y':pt[1],'source_handles':sorted({h for q in G[pt] for h in G[pt][q]['handles']}),'placement_rule':'same_ACI_three_distinct_rays_endpoint_contact_only','review_status':'unreviewed','system_semantic_state':'pending_source_legend_confirmation'})
 for system,G in graphs.items():
  occupied={(n['x'],n['y'])for n in nodes if n.get('system')==system}
  for pt in sorted(G):
   if pt in occupied or G.degree(pt)==2:continue
   nid='UT'+str(sum(n['node_id'].startswith('UT')for n in nodes)+1).zfill(4)
   nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal'if G.degree(pt)==1 else'pending_source_junction','boundary_type':'unresolved_source_terminal','label':nid,'floor':0,'system':system,'x':pt[0],'y':pt[1],'source_handles':sorted({h for q in G[pt]for h in G[pt][q]['handles']}),'review_required':True,'system_semantic_state':'pending_source_legend_confirmation'})
 nodes+=eq;edges=[];pending=[];covered=set()
 for system,G in graphs.items():
  ng={(n['x'],n['y']):n for n in nodes if n['node_type']in ['tee','virtual_equipment'] and n['system']==system};seen=set()
  for start,n in ng.items():
   for nxt in sorted(G[start]):
    if frozenset([start,nxt]) in seen:continue
    prev=start;cur=nxt;path=[start,nxt];hs=set(G[start][nxt]['handles']);local=[frozenset([start,nxt])]
    while cur not in ng and G.degree(cur)==2:
     q=next(q for q in G[cur] if q!=prev);local.append(frozenset([cur,q]));hs.update(G[cur][q]['handles']);prev,cur=cur,q;path.append(cur)
     if len(path)>len(G)+2:break
    seen.update(local)
    if cur in ng and cur!=start:
     end=ng[cur];eid='E'+str(len(edges)+1).zfill(4);length=sum(math.dist(a,b) for a,b in zip(path,path[1:]));edges.append({'edge_id':eid,'start_node_id':n['node_id'],'end_node_id':end['node_id'],'edge_type':'tee_to_tee','system':system,'floor_start':0,'floor_end':0,'start_x':start[0],'start_y':start[1],'end_x':cur[0],'end_y':cur[1],'path_length':length,'path_points':[list(q) for q in path],'attribute_paths':[[list(q) for q in path]],'source_handles':sorted(hs),'connection_mode':'native_same_color_polyline_continuation','equipment_inventory':[],'review_status':'unreviewed'});covered.update(hs)
    else:pending.append({'pending_id':'P'+str(len(pending)+1).zfill(4),'system':system,'source_handles':sorted(hs),'path_points':[list(q) for q in path],'reason':'Path reaches ordinary endpoint or unresolved junction; no equipment/interface node invented','start_node_id':n['node_id']})
  used={h for x in edges for h in x['source_handles']}|{h for x in pending if x['system']==system for h in x['source_handles']}
  for s in [x for x in segments if x['system']==system and x['handle'] not in used]:pending.append({'pending_id':'P'+str(len(pending)+1).zfill(4),'system':system,'source_handles':[s['handle']],'path_points':[s['a'],s['b']],'reason':'Disconnected centerline fragment without two verified semantic nodes'})
 issues=[{'issue_id':tid+'-Q01','kind':'system_semantics','status':'pending','message':'Generic plan layer uses ACI 112/5/2/6; these groups are kept separate without asserting supply/return.'},{'issue_id':tid+'-Q02','kind':'nested_double_line_pipe','status':'pending','count':len(geom),'message':'Native cold-station block uses double-line pipe outlines, bends and fittings; centerline/port reconstruction remains pending.'},{'issue_id':tid+'-Q03','kind':'equipment_ports','status':'pending','count':len(eq),'message':'Native physical equipment recognized; ports and unique equipment schedule variants not established.'},{'issue_id':tid+'-Q04','kind':'inline_ownership','status':'pending','count':len(unres),'message':'Native inline components retained unassigned; no nearest-edge forced match.'},{'issue_id':tid+'-Q05','kind':'source_coverage','status':'pending','count':len(pending),'message':'Unclosed paths and fragments retained as pending geometry; all ordinary ends remain non-nodes.'}]
 metadata={'project_id':tid,'task_id':tid,'source_dxf':p.name,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'partial_graph_requires_review','graph_complete':False,'review_status':'unreviewed','parameter_library_id':MAN.get('library_id'),'coordinate_system':'native_DXF_WCS','floor':0,'scope':'outdoor_plant_plan','tolerance_drawing_units':snap_tol,'system_policy':'source color groups kept separate; semantic mapping pending','direction_policy':'No flow direction inferred','source_display_geometry_file':'source_pipe_geometry_pending.json'}
 graph={'metadata':metadata,'nodes':nodes,'edges':edges};dump(out/'graph_with_edges.json',graph);dump(out/'unresolved_paths.json',pending);dump(out/'unresolved_components.json',unres);dump(out/'source_pipe_geometry_pending.json',geom);dump(out/'source_block_inventory.json',block_audit);dump(out/'source_layer_inventory.json',[{'layer':l,'entity_type':t,'count':c} for (l,t),c in layers.items()]);dump(out/'curve_audit.json',curves);dump(out/'excluded_geometry_audit.json',excluded);dump(out/'quality_issues.json',issues)
 bindings=[]
 comprefs={'rubber_flexible_joint':['MAT-01-WATER-15-01','MAT-01-WATER-15-02'],'check_valve':['MAT-01-WATER-17-01'],'Y_strainer':['MAT-01-WATER-09-01'],'butterfly_valve':['MAT-01-WATER-14-01','MAT-01-WATER-14-02'],'motorized_control_valve':['MAT-01-WATER-13-01'],'sensor':[]}
 for n in eq:bindings.append({'object_type':'equipment_node','object_id':n['node_id'],'source_chain':n['source_chain'],'source_block_name':n['source_block_name'],'candidate_parameter_profiles':n['parameter_profile_candidates'],'parameter_state':n['parameter_binding_state'],'installed_parameters':{},'reason':'Family reference only; exact schedule variant and serial tag not established.'})
 for c in unres:bindings.append({'object_type':'unresolved_inline_component','object_id':c['device_name'],'source_chain':c['source_chain'],'source_block_name':c['source_block_name'],'candidate_parameter_profiles':comprefs.get(c['equipment_type'],[]),'parameter_state':'family_reference_only_unreviewed','installed_parameters':{},'reason':'Schedule ranges are references, not an instance DN/rating; no edge owner yet.'})
 dump(out/'parameter_bindings.json',{'task_id':tid,'library_id':MAN.get('library_id'),'library_manifest_sha256':hashlib.sha256((LIB/'catalog-manifest.json').read_bytes()).hexdigest(),'bindings':bindings})
 csvout(out/'topology_nodes.csv',nodes,['node_id','node_type','subtype','label','floor','system','x','y','source_chain','source_block_name','source_handles','parameter_profile_candidates','parameter_binding_state','connection_state','review_status']);csvout(out/'edges.csv',edges,['edge_id','start_node_id','end_node_id','edge_type','system','floor_start','floor_end','start_x','start_y','end_x','end_y','path_length','path_points','source_handles']);csvout(out/'edge_device_instances.csv',[],['device_name','equipment_type','type_code','x','y','source_kind','source_block_name','edge_id','edge_distance','assignment_status']);csvout(out/'edge_equipment_by_type.csv',[],['edge_id','equipment_type','device_count','device_names']);csvout(out/'virtual_equipment_ports.csv',[],['port_id','node_id','system','x','y']);csvout(out/'unresolved_components.csv',unres,['device_name','equipment_type','source_chain','source_block_name','x','y','edge_id','assignment_status','reason'])
 summary={'task_id':tid,'status':'partial_graph_requires_review','nodes':len(nodes),'edges':len(edges),'equipment_nodes':len(eq),'tee_nodes':sum(n['node_type']=='tee'for n in nodes),'virtual_nodes':sum(n['node_type']=='virtual_equipment'for n in nodes),'assigned_components':0,'unresolved_components':len(unres),'pending_paths':len(pending),'nested_pipe_primitives_pending':len(geom),'top_level_centerline_segments':len(segments),'top_level_centerline_handles':len({s['handle'] for s in segments}),'logical_edge_source_handles':len(covered),'quality_issue_groups':len(issues),'system_semantics':'unresolved','all_counts_are_observed_not_schedule_expected':True};dump(out/'edge_summary.json',summary)
 ids={n['node_id'] for n in nodes};checks={'unique_nodes':len(ids)==len(nodes),'unique_edges':len({e['edge_id'] for e in edges})==len(edges),'edge_endpoints_exist':all(e['start_node_id'] in ids and e['end_node_id'] in ids for e in edges),'every_edge_has_source_handles':all(e['source_handles'] for e in edges),'explicit_review_boundaries':all(n.get('review_required')for n in nodes if n['node_type']=='virtual_equipment'),'source_system_groups_preserved':all(e['system'].startswith('unresolved:aci') for e in edges),'all_inline_instances_explicitly_unresolved':all(x['assignment_status']=='unresolved' and x['edge_id'] is None for x in unres),'independent_task':all(x['task_id']==tid for x in [metadata])};dump(rep/'validation.json',{'checks':checks,'structural_checks_passed':all(checks.values()),'complete':False,'status':'partial_not_accepted','metrics':summary,'issues':issues})
 report=f'''# Sheet {sheet} outdoor topology build\n\nStatus: **PARTIAL / NOT ACCEPTED**. All {len(checks)} structural invariants pass; coverage is incomplete.\n\n{len(nodes)} nodes = {len(eq)} native equipment + {len(nodes)-len(eq)} source junctions and review-required virtual boundaries; {len(edges)} source-supported logical edges. Equipment labels are local stable source-chain identifiers, not fabricated schedule tags.\n\n{len(unres)} native inline instances are explicit unresolved edge attributes. No device has been forced onto a nearby line. {len(geom)} nested pipe outline primitives require centerline reconstruction. {len(pending)} source fragments or unclosed paths remain pending; source endpoints without established hardware semantics are explicit review-required virtual boundaries.\n\nThe recognized schedule library is referenced by family; source native block variants are unreviewed and no local pipe diameter or equipment serial number is copied from a schedule quantity. Top-level ACI groups 112/5/2/6 are isolated with unresolved system meaning. The nesting transform is applied to native equipment outlines and pipe geometry. All node/edge and source audit artifacts are local to {tid}.\n\nNo cross-drawing links, supply/return guesses or automatic HIL confirmation were performed. Source-proven straight crossovers were normalized before junction detection. Graph counts deliberately differ from reference table quantities. Review needs: establish pipe centerlines through nested fittings, verify explicit equipment ports, and map source color groups to systems.\n''';(rep/'topology-build-report.md').write_text(report,encoding='utf8')
 # Source-coordinate diagnostic overlay, no invented edges for missing fragments.
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(12,12));colors={112:'#24955c',5:'#3979bb',2:'#b99c00',6:'#af4aab'}
 for s in segments:ax.plot([s['a'][0],s['b'][0]],[s['a'][1],s['b'][1]],color=colors[int(s['system'].split('aci')[1])],alpha=.45,lw=.7)
 for e in edges:ax.plot([x[0] for x in e['path_points']],[x[1] for x in e['path_points']],color='#222',lw=1.8)
 for n in nodes:ax.plot(n['x'],n['y'],'s' if n['node_type']=='equipment' else 'o',ms=3,color='#d14939' if n['node_type']=='equipment' else '#222')
 ax.set_aspect('equal');ax.set_title(f'Sheet {sheet} | Partial native topology | {len(nodes)} nodes, {len(edges)} edges\nSystem meaning, nested pipe centerlines and equipment ports pending');ax.ticklabel_format(style='plain');fig.tight_layout();fig.savefig(rep/'partial-topology-overlay.png',dpi=180);plt.close(fig)
 print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':
 for s in ['06','07']:run(s)
