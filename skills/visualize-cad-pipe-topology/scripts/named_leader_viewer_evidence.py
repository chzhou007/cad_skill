"""Validate graph-pinned endpoint candidates before displaying them."""
def validate(screen,source_graph,view_graph,source_hash,source_graph_hash):
 if screen.get('status')!='scoped_leader_candidates_not_binding' or screen.get('source_sha256')!=source_hash or screen.get('graph_sha256')!=source_graph_hash or screen.get('graph_mutated') is not False or screen.get('mapping_ready') is not False or screen.get('hil_ready') is not False:raise ValueError('stale or invalid named leader screen')
 if source_graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('named leader source graph mismatch')
 def indexed(items,key):
  out={x[key]:x for x in items}
  if len(out)!=len(items):raise ValueError('duplicate graph identity')
  return out
 sn=indexed(source_graph['nodes'],'node_id');vn=indexed(view_graph['nodes'],'node_id');se=indexed(source_graph['edges'],'edge_id');ve=indexed(view_graph['edges'],'edge_id')
 if sn.keys()!=vn.keys() or se.keys()!=ve.keys():raise ValueError('viewer graph identities differ from evidence graph')
 for eid,e in se.items():
  if any(e.get(k)!=ve[eid].get(k) for k in ('system','start_node_id','end_node_id','attribute_paths','path_points')):raise ValueError('viewer graph path differs from evidence graph')
 rows=screen.get('selections');seen=set()
 if not isinstance(rows,list) or not rows:raise ValueError('named leader screen empty')
 for row in rows:
  nid=row.get('node_id');n=sn.get(nid);v=vn.get(nid);label=row.get('label',{})
  if nid in seen or not n or not v or row.get('status')!='source_geometry_candidate_not_binding' or row.get('system') not in ('supply','return') or row.get('system')!=n.get('system') or n.get('boundary_type')!='unresolved_source_terminal' or row.get('pipe_handle') not in n.get('source_handles',[]) or label.get('binding_status')!='unbound_source_text_candidate' or label.get('system')!=n.get('system') or not all(row.get(k) for k in ('pipe_handle','leader_handle','text_handle')) or not label.get('original_text'):raise ValueError('invalid named leader candidate')
  if any(n.get(k)!=v.get(k) for k in ('node_type','boundary_type','system','x','y','source_handles')):raise ValueError('viewer candidate node differs from evidence graph')
  seen.add(nid)
 return rows
