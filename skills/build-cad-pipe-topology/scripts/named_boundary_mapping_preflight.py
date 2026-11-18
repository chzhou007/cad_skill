"""Preflight named boundary route candidates; does not accept or merge mappings."""
import argparse,hashlib,json,math
from pathlib import Path
from crossview_route_diagnostics import shortest

def localize_candidate(candidate,edges,tolerance=.05):
 """Localize crossing to graph segments; retain broad scope if not resolvable."""
 broad=candidate.get('main_edge_ids',[]);point=candidate.get('crossing');handle=candidate.get('source_main_handle');system=candidate.get('system')
 if not isinstance(broad,list) or not broad or not isinstance(point,list) or len(point)!=2 or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in point):return set(broad) if isinstance(broad,list) else set(),'localization_unresolved'
 matched=set()
 for eid in broad:
  e=edges.get(eid)
  if not e or e.get('system')!=system or handle not in e.get('source_handles',[]):return set(broad),'localization_unresolved'
  paths=e.get('attribute_paths') or []
  if not paths:return set(broad),'localization_unresolved'
  try:
   for path in paths:
    for a,b in zip(path,path[1:]):
     dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy;u=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den)) if den else 0
     if math.hypot(point[0]-a[0]-u*dx,point[1]-a[1]-u*dy)<=tolerance:matched.add(eid)
  except (TypeError,IndexError,ValueError):return set(broad),'localization_unresolved'
 return (matched,'crossing_on_graph_path') if matched else (set(broad),'localization_unresolved')

