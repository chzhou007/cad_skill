"""Current isometric adapter; historical alignment implementation stays immutable."""
import sys,json,dataclasses,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'legacy_v17'))
import analyze_graph as geometry
import build_edges as edges
import pipe_geometry as pg
from topology_normalization import trim_elbow_overshoots,snap_near_junction_endpoints
import native_level_evidence
import junction_validation
import native_line_path_evidence
import native_segment_dn_candidates
from source_readability import read_source

def main():
 args=list(sys.argv[1:]);datum=None;line_policy=None;segment_policy=None;coverage_policy=None;partial_policy=None;junction_policy=None;device_circle_policy=None;nested_joint_policy=None;exploded_joint_policy=None
 final_bulk_dn_policy=None;final_cross_floor_policy=None;final_equipment_datum_policy=None;final_dn_detail_scope_policy=None;final_dn_pattern_policy=None
 final_path_coverage_policy=None;final_partial_length_policy=None
 final_gap_joint_policy=None;final_partial_line_policy=None;final_attach_partial_line=False;block_attachment_inputs=None
 upstream_system_policy=None
 source_floor_inputs=None
 if '--source-floor-repair-inputs' in args:
  if '--source-block-attachment-inputs' not in args:raise ValueError('source floor correction requires the final source attachment graph')
  index=args.index('--source-floor-repair-inputs');source_floor_inputs=Path(args[index+1]);del args[index:index+2]
  source_floor_dest=Path(args[args.index('--output-dir')+1])/'topology-source-floor-labels'
  if source_floor_dest.exists():raise ValueError('refusing to overwrite source floor correction')
 final_direct_spline_policy=None
 if '--final-direct-spline-joint-policy' in args:
  if '--upstream-joint-system-policy' not in args:raise ValueError('final direct joint recheck requires upstream system correction')
  index=args.index('--final-direct-spline-joint-policy');final_direct_spline_policy=Path(args[index+1]);del args[index:index+2]
  final_direct_spline_dest=Path(args[args.index('--output-dir')+1])/'direct_spline_joint_audit_final.json'
  if final_direct_spline_dest.exists():raise ValueError('refusing to overwrite final direct joint evidence')
 if '--upstream-joint-system-policy' in args:
  if '--source-block-attachment-inputs' not in args:raise ValueError('upstream system stage requires the final source attachment graph')
  index=args.index('--upstream-joint-system-policy');upstream_system_policy=Path(args[index+1]);del args[index:index+2]
  upstream_system_dest=Path(args[args.index('--output-dir')+1])/'topology-upstream-joint-systems'
  if upstream_system_dest.exists():raise ValueError('refusing to overwrite upstream system correction')
  if '--final-gap-joint-policy' in args and '--direct-spline-joint-policy' in args and final_direct_spline_policy is None:raise ValueError('corrected inventory requires final direct joint recheck for gap reconciliation')
 if ('--final-path-coverage-policy' in args)!=('--final-partial-length-policy' in args):raise ValueError('final partial length requires both coverage and partial policies')
 if '--final-path-coverage-policy' in args:
  if '--exploded-device-chain-policy' not in args:raise ValueError('final partial length requires final device chain stage')
  index=args.index('--final-path-coverage-policy');final_path_coverage_policy=Path(args[index+1]);del args[index:index+2]
  index=args.index('--final-partial-length-policy');final_partial_length_policy=Path(args[index+1]);del args[index:index+2]
  final_length_out=Path(args[args.index('--output-dir')+1]);final_coverage_dest=final_length_out/'native_path_coverage_final.json';final_partial_dest=final_length_out/'topology-final-partial-source-length'
  if final_coverage_dest.exists() or final_partial_dest.exists():raise ValueError('refusing to overwrite final partial length evidence')
 if '--final-partial-line-policy' in args:
  if final_path_coverage_policy is None:raise ValueError('final partial line evidence requires final coverage and partial length')
  index=args.index('--final-partial-line-policy');final_partial_line_policy=Path(args[index+1]);del args[index:index+2]
  final_partial_line_dest=Path(args[args.index('--output-dir')+1])/'partial_native_line_coverage_final.json'
  if final_partial_line_dest.exists():raise ValueError('refusing to overwrite final partial line evidence')
 if '--final-attach-partial-line' in args:
  if final_partial_line_policy is None:raise ValueError('partial line attachment requires final partial line evidence')
  args.remove('--final-attach-partial-line');final_attach_partial_line=True
  final_partial_line_attach_dest=Path(args[args.index('--output-dir')+1])/'topology-final-partial-line-evidence'
  if final_partial_line_attach_dest.exists():raise ValueError('refusing to overwrite final partial line attachment')
 if '--source-block-attachment-inputs' in args:
  if not final_attach_partial_line:raise ValueError('source block attachment requires final partial line attachment')
  index=args.index('--source-block-attachment-inputs');block_attachment_inputs=Path(args[index+1]);del args[index:index+2]
  block_output=Path(args[args.index('--output-dir')+1]);block_evidence=block_output/'source_block_equipment_attachment_evidence.json';block_dest=block_output/'topology-source-block-attachments'
  if block_evidence.exists() or block_dest.exists():raise ValueError('refusing to overwrite source block attachment evidence')
 if '--final-gap-joint-policy' in args:
  if final_path_coverage_policy is None or '--exploded-joint-ownership-policy' not in args:raise ValueError('gap joint screen requires final coverage and joint ownership')
  index=args.index('--final-gap-joint-policy');final_gap_joint_policy=Path(args[index+1]);del args[index:index+2]
  final_gap_joint_dest=Path(args[args.index('--output-dir')+1])/'missing_gap_joint_candidates_final.json'
  final_gap_joint_stage=Path(args[args.index('--output-dir')+1])/'missing_gap_joint_candidates_stage.json'
  final_joint_inventory=Path(args[args.index('--output-dir')+1])/'calibrated_joint_inventory_final.json'
  final_joint_contact_reconciliation=Path(args[args.index('--output-dir')+1])/'calibrated_joint_contact_reconciliation_final.json'
  if final_gap_joint_dest.exists() or final_gap_joint_stage.exists() or final_joint_inventory.exists() or final_joint_contact_reconciliation.exists():raise ValueError('refusing to overwrite gap joint evidence')
 if '--final-equipment-datum-policy' in args:
  if '--exploded-device-chain-policy' not in args or '--datum-policy' not in args:raise ValueError('final equipment datum screen requires final device chain and datum stages')
  index=args.index('--final-equipment-datum-policy');final_equipment_datum_policy=Path(args[index+1]);del args[index:index+2]
  final_equipment_datum_dest=Path(args[args.index('--output-dir')+1])/'equipment_datum_position_screen_final.json'
  final_equipment_datum_receipt=Path(args[args.index('--output-dir')+1])/'equipment_datum_position_screen_stage.json'
  if final_equipment_datum_dest.exists() or final_equipment_datum_receipt.exists():raise ValueError('refusing to overwrite final equipment datum evidence')
 if '--final-bulk-source-dn-policy' in args:
  if '--exploded-device-chain-policy' not in args:raise ValueError('final bulk DN requires final device chain stage')
  index=args.index('--final-bulk-source-dn-policy');final_bulk_dn_policy=Path(args[index+1]);del args[index:index+2]
  final_bulk_dn_dest=Path(args[args.index('--output-dir')+1])/'source_dn_bulk_screen_final.json'
  if final_bulk_dn_dest.exists():raise ValueError('refusing to overwrite final bulk DN evidence')
 if '--final-dn-detail-scope-policy' in args:
  if final_bulk_dn_policy is None:raise ValueError('final DN detail scope requires final bulk DN screen')
  index=args.index('--final-dn-detail-scope-policy');final_dn_detail_scope_policy=Path(args[index+1]);del args[index:index+2]
  final_dn_detail_scope_dest=Path(args[args.index('--output-dir')+1])/'source_dn_detail_scope_final.json'
  if final_dn_detail_scope_dest.exists():raise ValueError('refusing to overwrite final DN detail scope')
 if '--final-dn-pattern-policy' in args:
  if final_bulk_dn_policy is None:raise ValueError('final DN patterns require final bulk DN screen')
  index=args.index('--final-dn-pattern-policy');final_dn_pattern_policy=Path(args[index+1]);del args[index:index+2]
  final_dn_pattern_dest=Path(args[args.index('--output-dir')+1])/'source_dn_ambiguity_patterns_final.json'
  if final_dn_pattern_dest.exists():raise ValueError('refusing to overwrite final DN patterns')
 if '--final-cross-floor-line-policy' in args:
  if '--exploded-device-chain-policy' not in args or '--datum-policy' not in args:raise ValueError('final cross-floor evidence requires final device chain and datum stages')
  index=args.index('--final-cross-floor-line-policy');final_cross_floor_policy=Path(args[index+1]);del args[index:index+2]
  final_cross_floor_out=Path(args[args.index('--output-dir')+1]);final_cross_floor_lines=final_cross_floor_out/'cross_floor_native_line_evidence_final.json';final_cross_floor_dest=final_cross_floor_out/'cross_floor_axis_diagnostic_final.json'
  if final_cross_floor_lines.exists() or final_cross_floor_dest.exists():raise ValueError('refusing to overwrite final cross-floor evidence')
 translated_inline_policy=None
 if '--translated-inline-conflict-policy' in args:
  if '--exploded-device-chain-policy' not in args:raise ValueError('translated conflict screen requires final device chain stage')
  index=args.index('--translated-inline-conflict-policy');translated_inline_policy=Path(args[index+1]);del args[index:index+2]
  translated_out=Path(args[args.index('--output-dir')+1]);translated_triage=translated_out/'inline_system_conflict_triage_final.json';translated_dest=translated_out/'translated_inline_conflict_family.json'
  if translated_triage.exists() or translated_dest.exists():raise ValueError('refusing to overwrite translated inline conflict evidence')
 exploded_offset_circle_policy=None
 if '--exploded-offset-circle-policy' in args:
  if '--exploded-device-chain-policy' not in args:raise ValueError('exploded offset screen requires final device chain stage')
  index=args.index('--exploded-offset-circle-policy');exploded_offset_circle_policy=Path(args[index+1]);del args[index:index+2]
  exploded_offset_circle_dest=Path(args[args.index('--output-dir')+1])/'native_exploded_offset_circle_candidates.json'
  if exploded_offset_circle_dest.exists():raise ValueError('refusing to overwrite exploded offset circle evidence')
 exploded_device_chain_policy=None
 if '--exploded-device-chain-policy' in args:
  if '--exploded-joint-ownership-policy' not in args:raise ValueError('exploded device chain requires final ownership stage')
  index=args.index('--exploded-device-chain-policy');exploded_device_chain_policy=Path(args[index+1]);del args[index:index+2]
  chain_out=Path(args[args.index('--output-dir')+1]);chain_evidence=chain_out/'native_exploded_device_joint_evidence.json';chain_graph=chain_out/'graph_with_exploded_device_chains.json';chain_receipt=chain_out/'exploded_device_chain_stage.json'
  if any(x.exists() for x in (chain_evidence,chain_graph,chain_receipt)):raise ValueError('refusing to overwrite exploded device source chain')
 bulk_dn_policy=None
 if '--bulk-source-dn-policy' in args:
  index=args.index('--bulk-source-dn-policy');bulk_dn_policy=Path(args[index+1]);del args[index:index+2]
  bulk_dn_destination=Path(args[args.index('--output-dir')+1])/'source_dn_bulk_screen.json'
  if bulk_dn_destination.exists():raise ValueError('refusing to overwrite bulk DN evidence')
 supplemental_circle=None;supplemental_joint=None
 if ('--supplemental-device-circle-policy' in args)!=('--supplemental-nested-joint-policy' in args):raise ValueError('supplemental circle and nested joint policies must be supplied together')
 if '--supplemental-device-circle-policy' in args:
  index=args.index('--supplemental-device-circle-policy');supplemental_circle=Path(args[index+1]);del args[index:index+2]
  index=args.index('--supplemental-nested-joint-policy');supplemental_joint=Path(args[index+1]);del args[index:index+2]
  supplemental_out=Path(args[args.index('--output-dir')+1]);supplemental_circle_dest=supplemental_out/'supplemental_native_device_circle_lines.json';supplemental_joint_dest=supplemental_out/'supplemental_native_nested_joint_evidence.json'
  if supplemental_circle_dest.exists() or supplemental_joint_dest.exists():raise ValueError('refusing to overwrite supplemental source evidence')
 cross_floor_line_policy=None
 if '--cross-floor-line-policy' in args:
  if '--datum-policy' not in args:raise ValueError('cross-floor source diagnostics require datum policy')
  index=args.index('--cross-floor-line-policy');cross_floor_line_policy=Path(args[index+1]);del args[index:index+2]
  cross_floor_out=Path(args[args.index('--output-dir')+1]);cross_floor_lines=cross_floor_out/'cross_floor_native_line_evidence.json';cross_floor_report=cross_floor_out/'cross_floor_axis_diagnostic.json'
  if cross_floor_lines.exists() or cross_floor_report.exists():raise ValueError('refusing to overwrite cross-floor evidence')
 offset_circle_policy=None
 if '--offset-circle-policy' in args:
  index=args.index('--offset-circle-policy');offset_circle_policy=Path(args[index+1]);del args[index:index+2]
  offset_circle_dest=Path(args[args.index('--output-dir')+1])/'native_offset_circle_candidates.json'
  if offset_circle_dest.exists():raise ValueError('refusing to overwrite offset circle evidence')
 offset_joint_ownership_policy=None
 if '--offset-nested-ownership-policy' in args:
  if '--exploded-joint-ownership-policy' not in args:raise ValueError('offset nested ownership requires previous ownership stage')
  index=args.index('--offset-nested-ownership-policy');offset_joint_ownership_policy=Path(args[index+1]);del args[index:index+2]
  destination_offset_ownership=Path(args[args.index('--output-dir')+1])/'topology-offset-nested-ownership'
  if destination_offset_ownership.exists():raise ValueError('refusing to overwrite offset nested ownership')
 direct_spline_policy=None
 if '--direct-spline-joint-policy' in args:
  if '--exploded-joint-ownership-policy' not in args:raise ValueError('direct spline joint audit requires final ownership graph')
  index=args.index('--direct-spline-joint-policy');direct_spline_policy=Path(args[index+1]);del args[index:index+2]
  direct_spline_dest=Path(args[args.index('--output-dir')+1])/'direct_spline_joint_audit.json'
  if direct_spline_dest.exists():raise ValueError('refusing to overwrite spline joint audit')
 inline_conflict_triage='--inline-conflict-triage' in args
 if inline_conflict_triage:
  args.remove('--inline-conflict-triage')
  if '--exploded-joint-ownership-policy' not in args:raise ValueError('inline conflict triage requires exploded joint ownership')
  destination_inline_triage=Path(args[args.index('--output-dir')+1])/'inline_system_conflict_triage.json'
  if destination_inline_triage.exists():raise ValueError('refusing to overwrite inline conflict triage')
 if '--exploded-joint-ownership-policy' in args:
  index=args.index('--exploded-joint-ownership-policy');exploded_joint_policy=Path(args[index+1]);del args[index:index+2]
  if '--attach-device-source-paths' not in args:raise ValueError('exploded joint ownership requires device source paths')
  destination_exploded_joint=Path(args[args.index('--output-dir')+1])/'topology-exploded-joint-ownership'
  if destination_exploded_joint.exists():raise ValueError('refusing to overwrite exploded joint ownership')
 attach_device_paths='--attach-device-source-paths' in args
 if attach_device_paths:
  if '--nested-joint-policy' not in args:raise ValueError('device source paths require nested joint evidence')
  args.remove('--attach-device-source-paths')
  destination_device_paths=Path(args[args.index('--output-dir')+1])/'graph_with_device_source_paths.json'
  if destination_device_paths.exists():raise ValueError('refusing to overwrite device source path graph')
 if '--nested-joint-policy' in args:
  index=args.index('--nested-joint-policy');nested_joint_policy=Path(args[index+1]);del args[index:index+2]
  if '--device-circle-lines-policy' not in args:raise ValueError('nested joint evidence requires device circle line evidence')
  destination_nested_joint=Path(args[args.index('--output-dir')+1])/'native_nested_joint_evidence.json'
  if destination_nested_joint.exists():raise ValueError('refusing to overwrite nested joint evidence')
 if '--device-circle-lines-policy' in args:
  index=args.index('--device-circle-lines-policy');device_circle_policy=Path(args[index+1]);del args[index:index+2]
  destination_device_circle=Path(args[args.index('--output-dir')+1])/'native_device_circle_lines.json'
  if destination_device_circle.exists():raise ValueError('refusing to overwrite device circle line evidence')
 if '--junction-ray-policy' in args:
  index=args.index('--junction-ray-policy');junction_policy=Path(args[index+1]);del args[index:index+2]
  destination_junction=Path(args[args.index('--output-dir')+1])/'native_junction_ray_evidence.json'
  if destination_junction.exists():raise ValueError('refusing to overwrite junction ray evidence')
 if ('--path-coverage-policy' in args)!=('--partial-length-policy' in args):raise ValueError('partial length stage requires both coverage and partial policies')
 if '--path-coverage-policy' in args:
  index=args.index('--path-coverage-policy');coverage_policy=Path(args[index+1]);del args[index:index+2]
  index=args.index('--partial-length-policy');partial_policy=Path(args[index+1]);del args[index:index+2]
  _out=Path(args[args.index('--output-dir')+1]);coverage_destination=_out/'native_path_coverage_audit.json';partial_destination=_out/'topology-partial-source-length'
  if coverage_destination.exists() or partial_destination.exists():raise ValueError('refusing to overwrite partial source length evidence')
 if '--segment-dn-policy' in args:
  index=args.index('--segment-dn-policy');segment_policy=Path(args[index+1]);del args[index:index+2]
  if '--line-path-policy' not in args:raise ValueError('segment DN candidates require source line path evidence')
  destination_segment=Path(args[args.index('--output-dir')+1])/'native_segment_dn_candidates.json'
  if destination_segment.exists():raise ValueError('refusing to overwrite segment DN evidence')
 if '--line-path-policy' in args:
  index=args.index('--line-path-policy');line_policy=Path(args[index+1]);del args[index:index+2]
  destination_line=Path(args[args.index('--output-dir')+1])/'native_line_path_evidence.json'
  if destination_line.exists():raise ValueError('refusing to overwrite native line path evidence')
 if '--datum-policy' in args:
  index=args.index('--datum-policy');policy=Path(args[index+1]);del args[index:index+2]
  out=Path(args[args.index('--output-dir')+1]);destination=out/'native_level_evidence.json'
  if destination.exists():raise ValueError('refusing to overwrite native datum evidence')
  datum=native_level_evidence.collect(Path(args[args.index('--dxf')+1]),policy)
 index=args.index('--previous-graph');prior=Path(args[index+1]);del args[index:index+2];edges.PREVIOUS_GRAPH=json.loads(prior.read_text(encoding='utf8'))
 index=args.index('--normalization-config');cfg=json.loads(Path(args[index+1]).read_text(encoding='utf8'));del args[index:index+2]
 source_hash=hashlib.sha256(Path(args[args.index('--dxf')+1]).read_bytes()).hexdigest()
 prior_hash=hashlib.sha256(prior.read_bytes()).hexdigest()
 if cfg.get('previous_source_sha256') and cfg['previous_source_sha256']!=source_hash:raise ValueError('prior source hash mismatch')
 if cfg.get('previous_graph_sha256') and cfg['previous_graph_sha256']!=prior_hash:raise ValueError('prior graph hash mismatch')
 same_source=bool(cfg.get('previous_source_sha256')==source_hash and cfg.get('previous_graph_sha256')==prior_hash)
 geometry.get_system_layers=lambda doc:cfg['system_layers']
 edges.equipment_graph.tee_id_lookup=edges.node_ids
 owner_audit=[];old_matches=edges.equipment_graph.make_provisional_matches
 def stable_owners(owned,tees):
  matches=old_matches(owned,tees)
  if not cfg.get('previous_source_sha256'):return matches
  source=Path(args[args.index('--dxf')+1])
  if hashlib.sha256(source.read_bytes()).hexdigest()!=cfg['previous_source_sha256']:raise ValueError('Prior ownership requires identical source CAD identity')
  ids=edges.node_ids(tees);byid={ids[(t.system,geometry.point_key((t.x,t.y),geometry.ENDPOINT_QUANTUM))]:t for t in tees};result=[]
  for m in matches:
   prior=[e for e in edges.PREVIOUS_GRAPH['edges']if e['system']==m.system and m.equipment.label in [e['start_node_id'],e['end_node_id']]]
   if len(prior)==1:
    e=prior[0];oldid=e['end_node_id']if e['start_node_id']==m.equipment.label else e['start_node_id'];distance=min(pg.segdist((m.tee.x,m.tee.y),a,b)for path in e['attribute_paths']for a,b in zip(path,path[1:]))
    if m.tee_id!=oldid and distance>cfg.get('near_junction',{}).get('maximum_gap',.5)and oldid in byid:
     owner_audit.append(dict(equipment=m.equipment.label,system=m.system,rejected_target=m.tee_id,preserved_target=oldid,distance_to_prior_source_path=distance,rule='reject_new_owner_binding_outside_unchanged_source_path'))
     m=dataclasses.replace(m,tee=byid[oldid],tee_id=oldid,candidate_selection='source_path_verified_prior_owner_preserved')
   result.append(m)
  return result
 edges.equipment_graph.make_provisional_matches=stable_owners
 oldtrim=geometry.trim_short_dangling_overshoots;audit=[];snaps=[];source_index={};oldcollect=geometry.collect_pipe_segments
 def sourcekey(a,b):return tuple(sorted([tuple(round(v,5)for v in a),tuple(round(v,5)for v in b)]))
 def collect(doc):
  for top in doc.modelspace():
   for e in geometry.recursive_entities(top):
    if e.dxftype()=='LINE'and e.dxf.layer in cfg['system_layers']:
     k=(cfg['system_layers'][e.dxf.layer],sourcekey(tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]));source_index.setdefault(k,set()).add(top.dxf.handle)
  return oldcollect(doc)
 geometry.collect_pipe_segments=collect
 def trim(ss):
  ss,legacy=oldtrim(ss);pg.set_tolerance(geometry.POINT_TOLERANCE);rows=[dict(a=s.start,b=s.end,system=s.system,handle='SOURCE-SEGMENT-'+str(i),source_handles=sorted(source_index.get((s.system,sourcekey(s.start,s.end)),[])),source_handle_scope='top_level_owner')for i,s in enumerate(ss)]
  rows,records=trim_elbow_overshoots(rows,cfg['elbow_overshoot']);audit.extend(records);rows,records=snap_near_junction_endpoints(rows,cfg.get('near_junction'));snaps.extend(records);return [geometry.Segment(s['system'],tuple(s['a']),tuple(s['b']))for s in rows],legacy
 geometry.trim_short_dangling_overshoots=trim;sys.argv=[sys.argv[0]]+args;edges.main();out=Path(args[args.index('--output-dir')+1]);(out/'normalization_audit.json').write_text(json.dumps({'elbow_overshoots':audit,'junction_snaps':snaps,'config':cfg},indent=2),encoding='utf8')
 g=json.loads((out/'graph_with_edges.json').read_text(encoding='utf8'));old=edges.PREVIOUS_GRAPH
 g['junctionValidation']=junction_validation.compare(g,old,same_source=same_source)
 (out/'graph_with_edges.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 mapping={'retired_nodes':[n['node_id']for n in old['nodes']if n['node_id']not in {n['node_id']for n in g['nodes']}],'retired_edges':[e['edge_id']for e in old['edges']if e['edge_id']not in {e['edge_id']for e in g['edges']}],'merged_edges':[{'retained_edge_id':e['edge_id'],'old_start':next(x['start_node_id']for x in old['edges']if x['edge_id']==e['edge_id']),'new_start':e['start_node_id'],'end':e['end_node_id']}for e in g['edges']if any(x['edge_id']==e['edge_id']and{x['start_node_id'],x['end_node_id']}!={e['start_node_id'],e['end_node_id']}for x in old['edges'])]}
 (out/'id_mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf8');print('MAPPING',json.dumps(mapping))
 if datum is not None:
  datum['graph_sha256']=hashlib.sha256((out/'graph_with_edges.json').read_bytes()).hexdigest()
  datum['graph_status']='unverified; datum evidence does not validate topology'
  native_level_evidence.write_new(datum,destination)
 if line_policy is not None:
  source=Path(args[args.index('--dxf')+1]);doc,proof=read_source(source);graph_bytes=(out/'graph_with_edges.json').read_bytes();policy_bytes=line_policy.read_bytes()
  line_evidence=native_line_path_evidence.collect(doc,json.loads(graph_bytes),json.loads(policy_bytes),proof['source_sha256'],hashlib.sha256(graph_bytes).hexdigest())
  line_evidence.update(policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),script_sha256=hashlib.sha256(Path(native_line_path_evidence.__file__).read_bytes()).hexdigest(),source_preflight=proof)
  with destination_line.open('x',encoding='utf8',newline='\n') as f:json.dump(line_evidence,f,ensure_ascii=False,indent=2);f.write('\n')
 if segment_policy is not None:
  source=Path(args[args.index('--dxf')+1]);doc,proof=read_source(source);graph_bytes=(out/'graph_with_edges.json').read_bytes();line_bytes=destination_line.read_bytes();policy_bytes=segment_policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
  segment_evidence=native_segment_dn_candidates.collect(doc,json.loads(graph_bytes),json.loads(line_bytes),json.loads(policy_bytes),proof['source_sha256'],sha(graph_bytes),sha(line_bytes))
  segment_evidence.update(policy_sha256=sha(policy_bytes),script_sha256=hashlib.sha256(Path(native_segment_dn_candidates.__file__).read_bytes()).hexdigest(),text_guard_sha256=hashlib.sha256((ROOT/'native_dn_text_position.py').read_bytes()).hexdigest(),source_preflight=proof)
  with destination_segment.open('x',encoding='utf8',newline='\n') as f:json.dump(segment_evidence,f,ensure_ascii=False,indent=2);f.write('\n')
 if coverage_policy is not None:
  source=Path(args[args.index('--dxf')+1]);graph_file=out/'graph_with_edges.json'
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_path_coverage_audit_legacy.py'),'--source',str(source),'--graph',str(graph_file),'--policy',str(coverage_policy),'--output',str(coverage_destination)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'apply_partial_source_length_status.py'),'--source',str(source),'--graph',str(graph_file),'--coverage',str(coverage_destination),'--policy',str(partial_policy),'--output',str(partial_destination)],check=True)
 if junction_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=(partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_junction_ray_evidence.py'),'--source',str(source),'--graph',str(target),'--policy',str(junction_policy),'--output',str(destination_junction)],check=True)
 if device_circle_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=(partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_device_circle_lines.py'),'--source',str(source),'--graph',str(target),'--policy',str(device_circle_policy),'--output',str(destination_device_circle)],check=True)
 if nested_joint_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_nested_joint_evidence.py'),'--source',str(source),'--graph',str(target),'--inventory',str(out/'edge_device_instances.csv'),'--circle',str(destination_device_circle),'--policy',str(nested_joint_policy),'--output',str(destination_nested_joint)],check=True)
 if offset_circle_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=(partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_offset_circle_candidates.py'),'--source',str(source),'--graph',str(target),'--policy',str(offset_circle_policy),'--output',str(offset_circle_dest)],check=True)
 if supplemental_circle is not None:
  source=Path(args[args.index('--dxf')+1]);target=(partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_device_circle_lines.py'),'--source',str(source),'--graph',str(target),'--policy',str(supplemental_circle),'--output',str(supplemental_circle_dest)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_nested_joint_evidence.py'),'--source',str(source),'--graph',str(target),'--inventory',str(out/'edge_device_instances.csv'),'--circle',str(supplemental_circle_dest),'--policy',str(supplemental_joint),'--output',str(supplemental_joint_dest)],check=True)
 if attach_device_paths:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'attach_native_device_source_paths.py'),'--source',str(source),'--graph',str(target),'--inventory',str(out/'edge_device_instances.csv'),'--circle',str(destination_device_circle),'--joint',str(destination_nested_joint),'--policy',str(nested_joint_policy),'--output',str(destination_device_paths)],check=True)
 if exploded_joint_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'repair_exploded_joint_ownership.py'),'--source',str(source),'--graph',str(destination_device_paths),'--devices',str(out/'edge_device_instances.csv'),'--policy',str(exploded_joint_policy),'--output',str(destination_exploded_joint)],check=True)
 if offset_joint_ownership_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'repair_offset_nested_joint_ownership.py'),'--source',str(source),'--graph',str(destination_exploded_joint/'graph_with_edges.json'),'--devices',str(destination_exploded_joint/'edge_device_instances.csv'),'--policy',str(offset_joint_ownership_policy),'--output',str(destination_offset_ownership)],check=True)
 final_ownership=destination_offset_ownership if offset_joint_ownership_policy is not None else destination_exploded_joint if exploded_joint_policy is not None else None
 if direct_spline_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'audit_direct_spline_joint.py'),'--source',str(source),'--graph',str(final_ownership/'graph_with_edges.json'),'--inventory',str(final_ownership/'edge_device_instances.csv'),'--policy',str(direct_spline_policy),'--output',str(direct_spline_dest)],check=True)
 if inline_conflict_triage:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'inline_system_conflict_triage.py'),'--source',str(source),'--graph',str(final_ownership/'graph_with_edges.json'),'--output',str(destination_inline_triage)],check=True)
 if cross_floor_line_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=(final_ownership/'graph_with_edges.json') if final_ownership is not None else (partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_line_path_evidence.py'),'--source',str(source),'--graph',str(target),'--policy',str(cross_floor_line_policy),'--output',str(cross_floor_lines)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'cross_floor_axis_diagnostic.py'),'--source',str(source),'--graph',str(target),'--line-evidence',str(cross_floor_lines),'--line-policy',str(cross_floor_line_policy),'--datum-evidence',str(destination),'--datum-policy',str(policy),'--output',str(cross_floor_report)],check=True)
 if bulk_dn_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=(final_ownership/'graph_with_edges.json') if final_ownership is not None else (partial_destination/'graph_with_edges.json') if coverage_policy is not None else (out/'graph_with_edges.json')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'source_dn_bulk_screen.py'),'--source',str(source),'--graph',str(target),'--policy',str(bulk_dn_policy),'--output',str(bulk_dn_destination)],check=True)
 if exploded_device_chain_policy is not None:
  source=Path(args[args.index('--dxf')+1]);target=final_ownership/'graph_with_edges.json';inventory=final_ownership/'edge_device_instances.csv'
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_exploded_device_joint_evidence.py'),'--source',str(source),'--graph',str(target),'--inventory',str(inventory),'--policy',str(exploded_device_chain_policy),'--output',str(chain_evidence)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'attach_exploded_device_source_chain.py'),'--source',str(source),'--graph',str(target),'--inventory',str(inventory),'--policy',str(exploded_device_chain_policy),'--evidence',str(chain_evidence),'--output',str(chain_graph)],check=True)
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  chain_receipt.write_text(json.dumps({'status':'source_chain_attached_unreviewed','source_sha256':sha(source),'input_graph_sha256':sha(target),'inventory_sha256':sha(inventory),'policy_sha256':sha(exploded_device_chain_policy),'evidence_sha256':sha(chain_evidence),'output_graph_sha256':sha(chain_graph),'preexisting_evidence_graph_scope':'input_graph_only_rebind_for_output_graph','hil_ready':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 final_graph=chain_graph if exploded_device_chain_policy is not None else None
 if final_path_coverage_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_path_coverage_audit.py'),'--source',str(source),'--graph',str(chain_graph),'--policy',str(final_path_coverage_policy),'--output',str(final_coverage_dest)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'apply_partial_source_length_status.py'),'--source',str(source),'--graph',str(chain_graph),'--coverage',str(final_coverage_dest),'--policy',str(final_partial_length_policy),'--output',str(final_partial_dest)],check=True)
  final_graph=final_partial_dest/'graph_with_edges.json'
 if final_partial_line_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'partial_native_line_coverage.py'),'--source',str(source),'--graph',str(final_graph),'--coverage',str(final_coverage_dest),'--policy',str(final_partial_line_policy),'--output',str(final_partial_line_dest)],check=True)
 if final_attach_partial_line:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'attach_partial_line_evidence.py'),'--source',str(source),'--graph',str(final_graph),'--coverage',str(final_coverage_dest),'--screen',str(final_partial_line_dest),'--policy',str(final_partial_line_policy),'--output',str(final_partial_line_attach_dest)],check=True)
  final_graph=final_partial_line_attach_dest/'graph_with_edges.json'
 if block_attachment_inputs is not None:
  spec=json.loads(block_attachment_inputs.read_text(encoding='utf8'))
  keys=('old_graph','joint','inventory','circle','joint_policy')
  if set(spec)!=set(keys) or any(not isinstance(spec[k],str) or not Path(spec[k]).is_file() for k in keys):raise ValueError('invalid source block attachment inputs')
  shared=['--source',str(source),'--old-graph',spec['old_graph'],'--graph',str(final_graph),'--joint',spec['joint'],'--inventory',spec['inventory'],'--circle',spec['circle'],'--joint-policy',spec['joint_policy']]
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'verify_block_equipment_attachments.py'),*shared,'--output',str(block_evidence)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'attach_block_equipment_attachments.py'),*shared,'--evidence',str(block_evidence),'--output',str(block_dest)],check=True)
  final_graph=block_dest/'graph_with_source_block_attachments.json'
 if source_floor_inputs is not None:
  spec=json.loads(source_floor_inputs.read_text(encoding='utf8'))
  if set(spec)!={'plan_source','policy'} or any(not isinstance(v,str) or not Path(v).is_file() for v in spec.values()):raise ValueError('invalid source floor correction inputs')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'repair_source_floor_labels.py'),'--source',str(source),'--plan-source',spec['plan_source'],'--graph',str(final_graph),'--policy',spec['policy'],'--output',str(source_floor_dest)],check=True)
  final_graph=source_floor_dest/'graph_with_edges.json'
 if upstream_system_policy is not None:
  upstream_input=final_graph
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'repair_upstream_joint_systems.py'),'--source',str(source),'--graph',str(final_graph),'--devices',str(final_ownership/'edge_device_instances.csv'),'--policy',str(upstream_system_policy),'--output',str(upstream_system_dest)],check=True)
  final_graph=upstream_system_dest/'graph_with_edges.json'
  inventory=upstream_system_dest/'edge_device_instances.csv'
  # Source/graph/inventory-bound policies below must target this corrected
  # output; source contacts are reproduced rather than copied from old audits.
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  (upstream_system_dest/'stage.json').write_text(json.dumps({'status':'scoped_system_repair_downstream_rechecks_required','source_sha256':sha(source),'input_graph_sha256':sha(upstream_input),'final_graph_sha256':sha(final_graph),'policy_sha256':sha(upstream_system_policy),'audit_sha256':sha(upstream_system_dest/'upstream-system-repair-audit.json'),'canonical_inventory_sha256':sha(upstream_system_dest/'edge_device_instances.csv'),'historical_scoped_inventory_sha256':sha(final_ownership/'edge_device_instances.csv'),'hil_ready':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if final_direct_spline_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'audit_direct_spline_joint.py'),'--source',str(source),'--graph',str(final_graph),'--inventory',str(inventory),'--policy',str(final_direct_spline_policy),'--output',str(final_direct_spline_dest)],check=True)
 if final_gap_joint_policy is not None:
  from screen_missing_gap_joints import bind_final
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'screen_missing_gap_joints.py'),'--source',str(source),'--graph',str(chain_graph),'--coverage',str(final_coverage_dest),'--inventory',str(inventory),'--policy',str(final_gap_joint_policy),'--output',str(final_gap_joint_dest)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'audit_calibrated_joint_inventory.py'),'--source',str(source),'--inventory',str(inventory),'--policy',str(final_gap_joint_policy),'--output',str(final_joint_inventory)],check=True)
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  found=json.loads(final_gap_joint_dest.read_text(encoding='utf8'));stage=bind_final(found,json.loads(chain_graph.read_text(encoding='utf8')),json.loads(final_graph.read_text(encoding='utf8')),sha(final_graph))
  stage.update(source_sha256=sha(source),input_graph_sha256=sha(chain_graph),inventory_sha256=sha(inventory),coverage_sha256=sha(final_coverage_dest),evidence_sha256=sha(final_gap_joint_dest),policy_sha256=sha(final_gap_joint_policy),script_sha256=sha(ROOT/'screen_missing_gap_joints.py'),joint_inventory_evidence_sha256=sha(final_joint_inventory),joint_inventory_script_sha256=sha(ROOT/'audit_calibrated_joint_inventory.py'))
  if direct_spline_policy is not None:
   from reconcile_joint_inventory_contacts import write_reconciliation
   contact_report=final_direct_spline_dest if final_direct_spline_policy is not None else direct_spline_dest
   contact_graph=final_graph if final_direct_spline_policy is not None else final_ownership/'graph_with_edges.json'
   write_reconciliation(final_joint_inventory,contact_report,contact_graph,final_graph,sha(source),sha(inventory),final_joint_contact_reconciliation)
   stage.update(joint_contact_reconciliation_sha256=sha(final_joint_contact_reconciliation),joint_contact_reconciliation_script_sha256=sha(ROOT/'reconcile_joint_inventory_contacts.py'))
  final_gap_joint_stage.write_text(json.dumps(stage,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if final_bulk_dn_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'source_dn_bulk_screen.py'),'--source',str(source),'--graph',str(final_graph),'--policy',str(final_bulk_dn_policy),'--output',str(final_bulk_dn_dest)],check=True)
 if final_dn_detail_scope_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'isometric_detail_dn_scope.py'),'--source',str(source),'--graph',str(final_graph),'--bulk-screen',str(final_bulk_dn_dest),'--policy',str(final_dn_detail_scope_policy),'--output',str(final_dn_detail_scope_dest)],check=True)
 if final_dn_pattern_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'group_ambiguous_dn_patterns.py'),'--bulk-screen',str(final_bulk_dn_dest),'--policy',str(final_dn_pattern_policy),'--output',str(final_dn_pattern_dest)],check=True)
 if final_cross_floor_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_line_path_evidence.py'),'--source',str(source),'--graph',str(final_graph),'--policy',str(final_cross_floor_policy),'--output',str(final_cross_floor_lines)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'cross_floor_axis_diagnostic.py'),'--source',str(source),'--graph',str(final_graph),'--line-evidence',str(final_cross_floor_lines),'--line-policy',str(final_cross_floor_policy),'--datum-evidence',str(destination),'--datum-policy',str(policy),'--output',str(final_cross_floor_dest)],check=True)
 if final_equipment_datum_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'screen_equipment_datum_positions.py'),'--source',str(source),'--graph',str(final_graph),'--datum',str(destination),'--policy',str(final_equipment_datum_policy),'--output',str(final_equipment_datum_dest)],check=True)
  screen=json.loads(final_equipment_datum_dest.read_text(encoding='utf8'));unresolved=[x for x in screen['records'] if x['status']!='anchor_band_matches_graph_label']+screen['unscreened_equipment_ids']
  final_equipment_datum_receipt.write_text(json.dumps({'status':'screened_floor_interpretation_pending' if unresolved else 'screened_not_physical_floor_confirmation','source_sha256':sha(source),'graph_sha256':sha(final_graph),'evidence_sha256':sha(final_equipment_datum_dest),'policy_sha256':sha(final_equipment_datum_policy),'candidate_count':len(unresolved),'hil_ready':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if exploded_offset_circle_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'native_exploded_offset_circle_candidates.py'),'--source',str(source),'--graph',str(final_graph),'--inventory',str(inventory),'--policy',str(exploded_offset_circle_policy),'--output',str(exploded_offset_circle_dest)],check=True)
 if translated_inline_policy is not None:
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'inline_system_conflict_triage.py'),'--source',str(source),'--graph',str(final_graph),'--output',str(translated_triage)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'translated_inline_conflict_family.py'),'--source',str(source),'--graph',str(final_graph),'--triage',str(translated_triage),'--policy',str(translated_inline_policy),'--output',str(translated_dest)],check=True)
if __name__=='__main__':main()
