"""Record source-backed enclosed junction candidates without rewiring the graph."""
import copy

def attach(graph,evidence,original_source_sha256,graph_sha256):
 if graph.get('metadata',{}).get('original_dxf_sha256')!=original_source_sha256 or evidence.get('source_02_sha256')!=original_source_sha256 or evidence.get('graph_02_sha256')!=graph_sha256:
  raise ValueError('Stale source or graph evidence')
 rows=evidence.get('records',[])
 if len(rows)!=evidence.get('tower_count') or len(rows)!=evidence.get('return_entry_count'):raise ValueError('Incomplete family inventory')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};seen_towers=set();seen_junctions=set()
 for r in rows:
  tower=nodes.get(r['tower_id']);j=nodes.get(r['internal_junction_id']);e=edges.get(r['current_edge_id'])
  if not tower or tower.get('node_type')!='equipment' or not j or j.get('node_type')!='tee' or not e or e.get('system')!='cooling_return':raise ValueError('Stale source object, junction or edge')
  if not r.get('original_02_tag_handle') or tower.get('source_tag_handle')!=r['original_02_tag_handle']:
   raise ValueError('Equipment source tag does not match the original witness')
  cells=r.get('original_02_cell_handles')
  if not isinstance(cells,list) or len(cells)!=2 or any(not isinstance(h,str) or not h for h in cells) or len(set(cells))!=2:
   raise ValueError('Original two-cell witness is incomplete')
  incident=[x for x in out['edges']if j['node_id']in(x['start_node_id'],x['end_node_id'])]
  if len(incident)!=3 or {x['edge_id']for x in incident}!=set(r['incident_edges']) or any(x['system']!='cooling_return'for x in incident):raise ValueError('Source junction changed')
  if r['native_source_line'] not in e.get('source_handles',[]) or j['node_id'] not in(e['start_node_id'],e['end_node_id']):raise ValueError('Entry line witness changed')
  if tower['node_id']in seen_towers or j['node_id']in seen_junctions or tower.get('source_internal_return_candidate')or j.get('source_equipment_owner_candidate'):raise ValueError('Competing source ownership')
  candidate={'tower_node_id':tower['node_id'],'junction_node_id':j['node_id'],'entry_edge_id':e['edge_id'],'incident_edge_ids':r['incident_edges'],
    'source_line_handle':r['native_source_line'],'source_tag_handle':r['original_02_tag_handle'],'source_cell_handles':r['original_02_cell_handles'],
    'source_sha256':original_source_sha256,'source_graph_sha256':graph_sha256,'status':'source_enclosed_junction_candidate_not_bound',
    'scope':'Native return line enters the tower-pair outline and reaches an existing internal T; physical port and internal component ownership remain unconfirmed.'}
  tower['source_internal_return_candidate']=candidate;j['source_equipment_owner_candidate']=candidate
  for node in (tower,j):node['review_queue']='source_comparison';node['review_required']=True
  seen_towers.add(tower['node_id']);seen_junctions.add(j['node_id'])
 out['metadata']['hil_ready']=False;out['metadata']['hil_block_reason']='Source comparison required for repeated cooling tower return-water internal junctions.'
 out['metadata']['stage_status']='source_comparison_internal_tower_return_pending'
 out.setdefault('technicalPending',[]).append({'id':'CT-RETURN-INTERNAL-JUNCTIONS','kind':'algorithm_interpretation','reason':'Repeated native return entry into tower source outlines reaches internal graph junctions; equipment and internal-path ownership is not yet resolved.'})
 return out,{'tower_candidates':len(seen_towers),'junction_candidates':len(seen_junctions),'edges_unchanged':out['edges']==graph['edges'],
             'physical_ports_inferred':0,'source_02_sha256':original_source_sha256,'source_graph_sha256':graph_sha256}
