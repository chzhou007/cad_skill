import pipe_geometry as pg_constants
"""Physical source-contact schematic graph with explicit system uncertainty.
Geometry continuity and hydraulic classification are audited separately.
"""
import argparse,json,csv,hashlib,re,collections,math
from pathlib import Path
from ezdxf import bbox
from pipe_geometry import *
from schematic_preprocess import prepare
from auxiliary_pipes import recover_inline_source_spans
from equipment_assemblies import *
from source_glyphs import exploded_flange_spans,source_cup_terminals
from instrumentation import measurement_assemblies,exploded_bowties,box_contact,symbol_pipe_contacts,symbol_display_handles,source_gauges,source_reference_regions,instrument_head_match
from straight_crossovers import recover_straight_crossovers
from source_fidelity import equipment_display,assembly_fidelity
from exploded_templates import recover_exploded_templates
from source_profile_templates import install_templates,validate_template_fills
from source_coverage_gate import source_coverage_gate
from topology_normalization import trim_elbow_overshoots,snap_near_junction_endpoints,exclude_paired_bar_display_tails

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def table(p,rows,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))or['status']
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(list,dict,tuple))else v for k,v in r.items()}for r in rows)
def segment_box_contact(a,b,bb):
 if point_bbox(a,bb)<=pg_constants.TOL or point_bbox(b,bb)<=pg_constants.TOL:return True
 cs=[(bb[0],bb[1]),(bb[2],bb[1]),(bb[2],bb[3]),(bb[0],bb[3])];return any(intersection(a,b,c,d)is not None for c,d in zip(cs,cs[1:]+cs[:1]))
def external_interface_candidates(doc,vertices,pieces,adj,config):
 found=[];audit=[]
 for rule in config.get('external_interfaces',[]):
  for text in doc.modelspace():
   if text.dxftype()not in ('TEXT','MTEXT'):continue
   value=text.plain_text()if text.dxftype()=='MTEXT'else text.dxf.text
   if not re.search(rule['text_regex'],value):continue
   box=bbox.extents([text]);bb=[box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y];height=float(text.dxf.height if text.dxftype()=='TEXT' else text.dxf.char_height);candidates=[]
   for leader in doc.modelspace().query('LINE'):
    if leader.dxf.layer not in rule['annotation_layers']:continue
    for near,tip in [(xy(leader.dxf.start),xy(leader.dxf.end)),(xy(leader.dxf.end),xy(leader.dxf.start))]:
     if point_bbox(near,bb)>max(height*2,pg_constants.TOL):continue
     terminals=[i for i,p in enumerate(vertices)if len(adj.get(('physical',i),[]))==1 and dist(p,tip)<=max(pg_constants.TOL,height*rule.get('max_tip_gap_text_heights',.15))]
     if len(terminals)==1:candidates.append((terminals[0],leader.dxf.handle,dist(vertices[terminals[0]],tip)))
   uniq={x[0]for x in candidates};row={'source_note_handle':text.dxf.handle,'source_note':value,'system':rule['system'],'candidate_vertices':sorted(uniq),'status':'recognized_explicit_interface_note_and_leader'if len(uniq)==1 else 'pending_ambiguous_or_missing_source_leader'}
   if len(uniq)==1:
    v=next(iter(uniq));row.update(source_leader_handles=sorted({h for vv,h,dd in candidates}),tip_to_terminal_distance=min(dd for vv,h,dd in candidates));found.append({'vertex':v,'system':rule['system'],'label':rule['label'],'evidence':row})
   audit.append(row)
 return found,audit

