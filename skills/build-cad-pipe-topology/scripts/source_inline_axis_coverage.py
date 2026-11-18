"""Preserve source block axis-coverage uncertainty on assigned components."""
import copy,math

def attach(graph,instances,evidence,source_sha256,graph_sha256,source_doc):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale axis coverage evidence')
 rows=evidence.get('records',[])
 if not rows or len(rows)!=evidence.get('instances'):raise ValueError('Incomplete axis coverage evidence')
 out=copy.deepcopy(graph);devices=copy.deepcopy(instances);edges={e['edge_id']:e for e in out['edges']};byid={d['device_name']:d for d in devices};seen=set();stats={'partial':0,'spans':0}
 for r in rows:
  ident=r.get('instance_id');d=byid.get(ident);edge=edges.get(r.get('edge_id'))
  if not d or not edge or ident in seen or d.get('edge_id')!=edge['edge_id'] or d.get('source_top_handle')!=r.get('handle'):raise ValueError('Changed or competing component ownership')
  ent=source_doc.entitydb.get(r['handle'])
  if not ent or not ent.is_alive or ent.dxftype()!='INSERT' or ent.dxf.owner!=source_doc.modelspace().block_record_handle or ent.dxf.name!=d.get('source_block_name'):raise ValueError('Native block changed')
  points=[p.dxf.location for p in ent.virtual_entities() if p.dxftype()=='POINT']
  if len(points)!=2:raise ValueError('Native axis points changed')
  a,b=points;dx=b.x-a.x;dy=b.y-a.y;ll=dx*dx+dy*dy
  if not ll:raise ValueError('Degenerate source axis')
  values=[((p[0]-a.x)*dx+(p[1]-a.y)*dy)/ll for path in edge.get('attribute_paths',[]) for p in path]
  if not values:raise ValueError('Missing source path')
  lo,hi=min(values),max(values);span=lo<=0 and hi>=1
  if len(r.get('path_projection_range',[]))!=2 or abs(lo-r['path_projection_range'][0])>1e-7 or abs(hi-r['path_projection_range'][1])>1e-7 or span!=r.get('covers_point_axis_span'):raise ValueError('Source path axis witness changed')
  status='axis_projection_spans_both_points' if span else 'axis_projection_partial'
  d['source_axis_coverage_status']=status;d['source_axis_coverage_scope']='Projection range only; does not prove continuous physical connection or engineering type.'
  edge.setdefault('source_inline_axis_candidates',[]).append({'source_device_name':ident,'source_handle':r['handle'],'status':status,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256})
  stats['spans' if span else 'partial']+=1;seen.add(ident)
 out['metadata']['hil_ready']=False;out['metadata']['stage_status']='inline_axis_coverage_pending'
 out.setdefault('technicalPending',[]).append({'id':'PLANT-INLINE-PARTIAL-AXIS','kind':'algorithm_interpretation','reason':'Repeated native proxy blocks have source paths ending inside the source axis span; interpretation and continuation remain pending.'})
 return out,devices,{'instances':len(seen),'partial_axis_projections':stats['partial'],'spans_axis_projections':stats['spans'],'nodes_unchanged':out['nodes']==graph['nodes'],'new_nodes':0,'new_edges':0}
