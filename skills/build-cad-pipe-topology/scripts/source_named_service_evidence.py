"""Attach source-labelled service candidates without changing hydraulic tracing."""
import collections,copy

KINDS={'makeup_water_interface':('makeup_water','补水'), 'drain_interface':('drainage','排水')}

def attach(graph,trace,leader_check,boundary_audit,source_sha256,graph_sha256):
 if any(x.get('source_sha256')!=source_sha256 or x.get('graph_sha256')!=graph_sha256 for x in (trace,leader_check,boundary_audit)):
  raise ValueError('Source service evidence does not match current source and graph')
 if leader_check.get('status')!='PASS' or leader_check.get('verified')!=leader_check.get('total'):
  raise ValueError('Native source label and leader checks incomplete')
 if trace.get('conflicting_edges') or boundary_audit.get('edges_touching_mixed_or_other_layer'):
  raise ValueError('Conflicting source service evidence must stay pending')
 good={r['node_id']:r for r in leader_check['checks']if r.get('meets_prior_calibration')and r.get('connected_leader_path')}
 edges={e['edge_id']:e for e in graph['edges']};byedge=collections.defaultdict(list)
 for group in trace['groups']:
  if group['node_id'] not in good or group['kind']not in KINDS or group['status']!='candidate_trace_only':raise ValueError('Unverified named endpoint')
  witness=good[group['node_id']]
  if witness['source_text']!=group['label']or witness['label_handle']!=group['label_handle']or set(witness['leader_handles'])!=set(group['leader_handles']):raise ValueError('Native label witness mismatch')
  for eid in group['edges']:
   if eid not in edges or edges[eid]['system']!='unclassified_water':raise ValueError('Named source trace references missing or already classified edge')
   byedge[eid].append(group)
 audited={r['edge_id']:r for r in boundary_audit['edges']}
 if set(audited)!=set(byedge):raise ValueError('Boundary audit does not cover every candidate edge')
 for eid,groups in byedge.items():
  kinds={g['kind']for g in groups};layers={g['source_layer']for g in groups};row=audited[eid]
  if len(kinds)!=1 or len(layers)!=1 or row['kind']!=next(iter(kinds))or row['source_layer']!=next(iter(layers)):raise ValueError('Competing service type or native layer')
  if any(c['mixed_source_contact']or c['system_review_required']or c['different_or_missing_native_layer']for c in row['contacts']):raise ValueError('Unsafe graph boundary')
 out=copy.deepcopy(graph)
 for e in out['edges']:
  if e['edge_id'] not in byedge:continue
  groups=byedge[e['edge_id']];kind=groups[0]['kind'];service,zh=KINDS[kind]
  e['source_named_service']={'status':'source_label_and_same_layer_trace_candidate','service_id':service,'display_zh':zh,'source_layer':groups[0]['source_layer'],
   'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,
   'witnesses':[{'node_id':g['node_id'],'original_text':g['label'],'label_handle':g['label_handle'],'leader_handles':g['leader_handles']}for g in groups],
   'scope':'Candidate supported by a source-labelled interface and same-layer graph path. Existing hydraulic system classification and connectivity remain unchanged.'}
 return out,{'edges_with_source_named_service':len(byedge),'by_type':dict(collections.Counter(KINDS[groups[0]['kind']][0]for groups in byedge.values())),
             'existing_hydraulic_systems_unchanged':True,'hydraulic_connectivity_unchanged':True,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256}
