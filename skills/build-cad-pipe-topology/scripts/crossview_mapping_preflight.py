"""Classify scoped cross-view diagnostic readiness; never create a mapping."""
import argparse,hashlib,json
from pathlib import Path

def evaluate(plan_hash,iso_hash,plan,iso,diagnostic,detail,plan_coverage=None,plan_junctions=None,iso_coverage=None,iso_junctions=None,iso_device_joints=None,dn_evidence=None,iso_anchor_spans=None,iso_equipment_datum_screen=None):
 if diagnostic.get('plan_graph_sha256')!=plan_hash or diagnostic.get('iso_graph_sha256')!=iso_hash or detail.get('graph_sha256')!=plan_hash:raise ValueError('stale graph-bound evidence')
 if diagnostic.get('plan_source_sha256')!=detail.get('source_sha256'):raise ValueError('plan source evidence mismatch')
 if plan.get('metadata',{}).get('source_sha256')!=detail.get('source_sha256'):raise ValueError('plan graph source mismatch')
 if (plan_coverage is None)!=(plan_junctions is None):raise ValueError('plan coverage and junction evidence must be supplied together')
 if plan_coverage is not None:
  for evidence in (plan_coverage,plan_junctions):
   if evidence.get('graph_sha256')!=plan_hash or evidence.get('source_sha256')!=detail.get('source_sha256') or evidence.get('hil_ready') is not False:raise ValueError('stale plan source evidence')
  if plan_coverage.get('status')!='partial_source_coverage_not_physical_length' or plan_junctions.get('status')!='native_ray_evidence_unreviewed':raise ValueError('unexpected plan evidence state')
 if (iso_coverage is None)!=(iso_junctions is None):raise ValueError('isometric coverage and junction evidence must be supplied together')
 if iso_coverage is not None:
  for evidence in (iso_coverage,iso_junctions):
   if evidence.get('graph_sha256')!=iso_hash or evidence.get('source_sha256')!=diagnostic.get('iso_source_sha256') or evidence.get('hil_ready') is not False:raise ValueError('stale isometric source evidence')
  if iso_coverage.get('status')!='partial_source_coverage_not_physical_length' or iso_junctions.get('status')!='native_ray_evidence_unreviewed':raise ValueError('unexpected isometric evidence state')
 if iso_device_joints is not None:
  if iso_coverage is None or iso_device_joints.get('graph_sha256')!=iso_hash or iso_device_joints.get('source_sha256')!=diagnostic.get('iso_source_sha256') or iso_device_joints.get('status')!='native_exploded_device_joint_geometry_unreviewed' or iso_device_joints.get('hil_ready') is not False:raise ValueError('stale or incomplete isometric device joint evidence')
  jrows=iso_device_joints.get('records',[])
  if len({r['edge_id'] for r in jrows})!=len(jrows):raise ValueError('duplicate isometric device joint edge')
 if iso_anchor_spans is not None:
  if iso_device_joints is None or iso_anchor_spans.get('graph_sha256')!=iso_hash or iso_anchor_spans.get('source_sha256')!=diagnostic.get('iso_source_sha256') or iso_anchor_spans.get('status')!='source_witnessed_chain_and_unwitnessed_anchor_connector' or iso_anchor_spans.get('hil_ready') is not False or iso_anchor_spans.get('human_accepted') is not False or iso_anchor_spans.get('graph_mutated') is not False:raise ValueError('stale or unsupported device anchor evidence')
  spans=iso_anchor_spans.get('records',[])
  if not spans or len({s.get('edge_id') for s in spans})!=len(spans):raise ValueError('empty or duplicate device anchor spans')
  for s in spans:
   matches=[j for j in jrows if j.get('edge_id')==s.get('edge_id') and j.get('equipment_id')==s.get('equipment_id') and j.get('system')==s.get('system') and j.get('joint_handle')==s.get('joint_handle')]
   if len(matches)!=1 or s.get('status')!='equipment_anchor_to_joint_is_unwitnessed_logical_connector' or s.get('physical_port_verified') is not False or s.get('connectivity_accepted') is not False or s.get('physical_length')!='unknown':raise ValueError('device anchor evidence conflicts with joint')
 else:spans=[]
 if iso_equipment_datum_screen is not None:
  if iso_equipment_datum_screen.get('graph_sha256')!=iso_hash or iso_equipment_datum_screen.get('source_sha256')!=diagnostic.get('iso_source_sha256') or iso_equipment_datum_screen.get('status')!='drawing_anchor_datum_comparison_not_floor_assignment' or iso_equipment_datum_screen.get('hil_ready') is not False or iso_equipment_datum_screen.get('human_accepted') is not False or iso_equipment_datum_screen.get('graph_mutated') is not False:raise ValueError('stale or unsupported equipment datum screen')
  datum_rows=iso_equipment_datum_screen.get('records',[])
  if not datum_rows or len({v.get('equipment_id') for v in datum_rows})!=len(datum_rows) or any(v.get('physical_floor_verified') is not False or v.get('status') not in ('on_datum','below_first_known_datum','anchor_band_matches_graph_label','anchor_band_differs_from_graph_label') for v in datum_rows):raise ValueError('invalid equipment datum records')
 else:datum_rows=[]
 if dn_evidence is not None:
  if dn_evidence.get('plan_graph_sha256')!=plan_hash or dn_evidence.get('iso_graph_sha256')!=iso_hash or dn_evidence.get('plan_source_sha256')!=diagnostic.get('plan_source_sha256') or dn_evidence.get('iso_source_sha256')!=diagnostic.get('iso_source_sha256') or dn_evidence.get('status')!='crossview_candidate_screen_not_mapping' or dn_evidence.get('hil_ready') is not False or dn_evidence.get('graph_mutated') is not False:raise ValueError('stale or unsupported DN candidate evidence')
  dn_rows=dn_evidence.get('records',[]);keys=[(v.get('plan_edge'),v.get('iso_edge')) for v in dn_rows]
  if not dn_rows or len(keys)!=len(set(keys)):raise ValueError('empty or duplicate DN candidate pairs')
  for v in dn_rows:
   if v.get('status') not in ('different_values_potential_conflict','same_values_candidate_only') or v.get('crossview_path_mapping')!='not_confirmed' or v.get('annotation_binding')!='candidate_not_accepted' or v.get('physical_diameter_selected') is not False:raise ValueError('unsupported DN candidate state')
 else:dn_rows=[]
 if diagnostic.get('status')!='diagnostic_only' or detail.get('status')!='detail_correspondence_unresolved' or detail.get('mapping_ready') is not False:raise ValueError('unexpected evidence state')
 p={e['edge_id']:e for e in plan['edges']};a={e['edge_id']:e for e in iso['edges']}
 if len(p)!=len(plan['edges']) or len(a)!=len(iso['edges']):raise ValueError('duplicate edge ID')
 for v in dn_rows:
  system=v.get('system');plan_edge=p.get(v.get('plan_edge'));iso_edge=a.get(v.get('iso_edge'))
  if system not in ('supply','return') or plan_edge is None or iso_edge is None or plan_edge.get('system')!=system or iso_edge.get('system')!=system:raise ValueError('DN candidate edge/system mismatch')
 unresolved={eid for row in detail['records'] for eid in (row['upper_edge'],row['detail_edge'])}
 if not unresolved<=p.keys():raise ValueError('detail gate references missing plan edge')
 result=[];matched_dn=set()
 for item in diagnostic['comparisons']:
  if item.get('status')!='crossview_diagnostic_not_mapping':raise ValueError('unexpected diagnostic status')
  for side,edges in [('plan_routes',p),('isometric_routes',a)]:
   for route in item.get(side,[]):
    system=route['system'];paths=route['paths'];reasons=['equipment_identity_not_confirmed_across_views']
    if system not in ('supply','return'):raise ValueError('invalid route system')
    if not paths:reasons.append('no_graph_path')
    elif len(paths)>1:reasons.append('multiple_graph_paths')
    path_ids=set()
    for path in paths:
     if not path:raise ValueError('empty route')
     for eid in path:
      if eid not in edges or edges[eid].get('system')!=system:raise ValueError('route edge missing or wrong system')
      path_ids.add(eid)
    if side=='plan_routes' and path_ids&unresolved:reasons.append('route_intersects_unresolved_main_detail_candidates')
    if paths:reasons.append('plan_local_topology_not_verified' if side=='plan_routes' else 'isometric_local_topology_not_verified')
    record={'equipment_id':item['equipment_id'],'view':'plan' if side=='plan_routes' else 'isometric','system':system,'paths':paths,'unresolved_detail_edges':sorted(path_ids&unresolved) if side=='plan_routes' else [],'reasons':reasons,'mapping_ready':False}
    if side=='isometric_routes' and datum_rows:
     matches=[v for v in datum_rows if v['equipment_id']==item['equipment_id']]
     if len(matches)!=1:raise ValueError('equipment missing from selected datum screen')
     n=next((v for v in iso.get('nodes',[]) if v.get('node_id')==item['equipment_id']),None)
     if not n or n.get('floor')!=matches[0].get('graph_floor_label'):raise ValueError('equipment datum screen graph floor mismatch')
     record['isometric_equipment_datum_position']=matches[0]
     if matches[0]['status']!='anchor_band_matches_graph_label':reasons.append('equipment_drawing_anchor_datum_interpretation_unresolved')
    other_side='isometric_routes' if side=='plan_routes' else 'plan_routes'
    other_ids={eid for other in item.get(other_side,[]) if other.get('system')==system for path in other.get('paths',[]) for eid in path}
    matches=[]
    for index,v in enumerate(dn_rows):
     if v.get('system')!=system:continue
     local=v['plan_edge'] if side=='plan_routes' else v['iso_edge'];remote=v['iso_edge'] if side=='plan_routes' else v['plan_edge']
     if local in path_ids and remote in other_ids:
      if v['plan_edge'] not in p or p[v['plan_edge']].get('system')!=system or v['iso_edge'] not in a or a[v['iso_edge']].get('system')!=system:raise ValueError('DN candidate edge/system mismatch')
      matches.append({'plan_edge':v['plan_edge'],'iso_edge':v['iso_edge'],'plan_dn_candidate_mm':v['plan_dn_candidate_mm'],'iso_dn_candidate_mm':v['iso_dn_candidate_mm'],'iso_text_handle':v['iso_text_handle'],'status':v['status']});matched_dn.add(index)
      if v['status']=='different_values_potential_conflict' and 'crossview_dn_candidate_conflict_unresolved' not in reasons:reasons.append('crossview_dn_candidate_conflict_unresolved')
    if matches:record['crossview_dn_candidates']=matches
    coverage=plan_coverage if side=='plan_routes' else iso_coverage;junction_evidence=plan_junctions if side=='plan_routes' else iso_junctions
    if coverage is not None:
     covered={v['edge_id']:v for v in coverage['edges']};junctions={v['node_id']:v for v in junction_evidence['junctions']}
     if len(covered)!=len(coverage['edges']) or len(junctions)!=len(junction_evidence['junctions']):raise ValueError('duplicate source evidence')
     all_covered=bool(path_ids) and all(eid in covered and covered[eid].get('system')==system and covered[eid].get('segments') and all(x.get('status')=='single_source_line_covers' for x in covered[eid]['segments']) for eid in path_ids)
     shared=[]
     for path in paths:
      for left,right in zip(path,path[1:]):
       common={edges[left].get('start_node_id'),edges[left].get('end_node_id')}&{edges[right].get('start_node_id'),edges[right].get('end_node_id')};common.discard(None)
       if len(common)!=1:raise ValueError('route edges do not share one node')
       nid=next(iter(common));j=junctions.get(nid);shared.append({'node_id':nid,'source_ray_evidence':bool(j and j.get('system')==system and j.get('status')=='native_line_ray_evidence_not_accepted' and {left,right}<={r['edge_id'] for r in j.get('source_rays',[])})})
     source_evidence={'all_drawing_segments_covered':all_covered,'junctions':shared,'status':'source_geometry_only_not_connectivity_acceptance'}
     if side=='isometric_routes':
      anchor=route.get('anchor_edge');nid=route.get('anchor_endpoint');j=junctions.get(nid)
      if anchor not in edges or edges[anchor].get('system')!=system or nid not in (edges[anchor].get('start_node_id'),edges[anchor].get('end_node_id')):raise ValueError('invalid isometric anchor')
      first={path[0] for path in paths if path};source_evidence['anchor']={'edge_id':anchor,'node_id':nid,'source_ray_evidence':bool(j and j.get('system')==system and j.get('status')=='native_line_ray_evidence_not_accepted' and ({anchor}|first)<={r['edge_id'] for r in j.get('source_rays',[])})}
     record['plan_source_path_evidence' if side=='plan_routes' else 'isometric_source_path_evidence']=source_evidence
    if side=='isometric_routes' and iso_device_joints is not None:
     matching=[r for r in iso_device_joints['records'] if r['edge_id'] in path_ids]
     if any(r.get('system')!=system or r.get('equipment_id')!=item['equipment_id'] or r.get('status')!='native_chain_geometry_unreviewed' or r.get('physical_port_verified') is not False or r.get('physical_length')!='unknown' for r in matching):raise ValueError('device joint evidence conflicts with route')
     record['isometric_device_joint_evidence']=[{'edge_id':r['edge_id'],'joint_handle':r['joint_handle'],'inner_line_handle':r['inner_line_handle'],'outer_line_handle':r['outer_line_handle'],'circle_handle':r['circle_handle'],'status':r['status'],'physical_port_verified':False,'physical_length':'unknown'} for r in matching]
    if side=='isometric_routes' and spans:
     matching=[s for s in spans if s['edge_id'] in path_ids]
     if any(s['system']!=system or s['equipment_id']!=item['equipment_id'] for s in matching):raise ValueError('device anchor evidence conflicts with route')
     record['isometric_anchor_span_evidence']=matching
    result.append(record)
 if not result:raise ValueError('no routes in diagnostic')
 return {'status':'preflight_only_no_mapping','plan_graph_sha256':plan_hash,'iso_graph_sha256':iso_hash,'records':result,'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'unmatched_dn_candidate_count':len(dn_rows)-len(matched_dn),'limitations':['DN differences are candidate clues, not proven contradictory physical pipe segments.','This consumes unverified diagnostic paths; even paths outside ambiguous detail candidates still require independent source-topology and cross-view identity evidence.','The absence of a route intersection does not establish that a view or mapping is correct.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-graph','iso-graph','diagnostic','detail-gate','output'):p.add_argument('--'+k,required=True,type=Path)
 p.add_argument('--plan-coverage',type=Path);p.add_argument('--plan-junctions',type=Path)
 p.add_argument('--iso-coverage',type=Path);p.add_argument('--iso-junctions',type=Path)
 p.add_argument('--iso-device-joints',type=Path);p.add_argument('--dn-evidence',type=Path);p.add_argument('--iso-anchor-spans',type=Path);p.add_argument('--iso-equipment-datum-screen',type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if a.output.exists():raise FileExistsError(a.output)
 coverage=json.loads(a.plan_coverage.read_text(encoding='utf8')) if a.plan_coverage else None;junctions=json.loads(a.plan_junctions.read_text(encoding='utf8')) if a.plan_junctions else None
 iso_coverage=json.loads(a.iso_coverage.read_text(encoding='utf8')) if a.iso_coverage else None;iso_junctions=json.loads(a.iso_junctions.read_text(encoding='utf8')) if a.iso_junctions else None
 device_joints=json.loads(a.iso_device_joints.read_text(encoding='utf8')) if a.iso_device_joints else None
 dn_evidence=json.loads(a.dn_evidence.read_text(encoding='utf8')) if a.dn_evidence else None
 anchor_spans=json.loads(a.iso_anchor_spans.read_text(encoding='utf8')) if a.iso_anchor_spans else None
 equipment_datum=json.loads(a.iso_equipment_datum_screen.read_text(encoding='utf8')) if a.iso_equipment_datum_screen else None
 if anchor_spans is not None and (not a.iso_coverage or not a.iso_device_joints or anchor_spans.get('coverage_sha256')!=sha(a.iso_coverage) or anchor_spans.get('joints_sha256')!=sha(a.iso_device_joints)):raise ValueError('stale anchor-span dependency hashes')
 r=evaluate(sha(a.plan_graph),sha(a.iso_graph),json.loads(a.plan_graph.read_text(encoding='utf8')),json.loads(a.iso_graph.read_text(encoding='utf8')),json.loads(a.diagnostic.read_text(encoding='utf8')),json.loads(a.detail_gate.read_text(encoding='utf8')),coverage,junctions,iso_coverage,iso_junctions,device_joints,dn_evidence,anchor_spans,equipment_datum);r.update(diagnostic_sha256=sha(a.diagnostic),detail_gate_sha256=sha(a.detail_gate),script_sha256=sha(Path(__file__)))
 if a.plan_coverage and a.plan_junctions:r.update(plan_coverage_sha256=sha(a.plan_coverage),plan_junctions_sha256=sha(a.plan_junctions))
 if a.iso_coverage and a.iso_junctions:r.update(iso_coverage_sha256=sha(a.iso_coverage),iso_junctions_sha256=sha(a.iso_junctions))
 if a.iso_device_joints:r.update(iso_device_joints_sha256=sha(a.iso_device_joints))
 if a.dn_evidence:r.update(dn_evidence_sha256=sha(a.dn_evidence))
 if a.iso_anchor_spans:r.update(iso_anchor_spans_sha256=sha(a.iso_anchor_spans))
 if a.iso_equipment_datum_screen:r.update(iso_equipment_datum_screen_sha256=sha(a.iso_equipment_datum_screen))
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'routes':len(r['records'])}))
if __name__=='__main__':main()
