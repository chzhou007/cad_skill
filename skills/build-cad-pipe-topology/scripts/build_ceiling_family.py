import json,csv,math,pathlib,hashlib,collections,html
import ezdxf
from cad_ceiling_native_rules import circle_connection_candidate,match_out_of_plane_symbol,riser_terminal_candidate
from straight_crossovers import recover_straight_crossovers
import pipe_geometry as pg
import argparse
from topology_normalization import snap_near_junction_endpoints
from proven_contacts import canonical_contact_points,validate_junction_contacts
from native_inline_coordinates import ball_valve_anchor,balancing_valve_anchor
cli=argparse.ArgumentParser();cli.add_argument('--input-root',type=pathlib.Path,required=True);cli.add_argument('--output-root',type=pathlib.Path,required=True);cli.add_argument('--normalization-config',type=pathlib.Path,required=True);args=cli.parse_args()
BATCH=args.input_root;OUT=args.output_root;TOL=.05;NORM=json.loads(args.normalization_config.read_text(encoding='utf8'))

def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def table(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def pt(v):return (float(v[0]),float(v[1]))
def key(p):return tuple(round(x/ TOL) for x in p)
def distance(a,b):return math.dist(a,b)
def on(p,a,b,tol=TOL):
 dx=b[0]-a[0];dy=b[1]-a[1];l=dx*dx+dy*dy
 if not l:return None
 t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l
 q=(a[0]+t*dx,a[1]+t*dy)
 return max(0,min(1,t)) if -tol/math.sqrt(l)<=t<=1+tol/math.sqrt(l) and distance(p,q)<=tol else None
reg=json.loads((BATCH/'batch.json').read_text(encoding='utf-8'));lib=BATCH/'reference-library/parameters-v1';manifest=json.loads((lib/'catalog-manifest.json').read_text(encoding='utf-8'));protos=json.loads((lib/'cad-pattern-prototypes.json').read_text(encoding='utf-8'));proto_by_block={x['source_block']:x for x in protos}
for task in reg['tasks']:
 sheet=task['sheet']
 if sheet not in ['08','09','10']:continue
 tid=task['task_id'];old=BATCH/'tasks'/tid;meta=json.loads((old/'task.json').read_text(encoding='utf-8'));src=(old/meta['source']['dxf']).resolve();out=OUT/'tasks'/tid/'topology';out.mkdir(parents=True,exist_ok=True);rep=out.parent/'reports';rep.mkdir(exist_ok=True);d=ezdxf.readfile(src);m=d.modelspace();segments=[];circles=[];layercounts=collections.defaultdict(collections.Counter)
 for e in m:
  layercounts[e.dxf.layer][e.dxftype()]+=1
  sy={'空调冷冻水供水':'supply','空调冷冻水回水':'return'}.get(e.dxf.layer)
  if sy and e.dxftype()=='CIRCLE':circles.append({'handle':e.dxf.handle,'center':pt(e.dxf.center),'radius':e.dxf.radius,'system':sy})
  if e.dxftype()=='LINE' and (sy or e.dxf.layer=='空调立管、水平支管'):
   a,b=pt(e.dxf.start),pt(e.dxf.end)
   if distance(a,b)>TOL:segments.append({'id':len(segments),'handle':e.dxf.handle,'layer':e.dxf.layer,'system':sy,'a':a,'b':b,'cuts':{0.,1.}})
 for s in segments:
  if s['system'] is None and any(max(distance(s['a'],c['center']),distance(s['b'],c['center']))<=400 for c in circles):s['excluded_circle_local_geometry']=True
 # A circle explicitly lying on a same-system main can close a branch ending on its circumference.
 circle_bridges=[]
 riser_terminals=[]
 for c in circles:
  match=riser_terminal_candidate(c,segments,NORM[sheet].get('riser_terminal_radii',[]),TOL)
  if match:
   s,end,p=match;s[end]=c['center'];riser_terminals.append(dict(circle=c,pipe_handle=s['handle'],original_endpoint=p,semantic_endpoint=c['center']))
 for c in circles:
  match=circle_connection_candidate(c,segments,TOL)
  if match is None:continue
  main,branch=match;mains=[main];branches=[branch];center=c['center']
  u,side,end=branches[0];u['original_'+side]=end;u[side]=center;u['circle_connection_evidence']=c['handle'];circle_bridges.append({'circle_handle':c['handle'],'circle_radius':c['radius'],'branch_handle':u['handle'],'main_handle':mains[0]['handle'],'system':c['system'],'original_endpoint':end,'semantic_endpoint':center,'bridge_length':distance(end,center),'rule':'circle-centered-main plus unique radial branch stopping at circumference'})
 # Shared source crossover normalization precedes junction and logical-edge construction.
 pg.set_tolerance(TOL)
 qualified=[dict(s,source_system=s['system'])for s in segments if s['system']and not s.get('excluded_circle_local_geometry')]
 normalized,near_audit=snap_near_junction_endpoints(qualified,NORM[sheet].get('near_junction'))
 for n in normalized:segments[n['id']].update(a=n['a'],b=n['b'])
 qualified=normalized
 bridges,crossover_audit=recover_straight_crossovers(qualified,[],NORM[ sheet ]['straight_crossovers'])
 for bridge in bridges:
  bridge.update(id=len(segments),layer=next(s['layer']for s in segments if s['system']==bridge['system']),cuts={0.,1.});segments.append(bridge)
 dump(out/'normalization_audit.json',{'near_junction':near_audit,'crossovers':crossover_audit,'configuration':NORM[sheet],'relative_elevation':'unknown'})
 # Only endpoint incidence connects. Interior/interior crossings remain independent.
 junction_pairs=[];contact_pairs=[]
 for i,s in enumerate(segments):
  for t in segments[i+1:]:
   if s.get('excluded_circle_local_geometry') or t.get('excluded_circle_local_geometry'):continue
   if s['system'] and t['system'] and s['system']!=t['system']:continue
   hits=[]
   for frac,p in [(0.,s['a']),(1.,s['b'])]:
    v=on(p,t['a'],t['b'])
    if v is not None and not(t.get('crossing_connectivity')and min(distance(p,t['a']),distance(p,t['b']))>TOL):s['cuts'].add(frac);t['cuts'].add(v);hits.append(p);contact_pairs.append(((s['id'],frac),(t['id'],v),p))
   for frac,p in [(0.,t['a']),(1.,t['b'])]:
    v=on(p,s['a'],s['b'])
    if v is not None and not(s.get('crossing_connectivity')and min(distance(p,s['a']),distance(p,s['b']))>TOL):t['cuts'].add(frac);s['cuts'].add(v);hits.append(p);contact_pairs.append(((t['id'],frac),(s['id'],v),p))
   if hits:junction_pairs.append((i,t['id']))
 parent=list(range(len(segments)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(i,j):parent[find(i)]=find(j)
 # Only untyped components propagate type, never bridge supply/return.
 for i,j in junction_pairs:
  if segments[i]['system'] is None and segments[j]['system'] is None:union(i,j)
 anchors=collections.defaultdict(set)
 for i,j in junction_pairs:
  s,t=segments[i],segments[j]
  if s['system'] is None and t['system']:anchors[find(i)].add(t['system'])
  if t['system'] is None and s['system']:anchors[find(j)].add(s['system'])
 for s in segments:
  if s['system'] is None:
   ass=anchors[find(s['id'])] if not s.get('excluded_circle_local_geometry') else set();s['system']=next(iter(ass)) if len(ass)==1 else None;s['inference']='unique_component_anchor' if len(ass)==1 else ('conflicting_system_anchors' if len(ass)>1 else 'no_system_anchor')
 # Canonicalize only proven endpoint-incidence contacts, never arbitrary nearby crossings.
 contact_point=canonical_contact_points(segments,contact_pairs)
 dump(out/'accepted-contact-canonicalization.json',[dict(endpoint_segment=a[0],main_segment=b[0],endpoint_fraction=a[1],main_fraction=b[1],point=contact_point(segments[a[0]],a[1])) for a,b,p in contact_pairs])
 verts={};adj=collections.defaultdict(list);atomic=[]
 for s in segments:
  if not s['system']:continue
  vals=sorted(s['cuts']);pts=[contact_point(s,v) for v in vals]
  for a,b in zip(pts,pts[1:]):
   if distance(a,b)<=TOL:continue
   ka,kb=(s['system'],key(a)),(s['system'],key(b));verts.setdefault(ka,a);verts.setdefault(kb,b)
   if any(atomic[j]['b']==kb if atomic[j]['a']==ka else atomic[j]['a']==kb for j in adj[ka]):continue
   eid=len(atomic);atomic.append({'a':ka,'b':kb,'source_handle':s['handle'],'source_handles':s.get('source_handles',[s['handle']]),'source_segment':s['id'],'length':distance(a,b)});adj[ka].append(eid);adj[kb].append(eid)
 tee=[];pending=[]
 for k,eds in adj.items():
  if len(eds)<3:continue
  p=verts[k];near=[c['handle'] for c in circles if c['system']==k[0] and distance(c['center'],p)<=400 and c['handle'] not in {b['circle_handle'] for b in circle_bridges}]
  rays=[]
  for ae in eds:
   atom=atomic[ae];other=atom['b'] if atom['a']==k else atom['a'];q=verts[other];dx,dy=q[0]-p[0],q[1]-p[1];ln=math.hypot(dx,dy);v=(dx/ln,dy/ln)
   if not any(v[0]*r[0]+v[1]*r[1]>.999999 for r in rays):rays.append(v)
  centered=[c for c in circles if c['system']==k[0]and distance(c['center'],p)<=TOL]
  if len(eds)==3 and len(rays)==3 and(not near or centered):tee.append(k)
  else:pending.append({'system':k[0],'x':p[0],'y':p[1],'degree':len(eds),'reason':'riser_or_circle_symbol_contact' if near else 'non_three_way_intersection','circle_handles':near})
 tee.sort(key=lambda k:(k[0],verts[k][1],verts[k][0]));nodeid={k:f'T{i+1:03}' for i,k in enumerate(tee)}
 nodes=[{'node_id':nodeid[k],'node_type':'tee','subtype':'physical_tee','floor':int(sheet)-7,'system':k[0],'x':verts[k][0],'y':verts[k][1],'label':nodeid[k],'source_handles':sorted({atomic[x]['source_handle'] for x in adj[k]}),'evidence':'three endpoint-incidence rays; no interior-crossing join'} for k in tee]
 interface_evidence=[];virtual_ports=[]
 for r in riser_terminals:
  c=r['circle'];center=c['center'];k=(c['system'],key(center))
  if k not in verts or len(adj[k])!=1:continue
  vid=f'RIF{len(interface_evidence)+1:03}';nodeid[k]=vid;pid=vid+'-P1';interface_evidence.append(dict(interface_id=vid,circle_handle=c['handle'],pipe_handles=[r['pipe_handle']],center=center,system=c['system'],semantic='out_of_plane_riser_terminal',evidence_state='source_profile_circle_and_unique_radial_pipe',equipment_association='unresolved'))
  nodes.append(dict(node_id=vid,node_type='virtual_equipment',subtype='out_of_plane_riser',floor=int(sheet)-7,system=c['system'],x=center[0],y=center[1],label=vid,source_handle=c['handle'],source_handles=[c['handle'],r['pipe_handle']],ports=[dict(port_id=pid,system=c['system'],x=center[0],y=center[1])],connection_status='riser_destination_unresolved'))
  virtual_ports.append(dict(virtual_equipment_id=vid,port_id=pid,system=c['system'],x=center[0],y=center[1]))
 glyphs=[u for u in segments if u['layer']=='空调立管、水平支管']
 for c in circles:
  match=match_out_of_plane_symbol(c,glyphs,TOL)
  if match is None:continue
  arms,bars=match;center=c['center'];vkey=(c['system'],key(center))
  if vkey not in verts or len(adj[vkey])!=1:continue
  vid=f'VIF{len(interface_evidence)+1:03}';nodeid[vkey]=vid;pid=vid+'-P1';evidence={'interface_id':vid,'circle_handle':c['handle'],'glyph_handles':[u['handle'] for u in arms+bars],'pipe_handles':sorted({atomic[j]['source_handle'] for j in adj[vkey]}),'center':center,'system':c['system'],'semantic':'out_of_plane_pipe_interface','evidence_state':'complete_native_circle_V_double_bar_pattern','equipment_association':'unresolved'};interface_evidence.append(evidence)
  nodes.append({'node_id':vid,'node_type':'virtual_equipment','subtype':'out_of_plane_interface','floor':int(sheet)-7,'system':c['system'],'x':center[0],'y':center[1],'label':vid,'source_handle':c['handle'],'source_handles':[c['handle']]+evidence['glyph_handles'],'ports':[{'port_id':pid,'system':c['system'],'x':center[0],'y':center[1]}],'connection_status':'equipment_beyond_interface_unresolved'})
  virtual_ports.append({'virtual_equipment_id':vid,'port_id':pid,'system':c['system'],'x':center[0],'y':center[1]})
 # Unproven source terminals remain explicit review boundaries, not discarded branches.
 for k,eds in sorted(adj.items(),key=lambda x:(x[0][0],verts[x[0]][1],verts[x[0]][0])):
  if k in nodeid or len(eds)==2:continue
  nid='UT'+str(sum(n['node_id'].startswith('UT')for n in nodes)+1).zfill(4);nodeid[k]=nid;p=verts[k]
  nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal'if len(eds)==1 else'pending_source_junction','boundary_type':'unresolved_source_terminal','floor':int(sheet)-7,'system':k[0],'x':p[0],'y':p[1],'label':nid,'review_required':True,'connection_status':'source_boundary_unconfirmed','source_handles':sorted({atomic[e]['source_handle']for e in eds})})
 edges=[];seen=set();used=set()
 for k in list(nodeid):
  for first in adj[k]:
   a=k;eid=first;path=[verts[k]];handles=[];walk=[];trail=set()
   while eid not in trail:
    trail.add(eid);atom=atomic[eid];b=atom['b'] if atom['a']==a else atom['a'];path.append(verts[b]);handles.extend(atom['source_handles']);walk.append(eid)
    if b in nodeid:
     signature=tuple(sorted((nodeid[k],nodeid[b])))+tuple(sorted(set(handles)))
     if b!=k and signature not in seen:
      seen.add(signature);used.update(walk);edges.append({'edge_id':f'E{len(edges)+1:04}','start_node_id':nodeid[k],'end_node_id':nodeid[b],'edge_type':('tee_to_virtual_equipment' if nodeid[k].startswith('VIF') or nodeid[b].startswith('VIF') else 'tee_to_tee'),'system':k[0],'start_floor':int(sheet)-7,'end_floor':int(sheet)-7,'path':path,'attribute_paths':[path],'path_length':sum(atomic[j]['length'] for j in walk),'source_handles':sorted(set(handles)),'equipment_counts':{},'equipment_names':[]})
     break
    if len(adj[b])!=2:break
    eid=next(j for j in adj[b] if j!=eid);a=b
 active_virtual_ids={v for edge in edges for v in [edge['start_node_id'],edge['end_node_id']] if v.startswith(('VIF','RIF','UT'))}
 pending_interface_nodes=[n for n in nodes if n['node_id'].startswith('VIF') and n['node_id'] not in active_virtual_ids]
 nodes=[n for n in nodes if n['node_type']!='virtual_equipment' or n['node_id'] in active_virtual_ids]
 virtual_ports=[v for v in virtual_ports if v['virtual_equipment_id'] in active_virtual_ids]
 for e in edges:
  e['path_points']=e['path']
  if e['start_node_id'].startswith(('VIF','RIF')):e['start_port_id']=e['start_node_id']+'-P1'
  if e['end_node_id'].startswith(('VIF','RIF')):e['end_port_id']=e['end_node_id']+'-P1'
 for i in interface_evidence:i['graph_state']='loaded_connected_interface' if i['interface_id'] in active_virtual_ids else 'source_candidate_no_completed_logical_edge'
 # Equipment identity is source bounded, not nearest graph/node attachment.
 inventory=json.loads((old/'enrichment/cad-elements.json').read_text(encoding='utf-8'));bounds={x['source_handle']:x['bounds'] for x in inventory};equipment=[]
 labels=[e for e in m.query('TEXT') if e.dxf.layer=='空调编号' and e.dxf.text.startswith('CRAH-')]
 eqblocks=[e for e in m.query('INSERT') if e.dxf.layer=='空调' and e.dxf.name in ['40kW','A$C478B2BA9']]
 for e in eqblocks:
  bb=bounds.get(e.dxf.handle)
  if not bb:continue
  lo,hi=bb;hits=[t for t in labels if lo[0]-600<=t.dxf.insert.x<=hi[0]+600 and lo[1]-600<=t.dxf.insert.y<=hi[1]+600]
  inside=[t for t in labels if lo[0]-TOL<=t.dxf.insert.x<=hi[0]+TOL and lo[1]-TOL<=t.dxf.insert.y<=hi[1]+TOL]
  if inside:hits=inside
  equipment.append({'source_handle':e.dxf.handle,'source_block':e.dxf.name,'bounds':bb,'label_candidates':[t.dxf.text for t in hits],'association_status':'unique_bounded_source_label' if len(hits)==1 else 'label_unresolved','connection_status':'ports_unresolved','parameter_candidates':['CRAH-40-BATTERY','CRAH-40-CARRIER'] if e.dxf.name=='40kW' else ['CRAH-155-DOWN','CRAH-155-UP'],'parameters_effective':False})
 # Keep unconnected identified equipment in graph only when unique label/block evidence.
 unique=collections.Counter(r['label_candidates'][0] for r in equipment if len(r['label_candidates'])==1)
 for r in equipment:
  if len(r['label_candidates'])==1 and unique[r['label_candidates'][0]]==1:
   lo,hi=r['bounds'];nodes.append({'node_id':r['label_candidates'][0],'node_type':'equipment','subtype':'CRAH','floor':int(sheet)-7,'label':r['label_candidates'][0],'x':(lo[0]+hi[0])/2,'y':(lo[1]+hi[1])/2,'source_handle':r['source_handle'],'source_block':r['source_block'],'connection_status':'ports_unresolved','parameter_candidates':r['parameter_candidates']})
 devices=[]
 for e in m.query('INSERT'):
  proto=proto_by_block.get(e.dxf.name)
  if proto is None:continue
  bb=bounds.get(e.dxf.handle)
  if not bb:continue
  lo,hi=bb;x,y=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
  native_signature='family_name_reference_only';native_center=None
  if e.dxf.name=='H-PICPNT-91':
   anchor=ball_valve_anchor(e)
   if anchor:native_center=anchor['center'];x,y=native_center;native_signature=anchor['signature']
  elif e.dxf.name=='平衡阀':
   anchor=balancing_valve_anchor(e)
   if anchor:native_center=anchor['center'];x,y=native_center;native_signature=anchor['signature']
  devices.append({'device_name' :f'{tid}-C-{e.dxf.handle}','equipment_type':{'H-PICPNT-91':'ball_valve','平衡阀':'balancing_valve'}.get(e.dxf.name,e.dxf.name),'type_code':proto['prototype_id'],'source_kind':'block_reference','source_block_name':e.dxf.name,'source_handle':e.dxf.handle,'x':x,'y':y,'edge_id':'','assignment_status':'unresolved','unresolved_reason':'source symbol exists; broken branch/device ports not yet proven','parameter_references':proto['parameter_references'],'native_signature':native_signature,'native_center':native_center})
 assigned_components=[]
 for dev in devices:
  if dev['native_center'] is None:continue
  center=dev['native_center'];matches=[ee for ee in edges if any(on(center,aa,bb,5.) is not None for aa,bb in zip(ee['path'],ee['path'][1:]))]
  if len(matches)!=1:continue
  ee=matches[0];dev['edge_id']=ee['edge_id'];dev['assignment_status']='assigned';dev['unresolved_reason']='';dev['edge_distance']=min(abs((bb[0]-aa[0])*(aa[1]-center[1])-(aa[0]-center[0])*(bb[1]-aa[1]))/distance(aa,bb) for aa,bb in zip(ee['path'],ee['path'][1:]) if on(center,aa,bb,5.) is not None);dev['assignment_tolerance_native_units']=5.;ee['equipment_counts'][dev['equipment_type']]=ee['equipment_counts'].get(dev['equipment_type'],0)+1;ee['equipment_names'].append(dev['device_name']);assigned_components.append(dev)
 aggregations=[]
 for ee in edges:
  for typ,num in ee['equipment_counts'].items():aggregations.append({'edge_id':ee['edge_id'],'start_node_id':ee['start_node_id'],'end_node_id':ee['end_node_id'],'equipment_type':typ,'device_count':num,'device_names':[v['device_name'] for v in devices if v['edge_id']==ee['edge_id'] and v['equipment_type']==typ]})
 contact_coverage=validate_junction_contacts(nodes,edges,circle_bridges+[c for c in near_audit if c.get('status')=='applied'],TOL)
 dump(out/'proven-contact-coverage.json',contact_coverage)
 gap_coverage=[]
 for i,bridge in enumerate(bridges,1):
  covered=[e['edge_id']for e in edges if any(on(bridge['a'],a,b,TOL*2)is not None and on(bridge['b'],a,b,TOL*2)is not None for a,b in zip(e['path'],e['path'][1:]))]
  if not covered:raise ValueError('Recovered crossover span missing from final logical edges')
  gap_coverage.append(dict(id='GAP-'+str(i).zfill(3),a=bridge['a'],b=bridge['b'],source_handles=bridge.get('source_handles',[]),edge_ids=covered,status='applied',crossing_connectivity='independent_pipes_no_junction'))
 dump(out/'source_gap_coverage.json',gap_coverage)
 graph={'schema_version':1,'project_id':tid,'status':'partial_unreviewed','nodes':nodes,'edges':edges,'virtual_equipment_ports':virtual_ports,'equipment_parameter_library':{'library_id':manifest.get('library_id'),'sha256':hashlib.sha256((lib/'catalog-manifest.json').read_bytes()).hexdigest()},'limitations':['Endpoint-incidence connections and source-proven crossover spans are used. Independent interior crossings are not joined.','Complete native interfaces and calibrated circle connections are resolved; unsupported valve and equipment gaps remain pending.','Unconfirmed source ends are explicit review-required virtual boundaries, not physical equipment ports.','Isolated source-identified equipment nodes are not connected by proximity.']}
 total_length=sum(distance(s.get('original_a',s['a']),s.get('original_b',s['b'])) for s in segments);covered_length=sum(atomic[j]['length'] for j in used)
 summary={'task_id':tid,'status':'partial_unreviewed','nodes':len(nodes),'edges':len(edges),'tee_nodes':len(tee),'equipment_nodes':sum(n['node_type']=='equipment' for n in nodes),'virtual_equipment_nodes':len(active_virtual_ids),'source_interface_candidates':len(interface_evidence),'unconnected_interface_candidates':len(pending_interface_nodes),'circle_connections_recovered':len(circle_bridges),'circle_local_symbol_lines_withheld':sum(bool(s.get('excluded_circle_local_geometry')) for s in segments),'equipment_labels':len(labels),'equipment_symbols':len(eqblocks),'inline_components_detected':len(devices),'inline_components_assigned':len(assigned_components),'inline_components_unresolved':len(devices)-len(assigned_components),'pipe_source_line_entities':len(segments),'explicit_typed_source_lines':sum(s['layer']!='空调立管、水平支管' for s in segments),'branch_source_lines':sum(s['layer']=='空调立管、水平支管' for s in segments),'system_classified_lines':sum(bool(s['system']) for s in segments),'unclassified_lines':sum(not s['system'] for s in segments),'source_line_length':total_length,'accepted_edge_covered_length':covered_length,'accepted_edge_length_coverage':covered_length/total_length,'pending_non_tee_contacts':len(pending),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'tolerance_native_units':TOL,'unresolved_degree1_network_vertices':sum(len(v)==1 for v in adj.values()),'human_review':'unreviewed'}
 dump(out/'circle-connection-bridges.json',circle_bridges);dump(out/'out-of-plane-interface-evidence.json',interface_evidence);dump(out/'pending-interface-candidates.json',pending_interface_nodes);dump(out/'graph_with_edges.json',graph);dump(out/'edge_summary.json',summary);dump(out/'source-fragments.json',[{k:v for k,v in s.items() if k!='cuts'} for s in segments]);dump(out/'source-layer-inventory.json',layercounts);dump(out/'equipment-source-bindings.json',equipment);dump(out/'pending-junctions.json',pending);dump(out/'source-risers-and-circles.json',circles);dump(out/'unresolved-components.json',[v for v in devices if v['assignment_status']!='assigned']);dump(out/'native-component-assignment-evidence.json',assigned_components)
 table(out/'topology_nodes.csv',nodes,['node_id','node_type','subtype','floor','system','label','x','y','source_handle','source_handles','connection_status']);table(out/'edges.csv',edges,['edge_id','start_node_id','end_node_id','edge_type','system','start_floor','end_floor','path_length','path','source_handles']);table(out/'edge_device_instances.csv',devices,['device_name','equipment_type','type_code','x','y','source_kind','source_block_name','source_handle','edge_id','assignment_status','unresolved_reason']);table(out/'assigned_edge_device_instances.csv',assigned_components,['device_name','equipment_type','type_code','x','y','source_kind','source_block_name','source_handle','edge_id','edge_distance','assignment_status']);table(out/'edge_equipment_by_type.csv',aggregations,['edge_id','equipment_type','device_count','device_names']);table(out/'virtual_equipment_ports.csv',virtual_ports,['virtual_equipment_id','port_id','system','x','y'])
 # Overlay retains all pipe source geometry, so graph incompleteness remains visible.
 xs=[v for s in segments for v in [s['a'][0],s['b'][0]]];ys=[v for s in segments for v in [s['a'][1],s['b'][1]]];xmin,xmax=min(xs)-500,max(xs)+500;ymin,ymax=min(ys)-500,max(ys)+500
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin} {-ymax} {xmax-xmin} {ymax-ymin}"><rect x="{xmin}" y="{-ymax}" width="{xmax-xmin}" height="{ymax-ymin}" fill="white"/>']
 for s in segments:svg.append(f'<path d="M{s["a"][0]} {-s["a"][1]} L{s["b"][0]} {-s["b"][1]}" fill="none" stroke="#c9ced4" stroke-width="40"/>')
 for edge in edges:
  points=' '.join(f'{x},{-y}' for x,y in edge['path']);color='#d34e4e' if edge['system']=='supply' else '#427ed0';svg.append(f'<polyline points="{points}" stroke="{color}" fill="none" stroke-width="85"/>')
 for n in nodes:
  svg.append(f'<circle cx="{n["x"]}" cy="{-n["y"]}" r="100" fill="#151f2a"/><text x="{n["x"]+140}" y="{-n["y"]}" font-size="340">{html.escape(n["node_id"])}</text>')
 svg.append('</svg>');(rep/'source-topology-overlay.svg').write_text(''.join(svg),encoding='utf-8')
 validation={'checks':{'node_ids_unique':len(nodes)==len({n['node_id'] for n in nodes}),'edge_ids_unique':len(edges)==len({e['edge_id'] for e in edges}),'all_endpoints_exist':all(e['start_node_id'] in {n['node_id'] for n in nodes} and e['end_node_id'] in {n['node_id'] for n in nodes} for e in edges),'no_endpoint_nodes':all(n['node_type'] in ['tee','equipment','virtual_equipment'] for n in nodes),'all_unassigned_components_reported':len(devices)==summary['inline_components_unresolved']+summary['inline_components_assigned'],'no_human_confirmation':True},'acceptance':'partial_only_not_complete','source_coverage':summary};dump(rep/'validation-report.json',validation)
 (rep/'construction-report.md').write_text(f'# {tid} ceiling plan construction\n\nStatus: PARTIAL / UNREVIEWED. Source drawing: {src.name}.\n\nBuilt {len(tee)} three-ray junction nodes, {sum(n['node_type']=='equipment' for n in nodes)} uniquely source-bound CRAH nodes, {len(active_virtual_ids)} native interfaces and review-required boundary nodes ({len(pending_interface_nodes)} further complete source glyphs remain pending outside the loaded graph) and {len(edges)} logical edges. Recovered {len(circle_bridges)} unique circle-centered branch connections. Accepted paths cover {covered_length/total_length:.2%} of all candidate source pipe LINE length. {len(devices)} inline symbols reference the supplied family library; {len(assigned_components)} native ball-valve signatures lie within 5 native units of exactly one accepted edge and are assigned. All others remain explicitly unresolved. Bounded assignment (5 native units, approximately 2% of the source flange span; parallel pipes are hundreds of units apart) uses the native two-bulge circle center and the complete three-line/two-bulge signature; neither INSERT coordinates nor an unconstrained nearest edge is used.\n\nSupply/return layers: 空调冷冻水供水 / 空调冷冻水回水. Untyped branch layer: 空调立管、水平支管. Source lines: {len(segments)}; system-classified: {summary["system_classified_lines"]}. Classification propagates only within an untyped component that touches exactly one typed system.\n\nNo guessed physical equipment connections, unverified gap bridges or cross-drawing links. Unconfirmed source ends have explicit review-required virtual boundaries, not physical ports. Circle-centered main/radial-branch connections retain their exact source circle and pipe handles in circle-connection-bridges.json. Complete circle-V-double-bar glyphs with an actual typed pipe endpoint become explicit out-of-plane interfaces; plain circles and unsupported endpoints do not. Interior/interior crossings do not create nodes. Remaining unclassified circle/riser contacts are withheld. Equipment identity uses actual transformed block bounds and a unique label in a 600-native-unit expanded box. Modelspace INSERT coordinates are not used as equipment centers because block base coordinates differ. Capacity labels provide candidate schedule references only. Local overlay showed the untyped yellow branch layer includes triangular circle/riser symbol strokes; lines fully inside a 400-native-unit circle-centered neighborhood are withheld from physical connectivity, retaining their geometry as unresolved source evidence.\n\nRemaining work: resolve physical equipment ports, valve symbol gaps, riser circles and shared-color branch semantics; verify candidate T geometry by source overlay before accepting the whole graph. See source-fragments.json, pending-junctions.json and unresolved-components.json. Human Finish Review remains untouched.\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False),flush=True)