def preflight(plan,axis,route,near,near_stage,axis_length,datum,receipt,plan_hash,axis_hash,near_hash,applied_near=None,axis_gap=None,pair_screen=None,axis_attachment=None):
 ps=plan.get('metadata',{}).get('source_sha256');source=route.get('axis_source_sha256')
 if route.get('status')!='boundary_path_comparison_not_mapping' or route.get('mapping_ready') is not False or route.get('hil_ready') is not False or route.get('plan_graph_sha256')!=plan_hash or route.get('axis_graph_sha256')!=axis_hash or route.get('plan_source_sha256')!=ps:raise ValueError('stale route evidence')
 if near.get('status')!='source_near_endpoint_crossings_not_connections' or near.get('source_sha256')!=ps or near.get('graph_sha256')!=plan_hash or near.get('graph_mutated') is not False or near.get('hil_ready') is not False:raise ValueError('stale plan near-endpoint screen')
 candidates=near.get('candidates');
 if not isinstance(candidates,list) or near.get('counts',{}).get('candidates')!=len(candidates) or near_stage.get('graph_sha256')!=plan_hash or near_stage.get('source_sha256')!=ps or near_stage.get('evidence_sha256')!=near_hash or near_stage.get('candidate_count')!=len(candidates) or near_stage.get('hil_ready') is not False:raise ValueError('invalid near-endpoint receipt')
 if any(c.get('status')!='near_endpoint_crossing_candidate_not_connection' or c.get('system') not in ('supply','return') for c in candidates):raise ValueError('invalid near-endpoint candidate')
 length_graph=axis_hash
 if axis_attachment is not None:
  if (axis_attachment.get('status')!='partial_line_evidence_attached_not_accepted' or axis_attachment.get('source_sha256')!=source or axis_attachment.get('output_graph_sha256')!=axis_hash or axis_attachment.get('connectivity_changed') is not False or axis_attachment.get('physical_length_changed') is not False or axis_attachment.get('review_inherited') is not False or axis_attachment.get('hil_ready') is not False):raise ValueError('stale axis attribute attachment')
  length_graph=axis_attachment.get('input_graph_sha256')
 if axis_length.get('status')!='partial_source_lengths_physical_unknown' or axis_length.get('source_sha256')!=source or axis_length.get('output_graph_sha256')!=length_graph or axis_length.get('hil_ready') is not False or axis_length.get('review_inherited') is not False:raise ValueError('stale axis length evidence')
 if receipt.get('inputs',{}).get('dxf')!=source or receipt.get('final_graph_sha256')!=axis_hash or receipt.get('hil_ready') is not False:raise ValueError('stale axis rebuild receipt')
 if datum.get('source_sha256')!=source or datum.get('graph_sha256')!=axis_hash or datum.get('status')!='drawing_anchor_datum_comparison_not_floor_assignment' or datum.get('hil_ready') is not False or datum.get('human_accepted') is not False or datum.get('graph_mutated') is not False:raise ValueError('stale axis datum screen')
 pe={e['edge_id']:e for e in plan['edges']};ae={e['edge_id']:e for e in axis['edges']};nodes={n['node_id']:n for n in axis['nodes']};lengths={e['edge_id']:e for e in axis_length.get('edges',[])};out=[]
 applied=[]
 gap_records=[]
 if axis_gap is not None:
  screen,stage,evidence_hash=axis_gap
  if (screen.get('status')!='missing_source_joints_candidate_screen' or screen.get('source_sha256')!=source or screen.get('graph_mutated') is not False or screen.get('hil_ready') is not False or stage.get('status')!='missing_joint_candidates_pending_source_comparison' or stage.get('source_sha256')!=source or stage.get('final_graph_sha256')!=axis_hash or stage.get('evidence_sha256')!=evidence_hash or stage.get('input_graph_sha256')!=screen.get('graph_sha256') or stage.get('policy_sha256')!=screen.get('policy_sha256') or stage.get('script_sha256')!=screen.get('script_sha256') or stage.get('human_accepted') is not False or stage.get('hil_ready') is not False):raise ValueError('stale axis gap joint evidence')
  gap_records=screen.get('records')
  if not isinstance(gap_records,list) or not gap_records or stage.get('candidate_count')!=len(gap_records) or stage.get('candidate_handles')!=[x.get('insert_handle') for x in gap_records] or len(set(stage['candidate_handles']))!=len(gap_records):raise ValueError('invalid axis gap joint scope')
  for x in gap_records:
   edge=ae.get(x.get('edge_id'))
   if not edge or edge.get('system')!=x.get('system') or x.get('status')!='source_calibrated_joint_unassigned_pending_review' or x.get('physical_length')!='unknown' or x.get('human_accepted') is not False:raise ValueError('invalid axis gap joint candidate')
 if applied_near is not None:
  if applied_near.get('status')!='applied_near_tees_pending_review' or applied_near.get('source_sha256')!=ps or applied_near.get('graph_sha256')!=plan_hash or applied_near.get('graph_mutated') is not False or applied_near.get('human_accepted') is not False or applied_near.get('hil_ready') is not False or not isinstance(applied_near.get('records'),list):raise ValueError('stale applied near-tee screen')
  applied=applied_near['records']
  for x in applied:
   nid=x.get('node_id');incident=[e for e in plan['edges'] if nid in (e.get('start_node_id'),e.get('end_node_id'))]
   if x.get('status')!='source_normalized_tee_not_human_accepted' or len(incident)!=3 or sorted(e['edge_id'] for e in incident)!=x.get('incident_edge_ids') or any(e.get('system')!=x.get('system') for e in incident):raise ValueError('invalid applied near-tee record')
 for row in route.get('comparisons',[]):
  s=row.get('system');pends=row.get('plan_boundary_nodes',[]);inner=row.get('axis_inner_nodes',[]);anchors=row.get('axis_anchor_edges',[]);boundary=row.get('axis_boundary_node')
  if s not in ('supply','return') or row.get('status')!='graph_adjacency_diagnostic_not_physical_loop' or len(pends)!=2 or len(inner)!=2 or len(anchors)!=2 or nodes.get(boundary,{}).get('node_type')!='virtual_equipment':raise ValueError('invalid route scope')
  for edge_id,node in zip(anchors,inner):
   e=ae.get(edge_id)
   if not e or e.get('system')!=s or {e.get('start_node_id'),e.get('end_node_id')}!={boundary,node} or edge_id not in lengths or e.get('path_length_complete') is not False or e.get('physical_length')!='unknown':raise ValueError('axis anchor evidence mismatch')
  pp=shortest(plan,pends[0],pends[1],s,set(),100);ip=shortest(axis,inner[0],inner[1],s,set(anchors),100)
  if pp!=row.get('plan_shortest_paths') or ip!=row.get('axis_shortest_paths_excluding_anchor_edges'):raise ValueError('route paths stale or altered')
  path_edges={eid for path in pp for eid in path}
  if any(e not in pe or pe[e].get('system')!=s for e in path_edges):raise ValueError('plan path system mismatch')
  dn_observations=[]
  for edge_id in sorted(path_edges):
   diameter=pe[edge_id].get('pipe_diameter') or {}
   if diameter.get('status')=='local_source_observation_edgewide_unverified':
    if diameter.get('nominal_mm') is not None or not diameter.get('observations'):raise ValueError('invalid local DN observation')
    dn_observations.append({'edge_id':edge_id,'display':diameter.get('display'),'status':diameter['status']})
  near_hits=[]
  for c in candidates:
   if c.get('system')!=s:continue
   localized,state=localize_candidate(c,pe);intersection=path_edges & localized
   if intersection:near_hits.append({'branch_handle':c['source_branch_handle'],'main_handle':c['source_main_handle'],'endpoint_node_id':c['endpoint_node_id'],'intersecting_main_edges':sorted(intersection),'localization':state})
  reasons=['plan_local_topology_not_verified','axis_local_topology_not_verified','crossview_correspondence_not_confirmed','axis_anchor_physical_length_unknown']
  if not pp or not ip:reasons.append('missing_graph_path')
  if near_hits:reasons.append('plan_route_intersects_near_endpoint_candidates')
  applied_hits=[{'node_id':x['node_id'],'branch_handle':x['branch_handle'],'main_handle':x['main_handle']} for x in applied if x['system']==s and len(path_edges.intersection(x['incident_edge_ids']))>=2]
  if applied_hits:reasons.append('plan_route_crosses_unreviewed_normalized_tee')
  if applied_near is None:reasons.append('plan_normalization_dependencies_not_checked')
  axis_path_edges=set(anchors)|{eid for path in ip for eid in path}
  gap_hits=[{'source_handle':x['insert_handle'],'edge_id':x['edge_id'],'status':x['status']} for x in gap_records if x['system']==s and x['edge_id'] in axis_path_edges]
  if gap_hits:reasons.append('axis_route_contains_unassigned_joint_candidates')
  if axis_gap is None:reasons.append('axis_gap_joint_dependencies_not_checked')
  out.append({'system':s,'labels':row['labels'],'plan_paths':pp,'axis_paths':ip,'plan_near_endpoint_candidates':near_hits,'plan_unreviewed_normalized_tees':applied_hits,'plan_local_dn_observations':dn_observations,'axis_anchor_edges':anchors,'axis_gap_joint_candidates':gap_hits,'reasons':reasons,'mapping_ready':False})
 if not out or len({r['system'] for r in out})!=len(out):raise ValueError('empty or duplicate route comparisons')
 datum_unresolved=[x for x in datum.get('records',[]) if x.get('status')!='anchor_band_matches_graph_label']
 global_datum=len(datum_unresolved)+len(datum.get('unscreened_equipment_ids',[]))
 # A baseline is a finite source segment. Extrapolated anchors and anchors
 # inside its extent remain unaccepted, but have different review evidence.
 datum_scope={'outside_claimed_baseline_extent':[],'inside_claimed_baseline_extent':[],'extent_unknown':[],'unscreened':sorted(datum.get('unscreened_equipment_ids',[]))}
 for item in datum_unresolved:
  within=item.get('anchor_x_within_claimed_native_baseline');key='inside_claimed_baseline_extent' if within is True else 'outside_claimed_baseline_extent' if within is False else 'extent_unknown'
  datum_scope[key].append({'equipment_id':item.get('equipment_id'),'status':item.get('status'),'graph_floor_label':item.get('graph_floor_label'),'drawing_anchor_band_floor':item.get('drawing_anchor_band_floor'),'physical_floor_verified':False})
 pending_equipment=sorted(n['node_id'] for n in plan['nodes'] if n.get('node_type')=='equipment' and n.get('identity_status')=='unresolved')
 pair_candidates=[]; refreshed={}
 if pair_screen is not None:
  if (pair_screen.get('status')!='equipment_label_pair_candidates_not_mapping' or pair_screen.get('plan_graph_sha256')!=plan_hash or pair_screen.get('axis_graph_sha256')!=axis_hash or pair_screen.get('plan_source_sha256')!=ps or pair_screen.get('axis_source_sha256')!=source or pair_screen.get('graph_mutated') is not False or pair_screen.get('mapping_ready') is not False or pair_screen.get('human_accepted') is not False or pair_screen.get('hil_ready') is not False):raise ValueError('stale equipment pair screen')
  groups=pair_screen.get('groups')
  if not isinstance(groups,list) or not groups:raise ValueError('invalid equipment pair screen')
  for group in groups:
   candidates=group.get('candidates');gid=group.get('group_id')
   if not gid or group.get('selected_candidate') is not None or group.get('status')!='pair_identity_not_confirmed' or not isinstance(candidates,list) or len(candidates)!=2:raise ValueError('invalid equipment pair group')
   perms=[]
   for candidate in candidates:
    assignments=candidate.get('assignments',[])
    if len(assignments)!=2:raise ValueError('invalid equipment pair assignments')
    pairs=frozenset((x.get('plan_node_id'),x.get('label'),x.get('plan_text_handle'),x.get('axis_text_handle')) for x in assignments)
    if len(pairs)!=2 or any(not all(x) for x in pairs) or len({x[0] for x in pairs})!=2 or len({x[1] for x in pairs})!=2:raise ValueError('invalid equipment pair evidence')
    perms.append(pairs)
   if perms[0]==perms[1] or {x[0] for x in perms[0]}!={x[0] for x in perms[1]} or {x[1:] for x in perms[0]}!={x[1:] for x in perms[1]}:raise ValueError('invalid equipment pair permutations')
   for perm in perms:
    for nid,label,ph,ah in perm:refreshed.setdefault(nid,set()).add((gid,label,ph,ah))
 for n in plan['nodes']:
  ev=n.get('source_label_pair_evidence')
  if not ev:continue
  labels=n.get('source_label_candidates');alts=ev.get('alternatives')
  if (n.get('node_type')!='equipment' or n.get('identity_status')!='unresolved' or ev.get('identity_confirmed') is not False
      or ev.get('plan_source_sha256')!=ps or ev.get('axis_source_sha256')!=source
      or not isinstance(labels,list) or len(labels)!=2 or len(set(labels))!=2 or not isinstance(alts,list) or len(alts)!=2
      or {x.get('label') for x in alts}!=set(labels)):raise ValueError('stale or invalid equipment pair candidates')
  expected={(ev.get('group_id'),x.get('label'),x.get('plan_text_handle'),x.get('axis_text_handle')) for x in alts}
  if pair_screen is None:
   if ev.get('axis_graph_sha256')!=axis_hash:raise ValueError('stale equipment pair candidates')
  elif refreshed.pop(n['node_id'],None)!=expected:raise ValueError('refreshed equipment pair does not match plan scope')
  pair_candidates.append({'node_id':n['node_id'],'candidate_labels':sorted(labels),'group_id':ev.get('group_id'),'status':'identity_and_crossview_mapping_unconfirmed'})
 if refreshed:raise ValueError('unmatched refreshed equipment pair')
 pair_candidates.sort(key=lambda x:x['node_id'])
 return {'status':'boundary_mapping_preflight_not_mapping','plan_graph_sha256':plan_hash,'axis_graph_sha256':axis_hash,'records':out,'plan_normalization_dependencies_checked':applied_near is not None,'plan_global_unidentified_equipment_ids':pending_equipment,'plan_global_equipment_pair_candidates':pair_candidates,'plan_equipment_scope':'Global inventory, not proof that these specific routes are affected.','axis_datum_global_pending_count':global_datum,'axis_datum_pending_by_extent':datum_scope,'axis_datum_scope':'Global coordinate screen; extrapolated positions are not direct baseline evidence. None of these records establishes a floor error or proves that these specific paths are affected.','mapping_ready':False,'human_accepted':False,'graph_mutated':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-graph','axis-graph','route','near-screen','near-stage','axis-length','axis-datum','axis-receipt','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--applied-near-screen',type=Path)
 p.add_argument('--axis-gap-screen',type=Path);p.add_argument('--axis-gap-stage',type=Path)
 p.add_argument('--equipment-pair-screen',type=Path)
 p.add_argument('--axis-attribute-attachment',type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'))
 applied=load(a.applied_near_screen) if a.applied_near_screen else None
 if applied is not None and applied.get('script_sha256')!=sha(Path(__file__).with_name('screen_applied_near_tees.py')):raise ValueError('stale applied near-tee extractor')
 if bool(a.axis_gap_screen)!=bool(a.axis_gap_stage):raise ValueError('axis gap joint screen and stage must be paired')
 gap=(load(a.axis_gap_screen),load(a.axis_gap_stage),sha(a.axis_gap_screen)) if a.axis_gap_screen else None
 if gap and gap[0].get('script_sha256')!=sha(Path(__file__).with_name('screen_missing_gap_joints.py')):raise ValueError('stale axis gap joint extractor')
 pair=load(a.equipment_pair_screen) if a.equipment_pair_screen else None
 if pair and (pair.get('script_sha256')!=sha(Path(__file__).with_name('screen_equipment_label_pairs.py')) or pair.get('axis_receipt_sha256')!=sha(a.axis_receipt)):raise ValueError('stale equipment pair extractor or receipt')
 attachment=load(a.axis_attribute_attachment) if a.axis_attribute_attachment else None
 if attachment and attachment.get('script_sha256')!=sha(Path(__file__).with_name('attach_partial_line_evidence.py')):raise ValueError('stale axis attachment extractor')
 result=preflight(load(a.plan_graph),load(a.axis_graph),load(a.route),load(a.near_screen),load(a.near_stage),load(a.axis_length),load(a.axis_datum),load(a.axis_receipt),sha(a.plan_graph),sha(a.axis_graph),sha(a.near_screen),applied,gap,pair,attachment);result['input_sha256']={k:sha(getattr(a,k)) for k in ('route','near_screen','near_stage','axis_length','axis_datum','axis_receipt')};result['script_sha256']=sha(Path(__file__))
 if a.axis_attribute_attachment:result['input_sha256']['axis_attribute_attachment']=sha(a.axis_attribute_attachment)
 if a.equipment_pair_screen:result['input_sha256']['equipment_pair_screen']=sha(a.equipment_pair_screen)
 if a.applied_near_screen:result['input_sha256']['applied_near_screen']=sha(a.applied_near_screen)
 if a.axis_gap_screen:result['input_sha256'].update(axis_gap_screen=sha(a.axis_gap_screen),axis_gap_stage=sha(a.axis_gap_stage))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'routes':len(result['records'])}))
if __name__=='__main__':main()