def build(args):
 cfg=json.loads(args.config.read_text(encoding='utf8'));set_tolerance(cfg.get('tolerance_native_units',.5));out=args.output_dir
 if out.exists()and(args.no_overwrite or(out/'graph_with_edges.json').exists()):raise ValueError('Select a fresh output directory; existing graphs are never overwritten')
 out.mkdir(parents=True,exist_ok=True);ns=prepare(args.dxf,args.bindings,args.profiles,cfg,out/'preprocessing');doc=ns['doc'];bindings=ns['bindings'];profiles=ns['profiles'];unknown=cfg.get('ambiguous_system','unclassified_water')
 # Existing resolved raw duplicates retain their audited classification. Unresolved
 # class changes remain physical evidence rather than silently cutting the pipe.
 segments=[];seen=set()
 for r in ns['segments']+ns['raw']:
  key=(r['handle'],tuple(round(z,5)for z in r['a']),tuple(round(z,5)for z in r['b']))
  if key in seen:continue
  seen.add(key);segments.append(dict(r,source_system=r['system']if r['system']!='pending'else unknown,system='physical'))
 segments,equipment_terminal_snaps=snap_native_equipment_terminals(doc,segments,cfg.get('native_equipment_terminal_snaps',[]));dump(out/'native_equipment_terminal_snaps.json',equipment_terminal_snaps)
 recovered_spans,span_audit=recover_inline_source_spans(segments,ns['symbols'],list(doc.modelspace()),cfg.get('inline_contact_fractions',{}));segments+=recovered_spans
 flange_spans,flange_audit=exploded_flange_spans(segments,list(doc.modelspace()),cfg.get('exploded_flange_layers',[]));segments+=flange_spans;span_audit+=flange_audit;dump(out/'physical_inline_span_audit.json',span_audit)
 ns['symbols']+=exploded_bowties(doc,cfg.get('exploded_valve_layers',[]))
 template_rules=install_templates(doc,cfg)
 recovered_templates=recover_exploded_templates(doc,cfg.get('exploded_template_blocks',[b for b in ['传感器','金属软连接']if b in cfg['inline_types']]),ns['symbols'],duplicate_tolerant_blocks=tuple(template_rules))
 recovered_templates,profile_template_audit=validate_template_fills(doc,recovered_templates,template_rules);dump(out/'profile_native_template_audit.json',profile_template_audit)
 ns['symbols']+=recovered_templates
 dump(out/'exploded_template_recognition.json',[{k:v for k,v in r.items()if k!='entity'}for r in recovered_templates])
 cfg['inline_types']['EXPLODED_ISOLATION_VALVE']=['Isolation Valve (subtype pending)','IV']
 materials=json.loads(args.materials.read_text(encoding='utf8'))if args.materials else []
 contours,contour_audit=material_contour_candidates(doc,materials,segments,cfg.get('material_equipment_rules',[]));contours_by_tag={c['binding']['equipment_tag']:c for c in contours};bindings=bindings+[c['binding']for c in contours];dump(out/'material_equipment_recognition.json',contour_audit)
 segments,package_audit=collapse_package_source_geometry(segments,contours,cfg.get('package_preserve_through_systems'));dump(out/'equipment_internal_source_geometry.json',package_audit)
 segments,instrument_groups,instrument_members=measurement_assemblies(doc,segments,ns['symbols'],cfg.get('instrumentation',{}));dump(out/'source_instrument_assemblies.json',instrument_groups)
 segments,elbow_trims=trim_elbow_overshoots(segments,cfg.get('elbow_overshoot'))
 segments,tail_exclusions=exclude_paired_bar_display_tails(segments,doc,cfg.get('paired_bar_display_tails'))
 segments,junction_snaps=snap_near_junction_endpoints(segments,cfg.get('near_junction'))
 dump(out/'straight_crossover_inputs.json',segments);gap_discovery=[]
 spans,straight_audit=recover_straight_crossovers(segments,ns['symbols'],cfg.get('straight_crossover_calibration'),discovery_audit=gap_discovery);segments+=spans;dump(out/'straight_crossover_audit.json',straight_audit);dump(out/'straight_crossover_discovery.json',gap_discovery)
 dump(out/'normalization_audit.json',{'elbow_overshoots':elbow_trims,'crossovers':straight_audit,'junction_snaps':junction_snaps,'display_tail_exclusions':tail_exclusions,'relative_elevation':'unknown','execution_stage':'before_source_junction_and_edge_extraction'})
 vs,ps,ad=build_network(segments);systems_by_handle=collections.defaultdict(set)
 for s in segments:
  for h in s.get('source_handles',[s['handle']]):systems_by_handle[h].add(s['source_system'])
 # Explicit source-native rule permits preserving a real assembly even if schedule parameters are missing.
 for rule in cfg.get('native_equipment_rules',[]):
  for text in doc.modelspace().query('TEXT'):
   if re.fullmatch(rule['tag_regex'],text.dxf.text.strip())and not any(b['equipment_tag']==text.dxf.text.strip()for b in bindings):
    bindings.append(dict(equipment_tag=text.dxf.text.strip(),source_handle=text.dxf.handle,x=text.dxf.insert.x,y=text.dxf.insert.y,profile_candidates=[],parameter_binding_state='source_native_equipment_parameters_missing'))
 owned=[g['source_handle']for b in bindings for g in b.get('glyph_candidates',[])];assemblies,assembly_audit=profile_native_assemblies(doc,bindings,profiles,set(cfg['inline_types']),owned,native_rules=cfg.get('native_equipment_rules',[]));bytag={a['binding']['equipment_tag']:a for a in assemblies};nodes=[];contacts=[];ends={};recognition=[];unresolved_tags=[];source_equipment=[]
 for b in bindings:
  tag=b['equipment_tag'];glyph=b.get('glyph_candidates',[]);assembly=bytag.get(tag);pump=next((p for p in ns['pump_bindings']if p['binding']['equipment_tag']==tag),None)
  if tag in contours_by_tag:
   contour=contours_by_tag[tag];box=contour['bounds'];e=contour['entity'];primitives=[e];kind=contour['label'];block='source_closed_equipment_contour';handles=[e.dxf.handle];center=((box[0]+box[2])/2,(box[1]+box[3])/2);symbol='EQ_CONTOUR';port_dist=lambda p,shape=e:primitive_distance(p,shape)
  elif assembly:
   box=assembly['bounds'];e=assembly['entity'];primitives=assembly['primitives'];kind='Profiled Equipment Assembly';block=e.dxf.name;handles=[e.dxf.handle];center=((box[0]+box[2])/2,(box[1]+box[3])/2);symbol='EQ_ASSEMBLY';port_dist=lambda p,prim=primitives:min(primitive_distance(p,z)for z in prim)
   if assembly.get('package_boundary_verified'):port_dist=lambda p,bb=box:point_bbox(p,bb)
  elif pump:
   center=pump['center'];rr=pump['radius'];box=[center[0]-rr,center[1]-rr,center[0]+rr,center[1]+rr];kind='Water Pump';block='exploded_pump_triangle_circle';handles=pump['source_handles'];symbol='EQ_PUMP';port_dist=lambda p,c=center,r=rr:abs(dist(p,c)-r)
  elif len(glyph)==1 and glyph[0]['block']in cfg['equipment_blocks']:
   e=doc.entitydb[glyph[0]['source_handle']];bb=bbox.extents([e]);box=[bb.extmin.x,bb.extmin.y,bb.extmax.x,bb.extmax.y];center=((box[0]+box[2])/2,(box[1]+box[3])/2);primitives=native_primitives(e);block=e.dxf.name;kind=cfg['equipment_blocks'][block]['label'];symbol=cfg['equipment_blocks'][block]['symbol_key'];handles=[e.dxf.handle];port_dist=lambda p,prim=primitives:min(primitive_distance(p,z)for z in prim)
  else:
   unresolved_tags.append({'equipment_tag':tag,'source_tag_handle':b['source_handle'],'profile_candidates':b.get('profile_candidates',[]),'reason':'no_unique_native_equipment_or_assembly_signature'});continue
  n={'node_id':tag,'node_type':'equipment','subtype':kind,'floor':'Schematic','label':tag,'x':center[0],'y':center[1],'source_handles':handles,'source_handle':handles[0],'source_block':block,'symbol_key':symbol,'source_bounds':box,'source_tag_handle':b['source_handle'],'profile_candidates':b.get('profile_candidates',[]),'package_boundary':bool((tag in contours_by_tag and contours_by_tag[tag].get('package_boundary'))or(assembly and assembly.get('package_boundary_verified'))),'recognition_status':'native_geometry_and_explicit_profile_reference_unreviewed'if b.get('profile_candidates')else'native_equipment_geometry_verified_parameters_missing','parameter_binding_state':'reference_candidates_only'if b.get('profile_candidates')else'missing_schedule_parameters'};nodes.append(n);source_equipment.append(n)
  for v,point in enumerate(vs):
   inds=ad.get(('physical',v),[])
   if len(inds)!=1 or point_bbox(point,box)>pg_constants.TOL or port_dist(point)>pg_constants.TOL:continue
   other=vs[next(k for k in ps[inds[0]]['vertices']if k!=v)]
   if point_bbox(other,box)<=pg_constants.TOL:
    if block not in cfg.get('native_equipment_multisegment_port_blocks',[]):continue
    cur=next(k for k in ps[inds[0]]['vertices']if k!=v);prev=inds[0];seen_pieces={prev};exit_proven=False
    while True:
     if point_bbox(vs[cur],box)>pg_constants.TOL:exit_proven=True;break
     nexts=[j for j in ad.get(('physical',cur),[])if j!=prev and j not in seen_pieces]
     if len(nexts)!=1:break
     prev=nexts[0];seen_pieces.add(prev);cur=next(k for k in ps[prev]['vertices']if k!=cur)
    if not exit_proven:continue
   if v in ends and ends[v]!=tag:raise ValueError('Ambiguous native equipment port ownership')
   ends[v]=tag;contacts.append({'node_id':tag,'port_id':tag+'-P'+str(sum(c['node_id']==tag for c in contacts)+1).zfill(2),'vertex':v,'x':point[0],'y':point[1],'source_equipment_handles':handles,'source_pipe_handles':ps[inds[0]]['source_handles'],'contact_rule':'verified_closed_equipment_enclosure_terminal_and_outward_source_pipe'if assembly and assembly.get('package_boundary_verified')else'native_pipe_terminal_on_equipment_primitive_and_outward_bbox_exit'})
 # Source-noted external boundaries, never plain pipe endpoints.
 external,external_audit=external_interface_candidates(doc,vs,ps,ad,cfg)
 marked,marked_audit=source_cup_terminals(list(doc.modelspace()),vs,ps,ad,cfg.get('source_terminal_glyph_rules',[]));external+=marked;external_audit+=marked_audit
 for i,c in enumerate(external,1):
  v=c['vertex'];nid='EXT'+str(i).zfill(3)
  if v in ends:raise ValueError('External note overlaps existing equipment ownership')
  nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'source_noted_external_interface','floor':'Schematic','label':c['label'],'x':vs[v][0],'y':vs[v][1],'system':c['system'],'source_handle':c['evidence']['source_note_handle'],'source_evidence':c['evidence'],'ports':[{'port_id':nid+'-P1','system':c['system'],'x':vs[v][0],'y':vs[v][1],'source_marker_handle':c['evidence']['source_note_handle']}]});ends[v]=nid
 # Preserve established T IDs spatially; append newly recovered contacts.
 prior=json.loads(args.previous_graph.read_text(encoding='utf8'))if args.previous_graph else {'nodes':[],'edges':[]};prior_t=[n for n in prior['nodes']if n['node_type']in ['tee','physical_junction']];next_t=max([int(n['node_id'][1:])for n in prior_t if re.fullmatch('T[0-9]+',n['node_id'])]+[0])+1;used_t=set();junction_audit=[]
 for v,point in sorted(enumerate(vs),key=lambda x:(-x[1][1],x[1][0])):
  inds=ad.get(('physical',v),[])
  if v in ends or len(inds)<3:continue
  if len(inds)>3:junction_audit.append({'x':point[0],'y':point[1],'degree':len(inds),'reason':'four_or_more_physical_source_rays_pending'});continue
  old=next((n for n in prior_t if dist(point,(n['x'],n['y']))<=pg_constants.TOL and n['node_id']not in used_t),None);nid=old['node_id']if old else 'T'+str(next_t).zfill(3)
  if not old:next_t+=1
  used_t.add(nid);nodes.append({'node_id':nid,'node_type':'tee','floor':'Schematic','label':nid,'x':point[0],'y':point[1],'source_handles':sorted({h for j in inds for h in ps[j]['source_handles']}),'recognition_status':'three_distinct_source_endpoint_contact_rays_unreviewed'});ends[v]=nid
 # A source contact with more than three rays is not a proven T. An opt-in
 # review boundary retains every adjacent source fragment without asserting
 # a hydraulic junction. Each ray has its own logical, unverified port.
 virtual_piece_ports={};ambiguous_boundaries=[]
 if cfg.get('ambiguous_contact_policy')=='explicit_virtual_review_boundary':
  for v,point in sorted(enumerate(vs),key=lambda x:(-x[1][1],x[1][0])):
   inds=ad.get(('physical',v),[])
   if v in ends or len(inds)<=3:continue
   nid='UC'+str(len(ambiguous_boundaries)+1).zfill(4)
   classes=sorted({sy for j in inds for h in ps[j]['source_handles']for sy in systems_by_handle[h]if sy!=unknown});sy=classes[0]if len(classes)==1 else unknown
   ports=[]
   for ordinal,j in enumerate(inds,1):
    pid=nid+'-P'+str(ordinal);virtual_piece_ports[(nid,j)]=pid
    ports.append({'port_id':pid,'system':sy,'x':point[0],'y':point[1],'review_required':True,'physical_port_verified':False,'status':'unverified_source_ray_binding'})
   evidence={'status':'ambiguous_multi_ray_source_contact','degree':len(inds),'source_handles':sorted({h for j in inds for h in ps[j]['source_handles']}),'rule':'explicit_review_boundary_preserves_each_source_ray_without_asserted_junction','physical_junction_confirmed':False}
   nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_multi_ray_contact','boundary_type':'unresolved_source_terminal','review_required':True,'floor':'Schematic','label':'Unresolved Source Contact '+str(len(ambiguous_boundaries)+1),'x':point[0],'y':point[1],'system':sy,'source_handles':evidence['source_handles'],'source_evidence':evidence,'ports':ports});ends[v]=nid;ambiguous_boundaries.append(dict(evidence,node_id=nid,x=point[0],y=point[1]))
 dump(out/'ambiguous_source_contact_boundaries.json',ambiguous_boundaries)
 terminal_audit=[]
 prior_ut=[n for n in prior['nodes']if n.get('node_type')=='virtual_equipment'and re.fullmatch('UT[0-9]+',n['node_id'])];used_ut=set();next_ut=max([int(n['node_id'][2:])for n in prior_ut if re.fullmatch('UT[0-9]+',n['node_id'])]+[0])+1
 if cfg.get('unresolved_terminal_policy','explicit_virtual_boundary')=='explicit_virtual_boundary':
  # Unknown ends are explicit review boundaries, never confirmed physical equipment.
  candidates=[v for v in range(len(vs))if v not in ends and len(ad.get(('physical',v),[]))==1]
  for ordinal,v in enumerate(sorted(candidates,key=lambda v:(-vs[v][1],vs[v][0])),1):
   p=vs[v];old_ut=[n for n in prior_ut if n['node_id']not in used_ut and dist(p,(n['x'],n['y']))<=pg_constants.TOL];nid=old_ut[0]['node_id']if len(old_ut)==1 else 'UT'+str(next_ut).zfill(4)
   if len(old_ut)!=1:next_ut+=1
   used_ut.add(nid);piece=ps[ad[('physical',v)][0]];classes=sorted({sy for h in piece['source_handles']for sy in systems_by_handle[h]if sy!=unknown});sy=classes[0]if len(classes)==1 else unknown
   evidence={'source_pipe_handles':piece['source_handles'],'x':p[0],'y':p[1],'status':'unresolved_source_endpoint','rule':'retained_native_pipe_endpoint_without_proven_equipment_or_external_boundary','external_connection_confirmed':False}
   nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal','boundary_type':'unresolved_source_terminal','review_required':True,'floor':'Schematic','label':'Unresolved Source Terminal '+str(ordinal),'x':p[0],'y':p[1],'system':sy,'source_handles':piece['source_handles'],'source_evidence':evidence,'ports':[{'port_id':nid+'-P1','system':sy,'x':p[0],'y':p[1],'review_required':True}]});ends[v]=nid;terminal_audit.append(dict(evidence,node_id=nid))
 dump(out/'unresolved_terminal_audit.json',terminal_audit)
 edges=[];unresolved=[];visited=set();represented=set();node_map={n['node_id']:n for n in nodes};next_edge=max([int(e['edge_id'][1:])for e in prior['edges']if re.fullmatch('E[0-9]+',e['edge_id'])]+[0])+1;old_edges={}
 def edge_sig(a,b,handles):return(tuple(sorted([a,b])),tuple(sorted(set(handles))))
 for e in prior['edges']:old_edges[edge_sig(e['start_node_id'],e['end_node_id'],e.get('source_handles',[]))]=e['edge_id']
 for v,nid in sorted(ends.items()):
  for first in ad[('physical',v)]:
   if first in visited:continue
   path=[vs[v]];handles=[];piece_ids=[];cur=v;j=first;other=None;normalizations=[]
   while True:
    if j in piece_ids:break
    piece_ids.append(j);piece=ps[j];handles+=piece['source_handles'];normalizations+=[piece['normalization']]if piece.get('normalization')else[];cur=next(k for k in piece['vertices']if k!=cur);path.append(vs[cur])
    if cur in ends:other=ends[cur];break
    choices=[k for k in ad[('physical',cur)]if k!=j]
    if len(choices)!=1:break
    j=choices[0]
   visited.update(piece_ids);sources=sorted({sy for h in handles for sy in systems_by_handle[h]if sy!=unknown});boundary_systems={node_map[n]['system']for n in [nid,other]if n and node_map[n]['node_type']=='virtual_equipment'}
   effective_classes=(set(sources)|boundary_systems)-{unknown};sy=next(iter(effective_classes))if len(effective_classes)==1 else unknown
   if other and other!=nid:
    eid=old_edges.get(edge_sig(nid,other,handles))
    if not eid:eid='E'+str(next_edge).zfill(4);next_edge+=1
    e={'edge_id':eid,'start_node_id':nid,'end_node_id':other,'edge_type':'tee_to_virtual_equipment'if any(node_map[k]['node_type']=='virtual_equipment'for k in [nid,other])else 'tee_to_tee'if all(node_map[k]['node_type']=='tee'for k in [nid,other])else 'tee_to_equipment','system':sy,'floor_start':'Schematic','floor_end':'Schematic','path_points':path,'attribute_paths':[path],'path_length':sum(dist(a,b)for a,b in zip(path,path[1:])),'source_handles':sorted(set(handles)),'source_systems':sources,'system_assignment':'source_layers_consistent'if sy!=unknown else 'physical_continuity_proven_system_classification_pending','connection_mode':'source_endpoint_continuity_and_verified_native_symbol_spans','normalizations':sorted(set(normalizations)),'equipment_inventory':[]}
    for key,k in [('start_port_id',nid),('end_port_id',other)]:
     if node_map[k]['node_type']=='virtual_equipment':e[key]=virtual_piece_ports.get((k,piece_ids[0]if key=='start_port_id'else piece_ids[-1]),node_map[k]['ports'][0]['port_id'])
    e['source_display_geometry']=[dict(a['source_display_geometry'],source_handle=a['handle'])for a in ns['arc_audit']if a['handle']in e['source_handles']];edges.append(e);represented.update(piece_ids)
    for c in contacts:
     if c['vertex']in [v,cur]:c.update(edge_id=eid,system=sy)
   else:unresolved.append({'start_node_id':nid,'end_node_id':other,'path_points':path,'source_handles':sorted(set(handles)),'source_systems':sources,'system':sy,'reason':'unverified_external_boundary_or_ambiguous_physical_contact','piece_ids':piece_ids})
 for j,p in enumerate(ps):
  if j not in visited:unresolved.append({'path_points':[vs[k]for k in p['vertices']],'source_handles':p['source_handles'],'reason':'no_verified_node_on_source_fragment','piece_ids':[j],'system':unknown})
 if unresolved and cfg.get('strict_source_path_coverage',True):
  dump(out/'unresolved_paths.json',unresolved);dump(out/'source_path_coverage_failure.json',{'status':'blocked_source_coverage','unrepresented_path_groups':len(unresolved),'reason':'Source pipe paths require explicit graph boundaries or an instrument-context classification before publication. Source evidence is retained.'})
  raise ValueError('Unrepresented source pipe paths remain; see source_path_coverage_failure.json. Do not publish a clean-looking graph that skips these paths.')
 connected_virtual={n['node_id']for n in nodes if n['node_type']=='virtual_equipment'and any(n['node_id']in[e['start_node_id'],e['end_node_id']]for e in edges)}
 dump(out/'pending_external_interfaces.json',[n for n in nodes if n['node_type']=='virtual_equipment'and n['node_id']not in connected_virtual])
 nodes=[n for n in nodes if n['node_type']!='virtual_equipment'or n['node_id']in connected_virtual]
 for n in nodes:
  incident={e['system']for e in edges if n['node_id']in[e['start_node_id'],e['end_node_id']]}
  if n['node_type']=='tee':n.update(system=next(iter(incident))if len(incident)==1 else unknown,mixed_source_contact=len(incident)>1,incident_systems=sorted(incident),system_review_required=len(incident)>1)
  if n['node_type']=='virtual_equipment'and len(incident)==1:
   effective=next(iter(incident));n['source_noted_system']=n['system'];n['system']=effective
   for p in n['ports']:p.update(system=effective,source_noted_system=n['source_noted_system'])
 section_audit={'connections':[],'edge_id_mapping':{},'retired_nodes':{}}
 if cfg.get('source_section_connections'):
  section_profile=cfg['source_section_connections']
  if section_profile.get('source_sha256')!=hashlib.sha256(args.dxf.read_bytes()).hexdigest():raise ValueError('Section calibration belongs to another source')
  from pipe_section_connections import apply_to_doc
  normalized,section_audit=apply_to_doc(doc,{'nodes':nodes,'edges':edges},section_profile,prior)
  nodes,edges=normalized['nodes'],normalized['edges'];node_map={n['node_id']:n for n in nodes}
  from pipe_section_connections import remap_id
  remapping=section_audit['edge_id_mapping']|section_audit.get('stable_edge_reconciliation',{})
  for contact in contacts:
   if contact.get('edge_id'):contact['edge_id']=remap_id(contact['edge_id'],remapping)
  for record in terminal_audit:
   if record['node_id']in section_audit['retired_nodes']:record.update(final_status='retired_section_connector',replacement=section_audit['retired_nodes'][record['node_id']])
  dump(out/'unresolved_terminal_audit.json',terminal_audit)
 dump(out/'source_section_connections_audit.json',section_audit)
 nested_audit=None
 if cfg.get('nested_equipment_ports'):
  from nested_equipment_ports import apply as bind_nested_equipment
  normalized,nested_audit=bind_nested_equipment({'nodes':nodes,'edges':edges},cfg['nested_equipment_ports'],prior)
  nodes,edges=normalized['nodes'],normalized['edges'];node_map={n['node_id']:n for n in nodes}
  source_equipment.extend(n for n in nodes if n.get('recognition_status')=='native_nested_body_and_caption_verified')
  contacts.extend(nested_audit['contacts'])
  for record in terminal_audit:
   if record['node_id']in nested_audit['retired_nodes']:record.update(final_status='promoted_native_equipment_port',replacement=nested_audit['retired_nodes'][record['node_id']])
  dump(out/'unresolved_terminal_audit.json',terminal_audit)
  dump(out/'native_equipment_reconciliation.json',nested_audit)
 assigned=[];unassigned=[];component_roles=[];gauges=source_gauges(doc);legend_regions=source_reference_regions(doc,set(cfg['inline_types']));dump(out/'source_reference_regions.json',legend_regions)
 for s in ns['symbols']:
  if s['handle']in instrument_members:
   component_roles.append({'source_handle':s['handle'],'role':'measurement_assembly_member','group_ids':[g['id']for g in instrument_groups if s['handle']in g['component_handles']]});continue
  label,code=cfg['inline_types'][s['block']];bb=s['bounds'];p=((bb[0]+bb[2])/2,(bb[1]+bb[3])/2);candidates,contact_rule=symbol_pipe_contacts(s,edges,doc,cfg.get('sensor_extension_blocks',[]),cfg.get('native_inline_anchor_rules',[]));r={'device_name':code+'-'+s['handle'],'equipment_type':label,'type_code':code,'source_kind':s.get('source_kind','block_insert'),'source_block_name':s['block'],'source_top_handle':s['handle'],'source_handles':symbol_display_handles(s,doc,gauges),'x':p[0],'y':p[1],'assignment_x':p[0],'assignment_y':p[1],'source_insert_x':s['insert'][0],'source_insert_y':s['insert'][1],'assignment_rule':contact_rule+'_unreviewed'}
  container=next((c for c in contours if c.get('package_boundary')and point_bbox(p,c['bounds'])<=pg_constants.TOL),None)
  if container is None and not candidates and s.get('entity')is not None:
   native_ends=[xy(z)for pe in native_primitives(s['entity'])if pe.dxftype()=='LINE'for z in [pe.dxf.start,pe.dxf.end]]
   owners={r['equipment_id']for r in package_audit if any(segdist(z,r['a'],r['b'])<=pg_constants.TOL for z in native_ends)}
   if len(owners)==1:container=next(c for c in contours if c['binding']['equipment_tag']in owners)
  reference=next((reg for reg in legend_regions if point_bbox(p,reg['bounds'])<=pg_constants.TOL),None)
  if container:
   role=dict(r,role='equipment_internal_component',owner_equipment=container['binding']['equipment_tag']);component_roles.append(role);next(n for n in nodes if n['node_id']==role['owner_equipment']).setdefault('internal_components',[]).append(role);continue
  if reference and not candidates:
   component_roles.append(dict(r,role='reference_legend_only',source_legend_evidence=reference));continue
  component_roles.append(dict(source_handle=s['handle'],role='edge_component'if len(candidates)==1 else 'unresolved_component'))
  if len(candidates)==1:e=candidates[0];r.update(edge_id=e['edge_id'],edge_distance=min(segdist(p,a,b)for a,b in zip(e['path_points'],e['path_points'][1:])),assignment_status='assigned');assigned.append(r)
  else:r.update(assignment_status='unresolved',candidate_edge_ids=[e['edge_id']for e in candidates]);unassigned.append(r)
 for group in instrument_groups:
  owner_ids=sorted({e['edge_id']for e in edges if any(any(segdist(p,a,b)<=pg_constants.TOL for a,b in zip(e['path_points'],e['path_points'][1:]))for p in group['attachment_points'])});group['related_edge_ids']=owner_ids
  if not owner_ids:continue
  x,y=group['display_center'];assigned.append({'device_name':group['id'],'equipment_type':group['label'],'type_code':'DPA','source_kind':group['source_kind'],'source_block_name':'SOURCE_'+group['label'].replace(' ','_').upper(),'source_top_handle':group['source_handles'][0],'source_handles':group['source_handles'],'x':x,'y':y,'assignment_x':x,'assignment_y':y,'source_insert_x':x,'source_insert_y':y,'edge_id':owner_ids[0],'related_edge_ids':owner_ids,'edge_distance':0,'assignment_status':'assigned','assignment_rule':group['rule']})
 dump(out/'source_component_roles.json',component_roles)
 dump(out/'source_instrument_assemblies.json',instrument_groups)
 dump(out/'source_component_geometry.json',[{'device_name':r['device_name'],'source_handles':r['source_handles'],'source_kind':r['source_kind'],'related_edge_ids':r.get('related_edge_ids',[r['edge_id']])}for r in assigned])
 head_audit=[]
 for symbol in ns['symbols']:
  if symbol['block']!='传感器':continue
  head=instrument_head_match(symbol,doc,gauges);role=next(r['role']for r in component_roles if r.get('source_handle',r.get('source_top_handle'))==symbol['handle']);head['source_role']=role
  record=next((r for r in assigned if r['source_top_handle']==symbol['handle']),None)
  if record is not None:
   head['edge_id']=record['edge_id'];record['source_head_status']=head['status'];record['source_head_handle']=head.get('source_head_handle','');record['source_head_tag']=head.get('source_head_tag','')
  head_audit.append(head)
 dump(out/'instrument_head_coverage.json',head_audit)
 # Discover tagged heads independently of accepted sensor bodies. Previously
 # completeness checked only recognized INSERTs and missed exploded bodies.
 claimed={h for r in assigned+instrument_groups for h in r.get('source_handles',[])}
 claimed.update(h for r in component_roles for h in r.get('source_handles',[]))
 tagged_coverage=[]
 for q in gauges:
  h=q['entity'].dxf.handle;reference=any(point_bbox(q['center'],reg['bounds'])<=pg_constants.TOL for reg in legend_regions)
  tagged_coverage.append({'source_head_handle':h,'source_tag':q['tag'],'source_layer':q['entity'].dxf.layer,'source_handles':q['handles'],'center':q['center'],'status':'reference_legend_only'if reference else 'represented_source_geometry'if h in claimed else 'pending_unrepresented_tagged_head'})
 dump(out/'source_tagged_head_coverage.json',tagged_coverage)
 for r in assigned:
  r['source_instrument_tags']=sorted({doc.entitydb[h].dxf.text.strip()for h in r['source_handles']if doc.entitydb[h].dxftype()=='TEXT'and re.fullmatch(r'[A-Z][A-Z0-9-]*',doc.entitydb[h].dxf.text.strip())})
 for e in edges:
  group=collections.defaultdict(list)
  for r in assigned:
   if r['edge_id']==e['edge_id']:group[r['equipment_type']].append(r['device_name'])
  e['equipment_inventory']=[{'equipment_type':typ,'count':len(names),'device_names':names}for typ,names in group.items()]
 display_audit=equipment_display(doc,nodes);fidelity=assembly_fidelity(doc,instrument_groups,ns['symbols'])
 dump(out/'equipment_display_coverage.json',display_audit);dump(out/'assembly_source_fidelity.json',fidelity)
 if any(r['missing_source_handles']for r in fidelity):raise ValueError('Source assembly fidelity failed; repair shared rules before viewer delivery')
 ledger=[]
 for n in source_equipment:
  cc=[c for c in contacts if c['node_id']==n['node_id']];n['source_ports']=cc;ledger.append({'equipment_id':n['node_id'],'source_block':n['source_block'],'source_port_count':len(cc),'ports_with_logical_edges':sum('edge_id'in c for c in cc),'ports_without_completed_edges':[c for c in cc if 'edge_id'not in c],'edges':[{'edge_id':e['edge_id'],'system':e['system'],'source_systems':e['source_systems']}for e in edges if n['node_id']in[e['start_node_id'],e['end_node_id']]]})
 graph={'metadata':{'task_id':cfg['project_id'],'project_id':cfg['project_id'],'extraction_status':'partial','graph_complete':False,'source_dxf':args.dxf.name,'source_sha256':hashlib.sha256(args.dxf.read_bytes()).hexdigest(),'shared_geometry_version':'1.0.0','review_status':'unreviewed','system_policy':'Physical continuity is preserved separately from uncertain hydraulic classification. No supply/return tracing across an unclassified segment.','relative_elevation':'unknown'},'nodes':nodes,'edges':edges}
 if cfg.get('source_section_connections'):graph['sourceSectionConnections']=section_audit
 if nested_audit is not None:
  graph['sourceNativeEquipment']=nested_audit
  graph['metadata'].update(hil_ready=False,stage_status='source_comparison_after_native_equipment_recovery')
 graph['sourceFidelity']=fidelity
 graph['sourceTaggedHeadCoverage']=tagged_coverage
 pending_curves=[]
 for arc in ns['arc_audit']:
  if arc['normalization_status']=='normalized':continue
  geo=arc.get('source_display_geometry')or {};center=geo.get('center')
  if center is None:continue
  start=math.radians(geo['start_angle']);span=math.radians((geo['end_angle']-geo['start_angle'])%360);count=max(8,int(abs(span)/math.radians(5)));radius=geo['radius']
  path=[(center[0]+radius*math.cos(start+span*i/count),center[1]+radius*math.sin(start+span*i/count))for i in range(count+1)]
  pending_curves.append({'path_points':path,'source_handles':[arc.get('source_entity_handle',arc['handle'])],'reason':'Unqualified native curve: '+arc['normalization_status']+'; source context only, connectivity unconfirmed','source_display_geometry':geo})
 source_coverage_gate(doc,graph,cfg,out)
 dump(out/'pending_source_curves.json',pending_curves)
 if pending_curves:graph['pendingSourcePaths']=pending_curves
 summary={'task_id':cfg['project_id'],'status':'partial_unreviewed','nodes':len(nodes),'edges':len(edges),'equipment_nodes':len(source_equipment),'tee_nodes':sum(n['node_type']=='tee'for n in nodes),'virtual_interfaces':sum(n['node_type']=='virtual_equipment'for n in nodes),'edges_by_system':dict(collections.Counter(e['system']for e in edges)),'assigned_components':len(assigned),'unresolved_components':len(unassigned),'recognized_inline_instances':len(ns['symbols']),'source_arcs':len(ns['arc_audit']),'normalized_jumps':sum(a['normalization_status']=='normalized'for a in ns['arc_audit']),'equipment_physical_ports':len(contacts),'equipment_ports_with_edges':sum('edge_id'in c for c in contacts),'unresolved_equipment_tags':len(unresolved_tags),'unresolved_path_groups':len(unresolved),'atomic_source_pieces':len(ps),'atomic_pieces_on_edges':len(represented),'mixed_source_junctions':sum(n.get('mixed_source_contact',False)for n in nodes),'unknown_system_edges':sum(e['system']==unknown for e in edges),'human_review':'unreviewed','unresolved_terminal_nodes':sum(n.get('boundary_type')=='unresolved_source_terminal'for n in nodes),'measurement_assemblies':len(instrument_groups),'inline_members_in_measurement_groups':len(instrument_members),'reference_legend_components':sum(r['role']=='reference_legend_only'for r in component_roles),'equipment_internal_components':sum(r['role']=='equipment_internal_component'for r in component_roles),'straight_crossovers':len(straight_audit),'edge_sensor_heads_complete':sum(r['source_role']=='edge_component'and r['status']=='complete_tagged_head'for r in head_audit),'edge_sensor_heads_pending':sum(r['source_role']=='edge_component'and r['status']!='complete_tagged_head'for r in head_audit)}
 if cfg.get('source_section_connections'):summary['source_section_connections']=sum(r['status']=='applied'for r in section_audit['connections'])
 for name,data in [('graph_with_edges.json',graph),('graph_all_systems.json',graph),('edge_summary.json',summary),('equipment_ports.json',contacts),('equipment_port_coverage.json',ledger),('equipment_assembly_recognition.json',assembly_audit),('external_interface_evidence.json',external_audit),('unresolved_equipment.json',unresolved_tags),('unresolved_paths.json',unresolved),('unresolved_components.json',unassigned),('pipe_crossover_arc_normalizations.json',ns['arc_audit']),('ambiguous_junctions.json',junction_audit),('source_physical_segments.json',segments)]:dump(out/name,data)
 table(out/'topology_nodes.csv',nodes);table(out/'edges.csv',edges);table(out/'edge_device_instances.csv',assigned,['device_name','equipment_type','type_code','source_kind','source_block_name','source_top_handle','x','y','assignment_x','assignment_y','source_insert_x','source_insert_y','edge_id','edge_distance','assignment_status','assignment_rule','source_handles','related_edge_ids','source_instrument_tags','source_head_status','source_head_handle','source_head_tag']);table(out/'unresolved_components.csv',unassigned);table(out/'equipment_ports.csv',contacts);table(out/'edge_equipment_by_type.csv',[dict(edge_id=e['edge_id'],start_node_id=e['start_node_id'],end_node_id=e['end_node_id'],equipment_type=a['equipment_type'],device_count=a['count'],device_names=a['device_names'])for e in edges for a in e['equipment_inventory']]);table(out/'virtual_equipment_ports.csv',[dict(node_id=n['node_id'],port_id=p['port_id'],system=p['system'],port_x=p['x'],port_y=p['y'],source_marker_handle=p.get('source_marker_handle',''))for n in nodes if n['node_type']=='virtual_equipment'for p in n['ports']],['node_id','port_id','system','port_x','port_y','source_marker_handle']);print(json.dumps(summary,ensure_ascii=False,indent=2))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dxf',type=Path,required=True);p.add_argument('--bindings',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--materials',type=Path);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--previous-graph',type=Path);p.add_argument('--no-overwrite',action='store_true');args=p.parse_args();build(args)
if __name__=='__main__':main()
