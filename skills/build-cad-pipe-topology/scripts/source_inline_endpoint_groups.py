"""Group unresolved endpoints by their existing source component assignment."""
import copy,math

def attach(graph,doc,devices,source_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('Source identity mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};groups=[];used_nodes=set();used_edges=set();used_inserts=set()
 for d in devices:
  if d.get('source_block_name')!='$VALVE$000005460':continue
  edge=edges.get(d.get('edge_id'));source=doc.entitydb.get(d.get('source_top_handle'))
  if not edge or not source or source.dxftype()!='INSERT' or source.dxf.name!=d['source_block_name'] or source.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('Component source or edge mismatch')
  if edge['edge_id'] in used_edges or source.dxf.handle in used_inserts:raise ValueError('Competing assignments')
  candidates=[nid for nid in (edge['start_node_id'],edge['end_node_id']) if nodes[nid].get('boundary_type')=='unresolved_source_terminal']
  if not candidates or used_nodes.intersection(candidates):raise ValueError('Endpoint ownership mismatch')
  points=[p.dxf.location for p in source.virtual_entities() if p.dxftype()=='POINT']
  if len(points)!=2:raise ValueError('Source axis evidence changed')
  a,b=points;dx=b.x-a.x;dy=b.y-a.y;ll=dx*dx+dy*dy
  if not ll:raise ValueError('Degenerate component axis')
  vals=[((p[0]-a.x)*dx+(p[1]-a.y)*dy)/ll for path in edge.get('attribute_paths',[]) for p in path]
  if not vals:raise ValueError('Missing edge source path')
  span=min(vals)<=0 and max(vals)>=1;status='axis_projection_spans_both_points' if span else 'axis_projection_partial'
  if d.get('source_axis_coverage_status')!=status:raise ValueError('Axis projection status mismatch')
  refs=[x for x in edge.get('source_inline_axis_candidates',[]) if x.get('source_device_name')==d.get('device_name') and x.get('source_handle')==source.dxf.handle and x.get('status')==status]
  if len(refs)!=1:raise ValueError('Graph source axis candidate mismatch')
  group={'group_id':'INLINE-SOURCE-'+source.dxf.handle,'source_device_id':d['device_name'],'source_insert_handle':source.dxf.handle,'edge_id':edge['edge_id'],'endpoint_node_ids':sorted(candidates),'system':edge['system'],'axis_projection_status':status,'status':'edge_component_assignment_semantics_pending','scope':'One existing component assignment and edge; endpoint ownership, exact contact and engineering subtype remain unresolved.','hydraulic_connection_confirmed':False}
  for nid in candidates:nodes[nid]['source_inline_endpoint_group']=copy.deepcopy(group)
  edge['source_inline_endpoint_group']=copy.deepcopy(group);groups.append(group);used_nodes.update(candidates);used_edges.add(edge['edge_id']);used_inserts.add(source.dxf.handle)
 out['sourceInlineEndpointGroups']=groups
 return out,{'groups':len(groups),'endpoint_nodes':len(used_nodes),'physical_edges_created':0,'partial_axis_groups':sum(g['axis_projection_status']=='axis_projection_partial' for g in groups),'full_axis_projection_groups':sum(g['axis_projection_status']=='axis_projection_spans_both_points' for g in groups)}
