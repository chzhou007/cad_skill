"""Independent full modelspace inventory and final-source topology checks."""
import collections,json
import pipe_geometry as pg

def source_coverage_gate(doc,graph,config,output):
 edges=graph['edges'];nodes=graph['nodes'];represented={h for e in edges for h in e.get('source_handles',[])}
 active=set(config['system_layers'])|{config['auxiliary_pipe_layer']}|set(config.get('additional_auxiliary_pipe_layers',[]))
 required=set(config.get('required_physical_candidate_layers',[]));layers=collections.defaultdict(collections.Counter);ledger=[];blocks=[]
 for entity in doc.modelspace():
  layer=entity.dxf.layer;typ=entity.dxftype();layers[layer][typ]+=1;handle=entity.dxf.handle
  status='final_edge_source'if handle in represented else'candidate_layer_context'if layer in active else'outside_physical_candidate_layers_requires_context_classification'
  ledger.append({'source_handle':handle,'source_layer':layer,'entity_type':typ,'status':status})
 for layer in sorted(required-active):blocks.append({'rule':'required_source_layer_not_loaded','layer':layer})
 degree=collections.Counter(n for e in edges for n in [e['start_node_id'],e['end_node_id']]);nodeids={n['node_id']for n in nodes}
 for e in edges:
  if e['start_node_id']not in nodeids or e['end_node_id']not in nodeids:blocks.append({'rule':'edge_missing_endpoint','edge_id':e['edge_id']})
 for n in nodes:
  if n['node_type']=='tee'and degree[n['node_id']]!=3:blocks.append({'rule':'final_tee_invalid_adjacency','node_id':n['node_id'],'degree':degree[n['node_id']]})
 # A handle assertion is source-bound project evidence, never a universal CAD constant.
 for h in config.get('required_final_source_handles',[]):
  if h not in represented:blocks.append({'rule':'required_source_handle_not_in_final_edge','source_handle':h})
 discovery=output/'straight_crossover_discovery.json';unverified_group_candidates=[]
 if discovery.exists():
  for candidate in json.loads(discovery.read_text(encoding='utf8')):
   source_layers=candidate.get('source_layers',[])
   if candidate.get('reason')=='source_group_not_verified_despite_crossing_evidence'and len(source_layers)==2 and source_layers[0]and source_layers[0]==source_layers[1]:
    unverified_group_candidates.append(candidate);blocks.append({'rule':'crossing_proven_but_physical_source_group_not_resolved','a':candidate['a'],'b':candidate['b'],'source_handles':candidate['source_handles'],'source_layer':source_layers[0],'reason':'Configure a source-proven physical group or provide a source exclusion. Do not classify this as a generic unproven endpoint.'})
 (output/'source_group_gap_blockers.json').write_text(json.dumps(unverified_group_candidates,ensure_ascii=False,indent=2),encoding='utf8')
 gap_coverage=[];requirements=list(config.get('required_source_gap_spans',[]))
 accepted=output/'straight_crossover_audit.json'
 if accepted.exists():requirements+=json.loads(accepted.read_text(encoding='utf8'))
 seen=set()
 for requirement in requirements:
  a,b=requirement['a'],requirement['b'];key=tuple(sorted([tuple(round(x,5)for x in a),tuple(round(x,5)for x in b)]))
  if key in seen:continue
  seen.add(key);source_handles=set(requirement.get('source_handles',[]))
  ids=[e['edge_id']for e in edges if source_handles<=set(e.get('source_handles',[]))and any(pg.on(a,p,q)and pg.on(b,p,q)for path in e.get('attribute_paths',[e.get('path_points',[])])for p,q in zip(path,path[1:]))]
  row={'a':a,'b':b,'source_handles':sorted(source_handles),'edge_ids':ids,'status':'applied'if ids else'failed_final_continuation','crossings':requirement.get('crossings',[])};gap_coverage.append(row)
  if not ids:blocks.append({'rule':'required_gap_has_no_complete_final_edge','source_handles':sorted(source_handles),'a':a,'b':b})
  for crossing in requirement.get('crossings',[]):
   if any(n['node_type']=='tee'and pg.dist((n['x'],n['y']),crossing['crossing'])<=pg.TOL for n in nodes):blocks.append({'rule':'independent_crossover_became_tee','crossing':crossing['crossing']})
 (output/'final_source_gap_coverage.json').write_text(json.dumps(gap_coverage,ensure_ascii=False,indent=2),encoding='utf8')
 if config.get('required_source_gap_spans'):graph['normalizationCoverage']=gap_coverage
 report={'status':'FAIL'if blocks else'PASS_WITH_PENDING_CONTEXT','source_modelspace_entities':len(ledger),'used_layers':dict(layers),'active_physical_candidate_layers':sorted(active),'required_layers':sorted(required),'blockers':blocks,'unclassified_context_entities':sum(x['status']=='outside_physical_candidate_layers_requires_context_classification'for x in ledger),'scope':'Full modelspace inventory is independent of configured candidate discovery. Context semantics remain pending; no human review.'}
 (output/'source_entity_input_inventory.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf8')
 (output/'independent_source_coverage_gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 if blocks:raise ValueError('Independent source coverage failed; see independent_source_coverage_gate.json')
 return report
