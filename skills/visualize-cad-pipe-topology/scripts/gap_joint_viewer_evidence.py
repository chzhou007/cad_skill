"""Validate scoped unassigned joint evidence before adding viewer-only glyphs."""
def validate(evidence,stage,canonical,viewer,source_hash,canonical_hash,evidence_hash):
 if (evidence.get('status')!='missing_source_joints_candidate_screen' or evidence.get('source_sha256')!=source_hash or evidence.get('graph_mutated') is not False or evidence.get('hil_ready') is not False or stage.get('status')!='missing_joint_candidates_pending_source_comparison' or stage.get('source_sha256')!=source_hash or stage.get('final_graph_sha256')!=canonical_hash or stage.get('evidence_sha256')!=evidence_hash or stage.get('input_graph_sha256')!=evidence.get('graph_sha256') or stage.get('policy_sha256')!=evidence.get('policy_sha256') or stage.get('script_sha256')!=evidence.get('script_sha256') or stage.get('human_accepted') is not False or stage.get('hil_ready') is not False):raise ValueError('gap joint evidence binding mismatch')
 rows=evidence.get('records');a={e['edge_id']:e for e in canonical['edges']};b={e['edge_id']:e for e in viewer['edges']}
 if not isinstance(rows,list) or not rows or len(a)!=len(canonical['edges']) or len(b)!=len(viewer['edges']):raise ValueError('invalid gap joint scope')
 result=[];seen=set()
 for r in rows:
  h=r.get('insert_handle');eid=r.get('edge_id');x=a.get(eid);y=b.get(eid)
  if (not isinstance(h,str) or not h or h in seen or not x or not y or r.get('system')!=x.get('system') or r.get('status')!='source_calibrated_joint_unassigned_pending_review' or r.get('candidate_type')!='金属软接' or r.get('physical_length')!='unknown' or r.get('human_accepted') is not False or any(x.get(k)!=y.get(k) for k in ('system','start_node_id','end_node_id','attribute_paths','source_handles'))):raise ValueError('invalid or stale joint candidate')
  seen.add(h);result.append({'id':'PENDING-JOINT-'+h,'source_handles':[h],'display_source_chain':[h],
   'floor':x.get('start_floor'),'system':x['system'],'candidate_edge_id':eid,
   'candidate_type':'金属软接','physical_length':'unknown','ownership':'unconfirmed',
   'source_evidence_sha256':evidence_hash})
 if stage.get('candidate_count')!=len(result) or stage.get('candidate_handles')!=[x['source_handles'][0] for x in result]:raise ValueError('joint candidate scope mismatch')
 return result
