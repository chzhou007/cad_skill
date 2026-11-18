"""Attach verified annotation reference relations, never hydraulic edges."""
import copy,math

def distance(p,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll)) if ll else 0
 return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
def attach(graph,doc,evidence,source_sha256,graph_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Source or graph identity mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};used_nodes=set();used_targets=set();groups=[]
 for r in evidence['records']:
  label=r['label'];t=doc.entitydb.get(r['text_handle'])
  if not t or t.dxftype()!='TEXT' or t.dxf.owner!=doc.modelspace().block_record_handle or t.plain_text()!='接至'+label or r.get('source_note')!=t.plain_text():raise ValueError('Native target note changed')
  local={}
  for nid in r['endpoint_node_ids']:
   n=nodes.get(nid)
   if not n or nid in used_nodes or n.get('source_endpoint_annotation',{}).get('text')!=label:raise ValueError('Endpoint label mismatch')
   incident=[e for e in out['edges'] if nid in (e['start_node_id'],e['end_node_id'])]
   if len(incident)!=1 or incident[0]['system'] in local:raise ValueError('Endpoint system ambiguous')
   local[incident[0]['system']]=nid;used_nodes.add(nid)
  if set(local)!={'supply','return'}:raise ValueError('Expected two distinct services')
  target_ids=[]
  for z in r['target_sources']:
   sys=z['system'];edge_ids=z.get('graph_edges',[])
   if sys not in local or len(edge_ids)!=1:raise ValueError('Ambiguous target graph edge')
   e=edges.get(edge_ids[0]);source=doc.entitydb.get(z['native_pipe_handle']);leader=doc.entitydb.get(z['leader_handle']);pt=z['point']
   if not e or e['system']!=sys or e['edge_id'] in used_targets or z['native_pipe_handle'] not in e.get('source_handles',[]):raise ValueError('Target source edge mismatch')
   if not source or source.dxftype()!='LINE' or not leader or leader.dxftype() not in ('LINE','LWPOLYLINE') or source.dxf.owner!=doc.modelspace().block_record_handle or leader.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('Source geometry unavailable')
   a=source.ocs().to_wcs(source.dxf.start);b=source.ocs().to_wcs(source.dxf.end)
   if distance(pt,(a.x,a.y),(b.x,b.y))>.01:raise ValueError('Leader point misses source line')
   vv=[leader.ocs().to_wcs(leader.dxf.start),leader.ocs().to_wcs(leader.dxf.end)] if leader.dxftype()=='LINE' else list(leader.vertices_in_wcs())
   if len(vv)<2 or min(math.dist(pt,(v.x,v.y)) for v in (vv[0],vv[-1]))>.01:raise ValueError('Leader endpoint changed')
   ins=t.ocs().to_wcs(t.dxf.insert)
   if min(math.dist((ins.x,ins.y),(v.x,v.y)) for v in vv)>20:raise ValueError('Leader no longer reaches note')
   if not any(distance(pt,a,b)<.01 for path in e.get('attribute_paths',[]) for a,b in zip(path,path[1:])):raise ValueError('Point missing from graph edge path')
   relation={'label':label,'source_note':r['source_note'],'text_handle':r['text_handle'],'leader_handle':z['leader_handle'],'source_pipe_handle':z['native_pipe_handle'],'point':pt,'endpoint_node_id':local[sys],'target_edge_id':e['edge_id'],'system':sys,'status':'source_annotation_reference_only','hydraulic_connection_confirmed':False}
   nodes[local[sys]]['source_annotation_reference']=copy.deepcopy(relation);e.setdefault('source_annotation_references',[]).append(copy.deepcopy(relation));used_targets.add(e['edge_id']);target_ids.append(e['edge_id'])
  if len(target_ids)!=2:raise ValueError('Missing supply or return target')
  groups.append({'label':label,'endpoint_node_ids':sorted(local.values()),'target_edge_ids':sorted(target_ids),'source_note_handle':r['text_handle'],'status':'annotation_reference_only'})
 out['sourceAnnotationReferenceGroups']=groups
 return out,{'groups':len(groups),'node_references':len(used_nodes),'edge_references':len(used_targets),'hydraulic_edges_created':0}
