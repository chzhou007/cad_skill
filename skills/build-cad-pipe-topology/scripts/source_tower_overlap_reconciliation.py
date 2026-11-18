"""Reopen source-symbol ambiguity and record unbound native equipment candidates."""
import collections,copy

def reconcile(graph,overlap,port_marks,source_sha256,graph_sha256):
 if any(e.get('source_sha256')!=source_sha256 or e.get('graph_sha256')!=graph_sha256 for e in (overlap,port_marks)):
  raise ValueError('Stale source or graph evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};reopened=[];candidates=collections.defaultdict(list);seen=set()
 for row in overlap['records']:
  if row['system']!='cooling_supply' or not row.get('nearby_equipment_circle_candidates'):continue
  n=nodes.get(row['node_id']);tower=nodes.get(row['tower_id']);e=edges.get(row['edge_id'])
  if not n or not tower or not e or n.get('boundary_type')!='source_native_downturn_terminal' or n['node_id']not in (e['start_node_id'],e['end_node_id']) or tower.get('node_type')!='equipment':raise ValueError('Stale candidate node, equipment or edge')
  if n['source_downturn_evidence']['circle_handle']!=row['source_circle'] or n['node_id']in seen:raise ValueError('Conflicting native source ownership')
  nearby=row['nearby_equipment_circle_candidates']
  if min(c['distance']for c in nearby)>4.0:raise ValueError('Invalid bounded proximity evidence')
  n.update(resolution_state='local_symbol_form_equipment_overlap_pending',review_queue='source_comparison',review_required=True,
           source_equipment_overlap={'tower_node_id':tower['node_id'],'exact_center_match':bool(row['native_equipment_circle_matches']),
             'nearest_distance_native':row['nearest_equipment_circle_center_distance'],'nearby_source_circles':nearby,
             'scope':'Visual source overlap; not an equipment port or established hydraulic connection.'})
  reopened.append(n['node_id']);seen.add(n['node_id'])
 for row in port_marks['records']:
  tower=nodes.get(row['tower_id']);n=nodes.get(row['node_id']);e=edges.get(row['edge_id']);matches=row.get('native_circle_matches',[])
  if not tower or not n or not e or tower.get('node_type')!='equipment' or n['node_id']not in(e['start_node_id'],e['end_node_id']) or len(matches)!=1 or matches[0]['distance']>.1:
   raise ValueError('Unverified native device mark or graph endpoint')
  if n['node_id']in seen:raise ValueError('Competing endpoint candidate roles')
  candidates[tower['node_id']].append({'candidate_node_id':n['node_id'],'edge_id':e['edge_id'],'equipment_circle_handle':matches[0]['handle'],
    'center_distance_native':matches[0]['distance'],'system':e['system'],'status':'source_mark_candidate_not_bound'})
  seen.add(n['node_id'])
 for tower_id,items in candidates.items():
  if len(items)!=2 or len({x['candidate_node_id']for x in items})!=2 or len({x['edge_id']for x in items})!=1:raise ValueError('Internal path pair is incomplete or ambiguous')
  tower=nodes[tower_id]
  if tower.get('source_ports') or tower.get('ports') or tower.get('source_port_candidates'):raise ValueError('Do not replace existing physical port ownership')
  tower['source_port_candidates']=items
  tower['source_internal_path_candidate']={'edge_id':items[0]['edge_id'],'source_node_ids':[x['candidate_node_id']for x in items],
      'scope':'Both ends lie at native body marks; physical meaning and representation as an internal path remain pending. No self-loop is created.'}
 return out,{'reopened_downturn_nodes':len(reopened),'candidate_towers':len(candidates),'candidate_ports':sum(map(len,candidates.values())),
             'reopened_node_ids':reopened,'edges_unchanged':out['edges']==graph['edges'],'physical_ports_inferred':0,
             'source_sha256':source_sha256,'source_graph_sha256':graph_sha256}
